"""Summarize session speed data (PROTOCOL §5.2, §5.4).

Per (engine, model, workload), over all non-warm-up requests of all blocks in the given sessions:
  - aggregate tg per repetition-pass = sum(tg tokens) / sum(generation time) over the prompt set;
    reported as median / IQR / min / max / CV over passes (a pass = one block repetition)
  - per-prompt medians of tg, TTFT and engine-reported pp
  - speedup vs a baseline engine: ratio of aggregate tg built from per-prompt median times,
    with a 95 % bootstrap CI resampling prompts (10 000 resamples, fixed seed)
Outliers (outside 1.5 IQR of the per-pass aggregates) are flagged, never dropped.

Usage: python bench/summarize.py <session_dir> [<session_dir> ...] [--baseline ENGINE] [--out file.json]
"""
from __future__ import annotations

import argparse, json
from collections import defaultdict
from pathlib import Path

import numpy as np

from common import ROOT, write_json


def load_sessions(dirs):
    rows = []
    for d in dirs:
        d = Path(d)
        meta = json.loads((d / "session.json").read_text(encoding="utf-8"))
        for b in meta["blocks"]:
            spec = b["spec"]
            for line in (d / b["file"]).read_text(encoding="utf-8").splitlines():
                r = json.loads(line)
                if r.get("warmup"):
                    continue
                r["_engine"], r["_model"], r["_workload"] = spec["engine"], spec["model"], spec["workload"]
                r["_pass"] = f'{d.name}/b{b["block"]}/r{r["rep"]}'
                rows.append(r)
    return rows


def q(x, p):
    return float(np.percentile(x, p)) if len(x) else None


