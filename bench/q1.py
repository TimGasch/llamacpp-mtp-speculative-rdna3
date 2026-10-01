"""Quality gate Q1 — teacher-forced full-distribution comparison (PROTOCOL §4.3).

  dump:    python bench/q1.py dump --engine E --model M --split dev --ub U [--tag T] [--extra-args "..."]
           runs E's qdump; the logits go to results/q1dumps/ (large, not in git), and a record with
           their SHA-256 goes to results/raw/q1/.
  compare: python bench/q1.py compare --ref <dump-name> --cand <dump-name> [--label L]
           writes per-position CSV + summary JSON (with gate verdicts) to results/raw/q1/.
"""
from __future__ import annotations

import argparse, json, shlex, subprocess, time
from datetime import datetime
from pathlib import Path

import numpy as np

from common import (ROOT, engine_server_args, load_engine, manifest_check, model_sha_verified, sha256_file,
                    split_dir, write_json)

DUMPS = ROOT / "results" / "q1dumps"
OUT = ROOT / "results" / "raw" / "q1"
GATES = {"mean_kld_max": 5e-4, "p99_kld_max": 5e-3, "top1_agree_min": 0.995, "abs_ln_ppl_ratio_max": 1e-3}


def cmd_dump(a):
    tool = manifest_check(a.allow_unfrozen)
    eng = load_engine(a.engine)
    model_sha_verified(a.model)
    split_dir(a.split, a.phase3_holdout, "q1-dump")
    segs = ROOT / "eval" / ("dev" if a.split == "dev" else "holdout_tokens") / f"q1_segments_{a.model}.txt"
    name = f"{a.engine}_{a.model}_{a.split}_ub{a.ub}" + (f"_{a.tag}" if a.tag else "")
    DUMPS.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    largs = engine_server_args(eng, a.model) + (shlex.split(a.extra_args) if a.extra_args else [])
    cmd = [str(ROOT / eng["qdump"]), "--segs", str(segs), "--ub", str(a.ub), "--out", str(DUMPS / name), "--"] + largs
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT / Path(eng["qdump"]).parent))
    (OUT / f"{name}.dump.log").write_text(r.stdout + r.stderr, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise SystemExit(f"qdump failed ({r.returncode}); see {OUT / (name + '.dump.log')}")
    rec = {"name": name, "date": datetime.now().isoformat(), "cmd": cmd, "wall_s": time.time() - t0,
           "engine": eng, "model": a.model, "split": a.split, "ub": a.ub, "tooling": tool,
           "segments_file_sha256": sha256_file(segs),
           "logits_sha256": sha256_file(DUMPS / f"{name}.logits"),
           "qdump_meta": json.loads((DUMPS / f"{name}.json").read_text(encoding="utf-8"))}
    for s in rec["qdump_meta"]["segments"]:
        s.pop("targets", None)                       # keep the record small; targets live in the dump json
    write_json(OUT / f"{name}.dump.json", rec)
    print(f"dump {name}: {rec['qdump_meta']['n_scored_total']} positions, {rec['wall_s']:.1f}s, sha={rec['logits_sha256'][:16]}")


def _load(name):
    meta = json.loads((DUMPS / f"{name}.json").read_text(encoding="utf-8"))
    n, v = meta["n_scored_total"], meta["n_vocab"]
    arr = np.memmap(DUMPS / f"{name}.logits", dtype=np.float32, mode="r", shape=(n, v))
    return meta, arr


def _log_softmax(x):
    x = x.astype(np.float64)
    m = x.max(axis=1, keepdims=True)
    return x - (m + np.log(np.exp(x - m).sum(axis=1, keepdims=True)))


def cmd_compare(a):
    tool = manifest_check(a.allow_unfrozen)
    mr, R = _load(a.ref)
    mc, C = _load(a.cand)
    assert R.shape == C.shape, (R.shape, C.shape)
    seg_r = [(s["id"], s["targets"]) for s in mr["segments"]]
    assert seg_r == [(s["id"], s["targets"]) for s in mc["segments"]], "segments/targets differ"
    targets = np.array([t for _, ts in seg_r for t in ts], dtype=np.int64)
    seg_of = [sid for sid, ts in seg_r for _ in ts]
    n = R.shape[0]
    kld = np.empty(n); t1r = np.empty(n, np.int64); t1c = np.empty(n, np.int64)
    nllr = np.empty(n); nllc = np.empty(n); maxabs = np.empty(n)
    CH = 32
    for i in range(0, n, CH):
        xr, xc = np.asarray(R[i:i + CH]), np.asarray(C[i:i + CH])
        lr, lc = _log_softmax(xr), _log_softmax(xc)
        kld[i:i + CH] = (np.exp(lr) * (lr - lc)).sum(axis=1)
        t1r[i:i + CH] = xr.argmax(axis=1); t1c[i:i + CH] = xc.argmax(axis=1)
        idx = np.arange(lr.shape[0]); tg = targets[i:i + CH]
        nllr[i:i + CH] = -lr[idx, tg]; nllc[i:i + CH] = -lc[idx, tg]
        maxabs[i:i + CH] = np.abs(xr.astype(np.float64) - xc).max(axis=1)
    kld = np.maximum(kld, 0.0)              # clamp tiny negative rounding
    agree = t1r == t1c

    def stats(mask):
        ppl_r, ppl_c = float(np.exp(nllr[mask].mean())), float(np.exp(nllc[mask].mean()))
        return {"n": int(mask.sum()), "mean_kld": float(kld[mask].mean()), "p99_kld": float(np.percentile(kld[mask], 99)),
                "max_kld": float(kld[mask].max()), "top1_agree": float(agree[mask].mean()),
                "ppl_ref": ppl_r, "ppl_cand": ppl_c, "abs_ln_ppl_ratio": float(abs(np.log(ppl_c / ppl_r))),
                "bit_identical_rows": int((maxabs[mask] == 0).sum()), "max_abs_logit_diff": float(maxabs[mask].max())}

    all_mask = np.ones(n, bool)
    summ = stats(all_mask)
    per_seg = {sid: stats(np.array([s == sid for s in seg_of])) for sid in dict.fromkeys(seg_of)}
    verdict = {"mean_kld": summ["mean_kld"] <= GATES["mean_kld_max"],
               "p99_kld": summ["p99_kld"] <= GATES["p99_kld_max"],
               "top1_agree": summ["top1_agree"] >= GATES["top1_agree_min"],
               "ppl_ratio": summ["abs_ln_ppl_ratio"] <= GATES["abs_ln_ppl_ratio_max"]}
    label = a.label or f"{a.cand}__vs__{a.ref}"
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / f"{label}.positions.csv", "w", encoding="utf-8") as f:
        f.write("segment,idx,target,kld,top1_ref,top1_cand,nll_ref,nll_cand,max_abs_logit_diff\n")
        for i in range(n):
            f.write(f"{seg_of[i]},{i},{targets[i]},{kld[i]:.6e},{t1r[i]},{t1c[i]},{nllr[i]:.6f},{nllc[i]:.6f},{maxabs[i]:.4e}\n")
    res = {"label": label, "date": datetime.now().isoformat(), "ref": a.ref, "cand": a.cand, "tooling": tool,
           "ref_logits_sha256": sha256_file(DUMPS / f"{a.ref}.logits"),
           "cand_logits_sha256": sha256_file(DUMPS / f"{a.cand}.logits"),
           "gates": GATES, "summary": summ, "verdict": verdict, "pass": all(verdict.values()), "per_segment": per_seg}
    write_json(OUT / f"{label}.summary.json", res)
    print(f"{label}: mean_kld={summ['mean_kld']:.3e} p99={summ['p99_kld']:.3e} top1={summ['top1_agree']*100:.2f}% "
          f"|lnPPL|={summ['abs_ln_ppl_ratio']:.2e} bit-identical={summ['bit_identical_rows']}/{n} "
          f"max|dlogit|={summ['max_abs_logit_diff']:.3g}  PASS={res['pass']}")


ap = argparse.ArgumentParser()
sub = ap.add_subparsers(dest="cmd", required=True)
d = sub.add_parser("dump")
d.add_argument("--engine", required=True); d.add_argument("--model", required=True)
d.add_argument("--split", default="dev", choices=["dev", "holdout"]); d.add_argument("--ub", type=int, required=True)
d.add_argument("--tag", default=""); d.add_argument("--extra-args", default="")
d.add_argument("--phase3-holdout", action="store_true"); d.add_argument("--allow-unfrozen", action="store_true")
c = sub.add_parser("compare")
c.add_argument("--ref", required=True); c.add_argument("--cand", required=True); c.add_argument("--label", default="")
c.add_argument("--allow-unfrozen", action="store_true")
a = ap.parse_args()
{"dump": cmd_dump, "compare": cmd_compare}[a.cmd](a)
