"""Quality gate Q2 — free-running greedy generation vs. the reference (PROTOCOL §4.4).

Reference data: a session block with workload "Q2" (reference engine, greedy, top-20 log-probs).
Candidate data: any greedy block(s) (S-greedy, L or Q2) of the candidate engine.

At the first divergent position of each item:
  delta = logP_R(R's token) - logP_R(C's token), from R's top-20 log-probs at that position.
  delta > 0.25 nats  -> HARD divergence (gate: zero allowed)
  C's token not in R's top-20 -> delta >= logP_R(top1) - logP_R(top20); hard if that bound > 0.25,
                                 otherwise "undetermined" (counted as failing, conservative)
  divergence at a position where R has no log-prob entry (e.g. R stopped at EOS) -> "undetermined"

Usage: python bench/q2.py --ref <session>/<Q2 block>.jsonl --cand <session>/<block>.jsonl [...] --label L
"""
from __future__ import annotations

import argparse, json
from datetime import datetime
from pathlib import Path

from common import ROOT, manifest_check, write_json

HARD_DELTA = 0.25
OUT = ROOT / "results" / "raw" / "q2"


def load(paths):
    recs = {}
    for p in paths:
        for line in Path(p).read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r.get("warmup"):
                continue
            if r.get("request", {}).get("temperature", 0) not in (0, 0.0):
                continue                       # only greedy runs are comparable
            recs.setdefault(r["item_id"], []).append(r)
    return recs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--cand", required=True, nargs="+")
    ap.add_argument("--label", required=True)
    ap.add_argument("--allow-unfrozen", action="store_true")
    a = ap.parse_args()
    tool = manifest_check(a.allow_unfrozen)
    ref = load([a.ref])
    cand = load(a.cand)
    items, n_hard, n_undet, shares, exact = [], 0, 0, [], 0
    nondet = 0
    for iid, rr in ref.items():
        if iid not in cand:
            continue
        r = rr[0]
        cs = cand[iid]
        c_tokens = cs[0]["tokens"]
        deterministic = all(x["tokens"] == c_tokens for x in cs)
        nondet += (not deterministic)
        rt = r["tokens"]
        j = next((k for k in range(min(len(rt), len(c_tokens))) if rt[k] != c_tokens[k]), None)
        if j is None and len(rt) == len(c_tokens):
            exact += 1
            items.append({"item": iid, "diverged": False, "len_ref": len(rt), "cand_reps": len(cs),
                          "cand_deterministic": deterministic})
            shares.append(1.0)
            continue
        if j is None:
            j = min(len(rt), len(c_tokens))    # one sequence is a prefix of the other (EOS / length)
        shares.append(j / max(1, len(rt)))
        info = {"item": iid, "diverged": True, "pos": j, "len_ref": len(rt), "len_cand": len(c_tokens),
                "cand_reps": len(cs), "cand_deterministic": deterministic}
        if j < len(r["probs"]) and j < len(c_tokens):
            p = r["probs"][j]
            top = p["top_logprobs"]
            lp_r = top[0]["logprob"]
            cand_tok = c_tokens[j]
            hit = [t for t in top if t["id"] == cand_tok]
            if hit:
                delta = lp_r - hit[0]["logprob"]
                info.update(delta=delta, delta_exact=True, cls="hard" if delta > HARD_DELTA else "soft")
            else:
                bound = lp_r - top[-1]["logprob"]
                info.update(delta_lower_bound=bound, delta_exact=False,
                            cls="hard" if bound > HARD_DELTA else "undetermined")
            info.update(ref_token=rt[j] if j < len(rt) else None, cand_token=cand_tok,
                        ref_top1_logprob=lp_r, ref_top2_logprob=top[1]["logprob"] if len(top) > 1 else None)
        else:
            info.update(cls="undetermined", note="no reference log-probs at divergence position")
        n_hard += info["cls"] == "hard"
        n_undet += info["cls"] == "undetermined"
        items.append(info)
    res = {"label": a.label, "date": datetime.now().isoformat(), "ref": a.ref, "cand": a.cand, "tooling": tool,
           "hard_delta_nats": HARD_DELTA, "n_items": len(items), "n_exact_match": exact,
           "n_hard": n_hard, "n_undetermined": n_undet,
           "mean_identical_token_share": sum(shares) / max(1, len(shares)),
           "n_items_cand_nondeterministic": nondet,
           "pass": n_hard == 0 and n_undet == 0, "items": items}
    write_json(OUT / f"{a.label}.json", res)
    print(f"{a.label}: items={len(items)} exact={exact} hard={n_hard} undetermined={n_undet} "
          f"identical-token-share={res['mean_identical_token_share']*100:.1f}% nondet={nondet} PASS={res['pass']}")
    for it in items:
        if it["diverged"]:
            d = it.get("delta", it.get("delta_lower_bound"))
            print(f"   {it['item']:>18s} pos={it['pos']:4d} cls={it['cls']:12s} delta={d}")


if __name__ == "__main__":
    main()
