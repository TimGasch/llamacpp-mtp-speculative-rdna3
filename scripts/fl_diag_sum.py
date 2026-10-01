"""Sum the fl_diag timer lines of a diag-host server log (DIAGNOSTIC ONLY).

Usage: python scripts/fl_diag_sum.py <server.log> [...]
Prints, per timer, the total count and the average wall time per call and per verified step.
"""
import re, sys
from collections import defaultdict

for path in sys.argv[1:]:
    tot, cnt = defaultdict(float), defaultdict(int)
    for line in open(path, encoding="utf-8", errors="replace"):
        m = re.match(r"fl_diag (\S+)\s+n=\s*(\d+) avg=\s*[\d.]+ ms total=\s*([\d.]+) ms", line.strip())
        if m:
            tot[m.group(1)] += float(m.group(3)); cnt[m.group(1)] += int(m.group(2))
    steps = cnt.get("iter", 0) or 1
    print(path)
    for k in tot:
        print(f"  {k:14s} n={cnt[k]:7d} avg/call={tot[k]/cnt[k]:8.3f} ms  per step={tot[k]/steps:8.3f} ms")
