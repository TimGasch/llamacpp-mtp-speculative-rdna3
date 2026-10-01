"""Generate the Phase 3 result tables for REPORT.md directly from measurement files.

Every number printed here is read from a JSON file under results/raw/ whose path is printed next
to the table, so the report contains no hand-typed measurement values.

Usage: python scripts/make_report_tables.py <out.md>
"""
import glob, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "results" / "raw"
out = []


def rel(p):
    return Path(p).relative_to(ROOT).as_posix()


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


MODELS = {"qwen35-9b": "Qwen3.5-9B Q4_K_M", "gemma4-e4b": "Gemma 4 E4B Q8_0"}
ENG = {"ref-vulkan": "R: stock llama.cpp b11284, no speculation (primary reference)",
       "stock-best": "S: stock llama.cpp b11284 + its built-in MTP speculation (secondary reference)",
       "final": "C: final candidate (patches 0001-0003 + reduced-vocab MTP head for Qwen)"}

SESSIONS = []
for m in MODELS:
    for tag, label in ((f"phase3-holdout-{m}", "evaluation #1"), (f"phase3-holdout-eval2-{m}", "evaluation #2 (after Phase 2b, dev-only decisions)"),
                       (f"phase3-holdout-eval3-{m}", "evaluation #3 (after Phase 2c, dev-only decisions)")):
        found = sorted(glob.glob(str(R / f"*_{tag}")))
        if found and (Path(found[-1]) / "summary_vs_stock.json").exists():
            SESSIONS.append((m, found[-1], label))
for m, s, label in SESSIONS:
    mname = MODELS[m]
    meta = load(Path(s) / "session.json")
    vr = load(Path(s) / "summary_vs_ref.json")["groups"]
    vs = load(Path(s) / "summary_vs_stock.json")["groups"]
    out.append(f"\n### {mname} — holdout, session `{rel(s)}`\n")
    out.append(f"Canary (llama-bench tg128, R): start {meta['canary_start']['avg_ts']:.2f} t/s, end {meta['canary_end']['avg_ts']:.2f} t/s, "
               f"drift {100*meta['canary_drift']:+.2f} %, session valid: {meta['session_valid']}. "
               f"Sources: `{rel(Path(s) / 'summary_vs_ref.json')}`, `{rel(Path(s) / 'summary_vs_stock.json')}`.\n")
    out.append("| Workload | Engine | tg aggregate t/s: median [IQR] (min–max), CV, n passes | Speedup vs R [95 % CI] | Speedup vs S [95 % CI] | TTFT median over prompts (ms) | TTFT ratio vs R (median / max over prompts) | pp ratio vs R (median / min) |")
    out.append("|---|---|---|---|---|---|---|---|")
    for w in ("S-greedy", "S-sampled", "L"):
        for e in ("ref-vulkan", "stock-best", "final", "final-v2", "final-v3"):
            g = vr.get(f"{e}|{m}|{w}")
            if not g:
                continue
            a = f"{g['tg_agg_median']:.2f} [{g['tg_agg_q1']:.2f}–{g['tg_agg_q3']:.2f}] ({g['tg_agg_min']:.2f}–{g['tg_agg_max']:.2f}), {100*(g['tg_agg_cv'] or 0):.2f} %, n={g['n_passes']}"
            if g.get("tg_agg_outliers"):
                a += f", outliers flagged: {', '.join(f'{x:.2f}' for x in g['tg_agg_outliers'])}"
            b = g.get("vs_baseline")
            sr = f"**{b['tg_speedup']:.3f}×** [{b['tg_speedup_ci95'][0]:.3f}, {b['tg_speedup_ci95'][1]:.3f}]" if b else "—"
            gs = vs.get(f"{e}|{m}|{w}", {}).get("vs_baseline")
            ss = f"{gs['tg_speedup']:.3f}× [{gs['tg_speedup_ci95'][0]:.3f}, {gs['tg_speedup_ci95'][1]:.3f}]" if gs else "—"
            tt = f"{b['ttft_ratio_median']:.3f} / {b['ttft_ratio_max']:.3f}" if b else "—"
            pp = f"{b['pp_ratio_median']:.3f} / {b['pp_ratio_min']:.3f}" if b else "—"
            out.append(f"| {w} | {e} | {a} | {sr} | {ss} | {g['ttft_ms_median_over_prompts']:.1f} | {tt} | {pp} |")
    # per-category speedups (S-greedy, C vs R)
    ce = next(e for e in ("final-v3", "final-v2", "final") if f"{e}|{m}|S-greedy" in vr)
    g = vr.get(f"{ce}|{m}|S-greedy", {}).get("vs_baseline")
    toks = load(ROOT / "eval" / "holdout_tokens" / f"tokens_{m}.json")
    cat = {p["id"]: p["category"] for p in toks["prompts"]}
    cat.update({l["id"]: l["category"] for l in toks["long"]})
    if g:
        per = {}
        for iid, v in g["per_prompt_tg_speedup"].items():
            per.setdefault(cat.get(iid, "?"), []).append(v)
        out.append(f"\nPer-category S-greedy speedup {ce} vs R (per-prompt tg ratios, min–max over the 3 prompts of each category): " +
                   "; ".join(f"{c}: {min(v):.2f}–{max(v):.2f}" for c, v in sorted(per.items())))
    gl = vr.get(f"{ce}|{m}|L", {}).get("vs_baseline")
    rl = vr.get(f"ref-vulkan|{m}|L", {}).get("per_prompt", {})
    cl = vr.get(f"{ce}|{m}|L", {}).get("per_prompt", {})
    if gl:
        out.append(f"\nLong-context per prompt ({ce} vs R): " + "; ".join(
            f"{cat.get(i,i)}: tg {cl[i]['tg_tps_med']:.1f} vs {rl[i]['tg_tps_med']:.1f} t/s, TTFT {cl[i]['ttft_ms_med']/1000:.2f} vs {rl[i]['ttft_ms_med']/1000:.2f} s"
            for i in sorted(cl) if i in rl))

