"""Q1 noise-envelope gate (PROTOCOL Amendment 1, A1.1).

Reads q1.py compare summaries:
  --envelope  the three stock-variant comparisons (V1 ub512, V2 ub4, V3 fa-off, each vs R ub=1)
  --cand      one or more candidate-path comparisons (each vs the same R ub=1 dump)
and writes the verdict to results/raw/q1/<label>.gate.json.

Usage: python bench/q1_gate.py --label L --envelope a.summary.json b.summary.json c.summary.json
                               --cand x.summary.json [y.summary.json ...]
"""
from __future__ import annotations

import argparse, json
from datetime import datetime
from pathlib import Path

from common import ROOT, manifest_check, write_json

ap = argparse.ArgumentParser()
ap.add_argument("--label", required=True)
ap.add_argument("--envelope", nargs=3, required=True)
ap.add_argument("--cand", nargs="+", required=True)
a = ap.parse_args()
tool = manifest_check()


def load(p):
    p = Path(p)
    if not p.is_absolute():
        p = ROOT / "results" / "raw" / "q1" / p
    return json.loads(p.read_text(encoding="utf-8"))


env = [load(p) for p in a.envelope]
refs = {e["ref"] for e in env}
assert len(refs) == 1, f"envelope comparisons use different references: {refs}"
E = {"mean_kld": max(e["summary"]["mean_kld"] for e in env),
     "p99_kld": max(e["summary"]["p99_kld"] for e in env),
     "top1_agree": min(e["summary"]["top1_agree"] for e in env),
     "abs_ln_ppl_ratio": max(e["summary"]["abs_ln_ppl_ratio"] for e in env)}
results = []
for p in a.cand:
    c = load(p)
    assert c["ref"] in refs, f"candidate {c['label']} compared against {c['ref']}, envelope uses {refs}"
    s = c["summary"]
    v = {"mean_kld": s["mean_kld"] <= E["mean_kld"], "p99_kld": s["p99_kld"] <= E["p99_kld"],
         "top1_agree": s["top1_agree"] >= E["top1_agree"],
         "abs_ln_ppl_ratio": s["abs_ln_ppl_ratio"] <= E["abs_ln_ppl_ratio"]}
    results.append({"cand": c["label"], "summary": {k: s[k] for k in E}, "verdict": v, "pass": all(v.values())})
    print(f"{c['label']}: " + " ".join(f"{k}={s[k]:.3e}{'<=' if k != 'top1_agree' else '>='}{E[k]:.3e}:{'ok' if v[k] else 'FAIL'}"
                                       for k in E) + f"  PASS={all(v.values())}")
res = {"label": a.label, "date": datetime.now().isoformat(), "tooling": tool, "rule": "PROTOCOL Amendment 1 (A1.1)",
       "envelope_sources": [e["label"] for e in env], "envelope": E, "candidates": results,
       "pass": all(r["pass"] for r in results)}
write_json(ROOT / "results" / "raw" / "q1" / f"{a.label}.gate.json", res)
print(f"envelope: {E}\nGATE {a.label}: PASS={res['pass']}")
