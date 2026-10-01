"""Post-hoc TTFT and pp noise estimate from existing session files (no new measurements).

For each short workload, the frozen session plan runs every engine in two blocks
(e.g. R in b00 with 3 passes and again in b05 with 2 passes). Comparing an engine's two blocks
with itself gives the TTFT ratio that pure run-to-run noise produces for identical code.
Per prompt: median TTFT (and engine-reported pp t/s) over the passes of each block, ratio second
block / first block.

Usage: python scripts/ttft_noise.py <out.json> <session_dir> [<session_dir> ...]
"""
import json, statistics, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bench"))
from common import derive_request_metrics  # noqa: E402

res = {"note": __doc__.strip().splitlines()[0], "sessions": {}}
for s in sys.argv[2:]:
    s = Path(s).resolve()
    blocks = defaultdict(list)  # (engine, workload) -> [block files in order]
    for f in sorted(s.glob("b??_*.jsonl")):
        _, eng, model, wl = f.stem.split("_", 3)
        blocks[(eng, wl)].append(f)
    out = {}
    for (eng, wl), files in sorted(blocks.items()):
        if len(files) != 2 or wl not in ("S-greedy", "S-sampled"):
            continue
        med, medpp = [], []
        for f in files:
            per, perpp = defaultdict(list), defaultdict(list)
            for line in f.read_text(encoding="utf-8").splitlines():
                r = json.loads(line)
                if r.get("warmup"):
                    continue
                dm = derive_request_metrics(r)
                per[r["item_id"]].append(dm["ttft_ms"])
                perpp[r["item_id"]].append(dm["pp_tps_engine"])
            med.append({k: statistics.median(v) for k, v in per.items()})
            medpp.append({k: statistics.median(v) for k, v in perpp.items()})
        ratios = {k: med[1][k] / med[0][k] for k in med[0] if k in med[1]}
        pp = {k: medpp[1][k] / medpp[0][k] for k in medpp[0] if k in medpp[1]}
        out[f"{eng}|{wl}"] = {"blocks": [f.name for f in files], "n_prompts": len(ratios),
                              "ttft_ratio_median": statistics.median(ratios.values()),
                              "ttft_ratio_min": min(ratios.values()), "ttft_ratio_max": max(ratios.values()),
                              "pp_ratio_median": statistics.median(pp.values()),
                              "pp_ratio_min": min(pp.values()), "pp_ratio_max": max(pp.values()),
                              "per_prompt": ratios, "per_prompt_pp": pp}
        print(f"{s.name} {eng:>12} {wl:<9} block2/block1 TTFT ratio: median {out[f'{eng}|{wl}']['ttft_ratio_median']:.3f} "
              f"min {min(ratios.values()):.3f} max {max(ratios.values()):.3f} | pp ratio median {statistics.median(pp.values()):.3f} "
              f"min {min(pp.values()):.3f} max {max(pp.values()):.3f}")
    res["sessions"][s.relative_to(ROOT).as_posix()] = out
Path(sys.argv[1]).write_text(json.dumps(res, indent=1), encoding="utf-8")
print("wrote", sys.argv[1])