# quality gates
out.append("\n### Quality gates on the holdout corpus\n")
for m, mname in MODELS.items():
    for f in sorted(glob.glob(str(R / "q1" / f"gate_holdout_{m}_*.gate.json"))):
        d = load(f)
        E = d["envelope"]
        out.append(f"**Q1 {mname}** (`{rel(f)}`), envelope: mean KLD ≤ {E['mean_kld']:.3e}, p99 ≤ {E['p99_kld']:.3e}, "
                   f"top-1 ≥ {100*E['top1_agree']:.2f} %, |lnPPL| ≤ {E['abs_ln_ppl_ratio']:.2e}. Gate PASS: **{d['pass']}**\n")
        out.append("| Candidate path | mean KLD | p99 KLD | top-1 | abs(ln PPL ratio) | pass |")
        out.append("|---|---|---|---|---|---|")
        for c in d["candidates"]:
            s = c["summary"]
            out.append(f"| {c['cand']} | {s['mean_kld']:.3e} | {s['p99_kld']:.3e} | {100*s['top1_agree']:.2f} % | {s['abs_ln_ppl_ratio']:.2e} | {c['pass']} |")
        out.append("")
for f in sorted(glob.glob(str(R / "q2" / "holdout_*.json"))):
    d = load(f)
    out.append(f"**Q2** `{rel(f)}`: items {d['n_items']}, exact full-sequence matches {d['n_exact_match']}, hard divergences **{d['n_hard']}**, "
               f"undetermined {d['n_undetermined']}, mean identical-token share {100*d['mean_identical_token_share']:.1f} %, PASS **{d['pass']}**")
# micro workload: plain (non-speculative) llama-bench, reference vs final build
out.append("\n### Plain decoding without speculation (llama-bench, 5 repetitions, mean ± stddev)\n")
out.append("| Model | Test | R: stock b11284 (t/s) | Final build (t/s) | Final / R | Source |")
out.append("|---|---|---|---|---|---|")
for m, mname in MODELS.items():
    rd = sorted(glob.glob(str(R / f"*_micro_ref-vulkan_{m}")))
    fd = sorted(glob.glob(str(R / f"*_micro_final_{m}")))
    if not rd or not fd:
        continue
    def rows(d):
        res = {}
        for l in (Path(d) / "llama-bench.jsonl").read_text(encoding="utf-8").splitlines():
            r = json.loads(l)
            k = (f"pp{r['n_prompt']}" if r["n_prompt"] else f"tg{r['n_gen']}") + f" @ depth {r['n_depth']}"
            res[k] = (r["avg_ts"], r["stddev_ts"])
        return res
    a, b = rows(rd[-1]), rows(fd[-1])
    for k in a:
        if k in b:
            out.append(f"| {mname} | {k} | {a[k][0]:.2f} ± {a[k][1]:.2f} | {b[k][0]:.2f} ± {b[k][1]:.2f} | {b[k][0]/a[k][0]:.3f} | `{rel(rd[-1])}`, `{rel(fd[-1])}` |")
Path(sys.argv[1]).write_text("\n".join(out) + "\n", encoding="utf-8")
print(f"wrote {sys.argv[1]} ({len(out)} lines)")
