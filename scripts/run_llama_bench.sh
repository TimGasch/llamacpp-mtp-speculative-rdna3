#!/usr/bin/env bash
# Micro workload (PROTOCOL §5.3): run an engine's own llama-bench with FIXED arguments and store the
# raw JSONL + stderr + metadata unchanged under results/raw/<timestamp>_micro_<engine>_<model>/.
# Usage: scripts/run_llama_bench.sh <engine-name> <model-key> [extra llama-bench args...]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENGINE="$1"; MODEL="$2"; shift 2
case "$MODEL" in
  qwen35-9b)  MPATH="$ROOT/models/Qwen3.5-9B-Q4_K_M.gguf" ;;
  gemma4-e4b) MPATH="$ROOT/models/gemma-4-E4B-it-Q8_0.gguf" ;;
  *) echo "unknown model $MODEL"; exit 2 ;;
esac
BENCH_REL=$("$ROOT/.venv/Scripts/python.exe" -c "import json,sys;print(json.load(open(sys.argv[1]))['bench'])" "$(cygpath -w "$ROOT/configs/engines/$ENGINE.json")")
BENCH="$ROOT/$BENCH_REL"
OUT="$ROOT/results/raw/$(date +%Y%m%d-%H%M%S)_micro_${ENGINE}_${MODEL}"
mkdir -p "$OUT"
ARGS=(-m "$MPATH" -ngl 99 -p 512 -n 128 -d 0,4096,16384 -r 5 -o jsonl "$@")
{
  echo "date: $(date -Iseconds)"; echo "engine: $ENGINE"; echo "bench: $BENCH_REL"
  echo "bench_sha256: $(sha256sum "$BENCH" | cut -d' ' -f1)"; echo "model: $MODEL"
  echo "args: ${ARGS[*]}"
} > "$OUT/meta.txt"
( cd "$(dirname "$BENCH")" && "$BENCH" "${ARGS[@]}" ) > "$OUT/llama-bench.jsonl" 2> "$OUT/llama-bench.stderr.txt"
"$ROOT/.venv/Scripts/python.exe" - "$(cygpath -w "$OUT/llama-bench.jsonl")" <<'EOF'
import json, sys
for l in open(sys.argv[1]):
    r = json.loads(l)
    kind = f"pp{r['n_prompt']}" if r['n_prompt'] else f"tg{r['n_gen']}"
    print(f"{kind:>6s} @ d{r['n_depth']:<6d} {r['avg_ts']:9.2f} ± {r['stddev_ts']:.2f} t/s  backend={r.get('backends')}")
EOF
echo "raw: $OUT"
