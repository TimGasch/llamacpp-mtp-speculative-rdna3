"""Measurement session driver (PROTOCOL §5.4).

A session = canary -> blocks (each block: start one engine's server, 2 warm-up requests,
N repetitions of a workload, stop server) -> canary. Blocks are listed in a plan so that
reference (R) and candidate (C) blocks can be interleaved (R C C R ...).

Workloads:
  S-greedy   chat prompts, 256 tokens, greedy
  S-sampled  chat prompts, 256 tokens, model-recommended sampling, fixed per-(prompt,rep) seeds
  L          long prompts (~4k/16k/32k), 256 tokens, greedy
  Q2         S-greedy + L prompts once, greedy, with top-20 log-probs (reference data for gate Q2)

Usage:
  python bench/session.py --tag NAME --split dev --plan '[{"engine":"ref-vulkan","model":"qwen35-9b","workload":"S-greedy","reps":3}, ...]'
All raw data goes to results/raw/<timestamp>_<tag>/ and is never edited afterwards.
"""
from __future__ import annotations

import argparse, json, subprocess, sys, time
from pathlib import Path

from common import (GREEDY, MODELS, N_PREDICT, ROOT, Server, derive_request_metrics, env_snapshot,
                    load_engine, manifest_check, model_sha_verified, new_session_dir, process_vram_mb,
                    split_dir, write_json)

CANARY_ENGINE, CANARY_MODEL = "ref-vulkan", "qwen35-9b"
CANARY_MAX_DRIFT = 0.03


def run_canary(sdir: Path, label: str) -> dict:
    eng = load_engine(CANARY_ENGINE)
    cmd = [str(ROOT / eng["bench"]), "-m", str(ROOT / MODELS[CANARY_MODEL]["path"]), "-ngl", "99",
           "-p", "0", "-n", "128", "-r", "3", "-o", "jsonl"]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT / Path(eng["bench"]).parent))
    (sdir / f"canary_{label}.jsonl").write_text(r.stdout, encoding="utf-8")
    (sdir / f"canary_{label}.stderr.txt").write_text(r.stderr, encoding="utf-8")
    rows = [json.loads(l) for l in r.stdout.splitlines() if l.strip()]
    return {"cmd": cmd, "avg_ts": rows[0]["avg_ts"], "stddev_ts": rows[0]["stddev_ts"], "samples_ts": rows[0].get("samples_ts")}


def workload_items(tokens: dict, workload: str) -> list[dict]:
    if workload in ("S-greedy", "S-sampled"):
        return tokens["prompts"]
    if workload == "L":
        return tokens["long"]
    if workload == "Q2":
        return tokens["prompts"] + tokens["long"]
    raise ValueError(workload)


def request_body(model_key: str, workload: str, item_idx: int, rep: int, prompt: list[int]) -> dict:
    body = {"prompt": prompt, "n_predict": N_PREDICT, "cache_prompt": False, "return_tokens": True,
            "n_probs": 0, "seed": 1000 + item_idx + 100 * rep}
    if workload == "S-sampled":
        body.update(MODELS[model_key]["sampling"])
    else:
        body.update(GREEDY)
    if workload == "Q2":
        body.update(n_probs=20, post_sampling_probs=False)
    return body


def run_block(sdir: Path, bi: int, blk: dict, tokens_by_model: dict, port: int) -> dict:
    eng = load_engine(blk["engine"])
    model = blk["model"]
    items = workload_items(tokens_by_model[model], blk["workload"])
    reps = blk.get("reps", 1 if blk["workload"] == "Q2" else 3)
    tag = f'b{bi:02d}_{blk["engine"]}_{model}_{blk["workload"]}'
    srv = Server(eng, model, port, sdir / f"{tag}.server.log")
    info = srv.start()
    info["vram_mb_after_load"] = process_vram_mb(info["pid"])
    out = sdir / f"{tag}.jsonl"
    try:
        with open(out, "w", encoding="utf-8") as f:
            # warm-up (discarded from stats but kept in the raw file, flagged)
            for w in range(2):
                it = items[w % len(items)]
                body = request_body(model, "S-greedy", 0, 0, it["tokens"])
                body["n_predict"] = 32
                rec = srv.stream_completion(body)
                rec.update(block=bi, warmup=True, item_id=it["id"])
                f.write(json.dumps(rec) + "\n")
            for rep in range(reps):
                for ii, it in enumerate(items):
                    body = request_body(model, blk["workload"], ii, rep, it["tokens"])
                    rec = srv.stream_completion(body)
                    rec.update(block=bi, warmup=False, rep=rep, item_id=it["id"],
                               category=it.get("category"), n_prompt=len(it["tokens"]),
                               request={k: v for k, v in body.items() if k != "prompt"},
                               metrics=derive_request_metrics(rec))
                    f.write(json.dumps(rec) + "\n")
                    f.flush()
                    m = rec["metrics"]
                    print(f'  [{tag} rep{rep}] {it["id"]:>18s} n_gen={m["n_gen"]:4d} '
                          f'ttft={m["ttft_ms"] or 0:8.1f}ms tg={m["tg_tps"] or 0:7.2f} t/s', flush=True)
        info["vram_mb_after_run"] = process_vram_mb(info["pid"])
    finally:
        srv.stop()
    info.update(block=bi, spec=blk, file=out.name, engine=eng)
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--split", default="dev", choices=["dev", "holdout"])
    ap.add_argument("--phase3-holdout", action="store_true")
    ap.add_argument("--plan", required=True, help="JSON list of blocks, or @file.json")
    ap.add_argument("--no-canary", action="store_true")
    ap.add_argument("--allow-unfrozen", action="store_true")
    ap.add_argument("--port", type=int, default=8090)
    a = ap.parse_args()

    tool = manifest_check(a.allow_unfrozen)
    plan = json.loads(Path(a.plan[1:]).read_text() if a.plan.startswith("@") else a.plan)
    split_dir(a.split, a.phase3_holdout, "session")          # guard + access log for holdout
    tok_dir = ROOT / "eval" / ("dev" if a.split == "dev" else "holdout_tokens")
    models = sorted({b["model"] for b in plan})
    tokens_by_model = {m: json.loads((tok_dir / f"tokens_{m}.json").read_text(encoding="utf-8")) for m in models}
    for m in models:
        model_sha_verified(m)

    sdir = new_session_dir(a.tag)
    meta = {"tag": a.tag, "split": a.split, "argv": sys.argv, "tooling": tool, "plan": plan,
            "env_start": env_snapshot(), "blocks": []}
    write_json(sdir / "session.json", meta)
    if not a.no_canary:
        meta["canary_start"] = run_canary(sdir, "start")
        print(f'canary start: {meta["canary_start"]["avg_ts"]:.2f} t/s', flush=True)
    for bi, blk in enumerate(plan):
        print(f"block {bi}: {blk}", flush=True)
        meta["blocks"].append(run_block(sdir, bi, blk, tokens_by_model, a.port))
        write_json(sdir / "session.json", meta)
    if not a.no_canary:
        meta["canary_end"] = run_canary(sdir, "end")
        s, e = meta["canary_start"]["avg_ts"], meta["canary_end"]["avg_ts"]
        meta["canary_drift"] = (e - s) / s
        meta["session_valid"] = abs(meta["canary_drift"]) <= CANARY_MAX_DRIFT
        print(f'canary end: {e:.2f} t/s  drift={meta["canary_drift"]*100:+.2f}%  valid={meta["session_valid"]}')
    meta["env_end"] = env_snapshot()
    write_json(sdir / "session.json", meta)
    print(f"session dir: {sdir}")


if __name__ == "__main__":
    main()
