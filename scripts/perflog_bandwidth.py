"""Effective weight bandwidth of MUL_MAT_VEC ops in a GGML_VK_PERF_LOGGER log (derived numbers).

For each MUL_MAT_VEC line: weight bytes = m * k * bytes_per_weight(type), GB/s = bytes / time.
The perf logger synchronizes after every op, so small ops are inflated; large mat-vecs are not much affected.
Usage: python scripts/perflog_bandwidth.py <perflog> <first_line> <last_line> <out.json>
"""
import json, re, sys

BPW = {"q4_K": 144 / 256, "q5_K": 176 / 256, "q6_K": 210 / 256, "q8_0": 34 / 32}
path, a, b, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
lines = open(path, encoding="utf-8", errors="replace").read().splitlines()[a - 1:b]
rows = []
for l in lines:
    m = re.match(r"MUL_MAT_VEC (\w+) m=(\d+) n=(\d+) k=(\d+): (\d+) x ([\d.]+) us", l)
    if m and m.group(1) in BPW:
        t, M, N, K, cnt, us = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5)), float(m.group(6))
        byts = M * K * BPW[t]
        rows.append({"type": t, "m": M, "n": N, "k": K, "count": cnt, "us_per_call": us, "weight_MB": byts / 1e6, "GBps": byts / us / 1e3})
        print(f"{t} m={M} n={N} k={K}: {us:8.1f} us  {byts/1e6:7.1f} MB  {byts/us/1e3:6.0f} GB/s")
json.dump({"source": path, "lines": [a, b], "note": __doc__.strip().splitlines()[0], "rows": rows}, open(out, "w"), indent=1)
