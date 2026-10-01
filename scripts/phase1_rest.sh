#!/usr/bin/env bash
# Remaining Phase 1 measurements (build validation, micro workloads, bandwidth). Raw outputs only.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/Scripts/python.exe"
cd "$ROOT/bench"

# 1) Build validation (PROTOCOL 5.5): official prebuilt Vulkan b11284 vs own build, interleaved R C C R
"$PY" session.py --tag buildval --plan '[
 {"engine":"ref-vulkan","model":"qwen35-9b","workload":"S-greedy","reps":2},
 {"engine":"ref-official-vulkan","model":"qwen35-9b","workload":"S-greedy","reps":3},
 {"engine":"ref-official-vulkan","model":"gemma4-e4b","workload":"S-greedy","reps":3},
 {"engine":"ref-vulkan","model":"gemma4-e4b","workload":"S-greedy","reps":2}]' 2>&1 | grep -v '^  \['

# 2) Micro workloads (llama-bench pp512/tg128 at depth 0/4096/16384, 5 reps)
for e in ref-vulkan ref-official-vulkan; do
  for m in qwen35-9b gemma4-e4b; do
    bash "$ROOT/scripts/run_llama_bench.sh" "$e" "$m"
  done
done

# 3) Achievable bandwidth: test-backend-ops perf for mat-vec (n=1) cases, raw CSV
OUT="$ROOT/results/raw/$(date +%Y%m%d-%H%M%S)_bandwidth"
mkdir -p "$OUT"
( cd "$ROOT/build/ref-vulkan/bin" && ./test-backend-ops.exe perf -b Vulkan0 -o MUL_MAT -p 'n=1,' --output csv ) \
  > "$OUT/mul_mat_n1.csv" 2> "$OUT/mul_mat_n1.stderr.txt"
( cd "$ROOT/build/ref-vulkan/bin" && ./test-backend-ops.exe perf -b Vulkan0 -o CPY --output csv ) \
  > "$OUT/cpy.csv" 2> "$OUT/cpy.stderr.txt"
echo "bandwidth raw: $OUT"
echo PHASE1_REST_DONE
