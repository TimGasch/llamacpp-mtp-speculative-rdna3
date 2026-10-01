"""Tokenize an evaluation split for one model, using the REFERENCE engine's server
(its chat template via /apply-template and its tokenizer via /tokenize), so that every engine
receives byte-identical token IDs.

Outputs (per split, per model):
  eval/<split>/tokens_<model>.json         prompts / long prompts / Q1 segments as token IDs
  eval/<split>/q1_segments_<model>.txt     qdump input format

Usage: python bench/prepare_tokens.py --model qwen35-9b --split dev [--phase3-holdout]
"""
import argparse, json
from pathlib import Path

from common import ROOT, Server, load_engine, split_dir, model_sha_verified, write_json, manifest_check

Q1_SCORED_SHORT = 512       # scored positions per corpus segment (8 segments -> 4096)
Q1_LONG_PREFIX = 15360      # long segment: prefix tokens ...
Q1_LONG_SCORED = 1024       # ... followed by this many scored positions
REF_ENGINE = "ref-vulkan"

ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True)
ap.add_argument("--split", required=True, choices=["dev", "holdout"])
ap.add_argument("--phase3-holdout", action="store_true")
ap.add_argument("--port", type=int, default=8091)
ap.add_argument("--allow-unfrozen", action="store_true")
a = ap.parse_args()

tool = manifest_check(a.allow_unfrozen)
sdir = split_dir(a.split, a.phase3_holdout, "prepare_tokens")
rows = {p: [json.loads(l) for l in (sdir / f"{p}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
        for p in ("prompts", "corpus", "long")}

eng = load_engine(REF_ENGINE)
model_sha_verified(a.model)
srv = Server(eng, a.model, a.port, ROOT / "results" / f".prepare_tokens_{a.model}.log")
srv.start()
try:
    def tmpl(messages):
        st, r = srv.request("POST", "/apply-template", {"messages": messages})
        assert st == 200, r
        return r["prompt"]

    def tok(text, add_special, parse_special=True):
        st, r = srv.request("POST", "/tokenize", {"content": text, "add_special": add_special,
                                                  "parse_special": parse_special})
        assert st == 200, r
        return r["tokens"]

    def detok(tokens):
        st, r = srv.request("POST", "/detokenize", {"tokens": tokens})
        assert st == 200, r
        return r["content"]

    out = {"model": a.model, "split": a.split, "tokenizer_engine": REF_ENGINE, "tooling": tool,
           "prompts": [], "long": [], "q1_segments": []}

    # chat prompts (template adds the generation prompt; template text contains BOS if the model uses one)
    for p in rows["prompts"]:
        out["prompts"].append({"id": p["id"], "category": p["category"],
                               "tokens": tok(tmpl(p["messages"]), add_special=False)})

    for d in rows["long"]:
        body = tok(d["text"], add_special=False, parse_special=False)
        if d["purpose"] == "L":
            # size the excerpt so that the whole templated prompt is ~target_tokens
            overhead = len(tok(tmpl([{"role": "user", "content": d["task"]}]), add_special=False))
            k = d["target_tokens"] - overhead
            assert len(body) >= k, f'{d["id"]}: text too short ({len(body)} < {k})'
            excerpt = detok(body[:k])
            toks = tok(tmpl([{"role": "user", "content": excerpt + d["task"]}]), add_special=False)
            out["long"].append({"id": d["id"], "category": f'L-{d["target_tokens"]}', "tokens": toks})
        else:  # Q1-long: raw text, prefix + scored positions
            full = tok(d["text"], add_special=True, parse_special=False)
            n = Q1_LONG_PREFIX + 1 + Q1_LONG_SCORED
            assert len(full) >= n, f'{d["id"]}: too short'
            out["q1_segments"].append({"id": d["id"], "kind": "long", "n_prefix": Q1_LONG_PREFIX, "tokens": full[:n]})

    for c in rows["corpus"]:
        if c["kind"] == "chat":
            toks = tok(tmpl(c["messages"]), add_special=False)
        else:
            toks = tok(c["text"], add_special=True, parse_special=False)
        n = 1 + 1 + Q1_SCORED_SHORT
        assert len(toks) >= n, f'{c["id"]}: only {len(toks)} tokens'
        out["q1_segments"].append({"id": c["id"], "kind": c["kind"], "n_prefix": 1, "tokens": toks[:n]})
finally:
    srv.stop()

write_json(sdir.parent / a.split / f"tokens_{a.model}.json", out) if a.split == "dev" else None
if a.split == "holdout":   # holdout dir is read-only by design; derived files go next to it
    write_json(ROOT / "eval" / "holdout_tokens" / f"tokens_{a.model}.json", out)
segdir = ROOT / "eval" / ("dev" if a.split == "dev" else "holdout_tokens")
with open(segdir / f"q1_segments_{a.model}.txt", "w", encoding="utf-8") as f:
    for s in out["q1_segments"]:
        f.write(f'{s["id"]} {s["n_prefix"]} ' + " ".join(map(str, s["tokens"])) + "\n")
print(f"{a.model}/{a.split}: prompts={len(out['prompts'])} "
      f"prompt_lens={[len(p['tokens']) for p in out['prompts']]} "
      f"long={[(l['category'], len(l['tokens'])) for l in out['long']]} "
      f"q1_segments={len(out['q1_segments'])} scored={sum(len(s['tokens'])-1-s['n_prefix'] for s in out['q1_segments'])}")