def summarize(rows, baseline=None):
    groups = defaultdict(list)
    for r in rows:
        groups[(r["_engine"], r["_model"], r["_workload"])].append(r)
    out = {}
    per_prompt = {}
    for key, rs in groups.items():
        passes = defaultdict(lambda: [0, 0.0])
        prompts = defaultdict(lambda: {"tg_time": [], "tg_tok": [], "ttft": [], "pp": [], "tps": [], "acc": []})
        for r in rs:
            m = r["metrics"]
            if m["gen_time_s"]:
                passes[r["_pass"]][0] += m["tg_tokens"]
                passes[r["_pass"]][1] += m["gen_time_s"]
            p = prompts[r["item_id"]]
            p["tg_time"].append(m["gen_time_s"] or np.nan); p["tg_tok"].append(m["tg_tokens"] or 0)
            p["ttft"].append(m["ttft_ms"]); p["pp"].append(m["pp_tps_engine"] or np.nan); p["tps"].append(m["tg_tps"] or np.nan)
            if m.get("draft_n"):
                p["acc"].append(m["draft_n_accepted"] / m["draft_n"])
        agg = np.array([tok / t for tok, t in passes.values() if t > 0])
        i1, i3 = q(agg, 25), q(agg, 75)
        outl = [float(x) for x in agg if i1 is not None and (x < i1 - 1.5 * (i3 - i1) or x > i3 + 1.5 * (i3 - i1))]
        pp = {iid: {"tg_time_med": float(np.nanmedian(v["tg_time"])), "tg_tok_med": float(np.median(v["tg_tok"])),
                    "tg_tps_med": float(np.nanmedian(v["tps"])), "ttft_ms_med": float(np.median(v["ttft"])),
                    "pp_tps_med": float(np.nanmedian(v["pp"])), "n": len(v["ttft"]),
                    "accept_rate_med": float(np.median(v["acc"])) if v["acc"] else None}
              for iid, v in prompts.items()}
        per_prompt[key] = pp
        out["|".join(key)] = {
            "engine": key[0], "model": key[1], "workload": key[2], "n_requests": len(rs), "n_passes": len(agg),
            "tg_agg_median": float(np.median(agg)) if len(agg) else None, "tg_agg_q1": i1, "tg_agg_q3": i3,
            "tg_agg_min": float(agg.min()) if len(agg) else None, "tg_agg_max": float(agg.max()) if len(agg) else None,
            "tg_agg_cv": float(agg.std(ddof=1) / agg.mean()) if len(agg) > 1 else None, "tg_agg_outliers": outl,
            "ttft_ms_median_over_prompts": float(np.median([v["ttft_ms_med"] for v in pp.values()])),
            "per_prompt": pp,
        }
    if baseline:
        rng = np.random.default_rng(12345)
        for key, pp in per_prompt.items():
            bkey = (baseline, key[1], key[2])
            if key[0] == baseline or bkey not in per_prompt:
                continue
            bp = per_prompt[bkey]
            ids = sorted(set(pp) & set(bp))
            ct = np.array([pp[i]["tg_time_med"] for i in ids]); ck = np.array([pp[i]["tg_tok_med"] for i in ids])
            bt = np.array([bp[i]["tg_time_med"] for i in ids]); bk = np.array([bp[i]["tg_tok_med"] for i in ids])
            ratio = (ck.sum() / ct.sum()) / (bk.sum() / bt.sum())
            bs = []
            for _ in range(10000):
                s = rng.integers(0, len(ids), len(ids))
                bs.append((ck[s].sum() / ct[s].sum()) / (bk[s].sum() / bt[s].sum()))
            ttft_ratio = [pp[i]["ttft_ms_med"] / bp[i]["ttft_ms_med"] for i in ids]
            pp_ratio = [pp[i]["pp_tps_med"] / bp[i]["pp_tps_med"] for i in ids]
            per_prompt_speedup = {i: (pp[i]["tg_tok_med"] / pp[i]["tg_time_med"]) / (bp[i]["tg_tok_med"] / bp[i]["tg_time_med"]) for i in ids}
            out["|".join(key)]["vs_baseline"] = {
                "baseline": baseline, "n_prompts": len(ids), "tg_speedup": float(ratio),
                "tg_speedup_ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
                "ttft_ratio_median": float(np.median(ttft_ratio)), "ttft_ratio_max": float(np.max(ttft_ratio)),
                "pp_ratio_median": float(np.nanmedian(pp_ratio)), "pp_ratio_min": float(np.nanmin(pp_ratio)),
                "per_prompt_tg_speedup": per_prompt_speedup,
                "significant": bool(ratio >= 1.02 and np.percentile(bs, 2.5) > 1.0),
            }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sessions", nargs="+")
    ap.add_argument("--baseline", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    res = summarize(load_sessions(a.sessions), a.baseline)
    res_meta = {"sessions": a.sessions, "baseline": a.baseline, "groups": res}
    if a.out:
        write_json(Path(a.out), res_meta)
    for k, g in res.items():
        line = (f'{g["engine"]:>24s} {g["model"]:>11s} {g["workload"]:>9s}  tg_agg median={g["tg_agg_median"]:.2f} '
                f'[IQR {g["tg_agg_q1"]:.2f}-{g["tg_agg_q3"]:.2f}, min {g["tg_agg_min"]:.2f}, max {g["tg_agg_max"]:.2f}, '
                f'CV {100*(g["tg_agg_cv"] or 0):.2f}%, n={g["n_passes"]}]  TTFT med={g["ttft_ms_median_over_prompts"]:.1f}ms')
        if "vs_baseline" in g:
            v = g["vs_baseline"]
            line += (f'\n{"":>38s}speedup={v["tg_speedup"]:.3f}x CI95=[{v["tg_speedup_ci95"][0]:.3f},{v["tg_speedup_ci95"][1]:.3f}] '
                     f'TTFT ratio med={v["ttft_ratio_median"]:.3f} pp ratio med={v["pp_ratio_median"]:.3f} sig={v["significant"]}')
        print(line)


if __name__ == "__main__":
    main()
