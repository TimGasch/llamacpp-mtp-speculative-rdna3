
### Qwen3.5-9B Q4_K_M — holdout, session `results/raw/20260930-222320_phase3-holdout-qwen35-9b`

Canary (llama-bench tg128, R): start 88.91 t/s, end 89.47 t/s, drift +0.63 %, session valid: True. Sources: `results/raw/20260930-222320_phase3-holdout-qwen35-9b/summary_vs_ref.json`, `results/raw/20260930-222320_phase3-holdout-qwen35-9b/summary_vs_stock.json`.

| Workload | Engine | tg aggregate t/s: median [IQR] (min–max), CV, n passes | Speedup vs R [95 % CI] | Speedup vs S [95 % CI] | TTFT median over prompts (ms) | TTFT ratio vs R (median / max over prompts) | pp ratio vs R (median / min) |
|---|---|---|---|---|---|---|---|
| S-greedy | ref-vulkan | 86.74 [86.73–86.89] (86.67–87.14), 0.22 %, n=5, outliers flagged: 87.14 | — | 0.613× [0.596, 0.632] | 166.6 | — | — |
| S-greedy | stock-best | 141.13 [140.02–141.63] (139.67–141.82), 0.68 %, n=5 | **1.630×** [1.582, 1.677] | — | 169.0 | 1.099 / 1.313 | 0.926 / 0.758 |
| S-greedy | final | 160.86 [160.48–160.97] (159.79–161.49), 0.39 %, n=5 | **1.858×** [1.782, 1.939] | 1.140× [1.120, 1.161] | 164.9 | 1.017 / 1.352 | 0.956 / 0.794 |
| S-sampled | ref-vulkan | 82.50 [82.09–82.63] (82.09–82.71), 0.36 %, n=5 | — | 0.669× [0.644, 0.695] | 175.9 | — | — |
| S-sampled | stock-best | 122.95 [122.71–123.13] (122.64–124.08), 0.47 %, n=5, outliers flagged: 124.08 | **1.495×** [1.440, 1.551] | — | 169.6 | 1.077 / 1.373 | 0.919 / 0.776 |
| S-sampled | final | 139.92 [139.66–141.60] (137.19–141.70), 1.31 %, n=5 | **1.685×** [1.591, 1.786] | 1.127× [1.097, 1.161] | 167.3 | 0.988 / 1.384 | 0.991 / 0.777 |
| L | ref-vulkan | 78.74 [78.74–78.76] (78.73–78.77), 0.02 %, n=5 | — | 0.627× [0.610, 0.659] | 12414.0 | — | — |
| L | stock-best | 125.58 [125.57–125.87] (125.24–126.27), 0.31 %, n=5 | **1.596×** [1.518, 1.639] | — | 13175.2 | 1.061 / 1.069 | 0.944 / 0.936 |
| L | final | 141.31 [141.19–141.66] (140.84–142.04), 0.32 %, n=5 | **1.801×** [1.758, 1.839] | 1.129× [1.105, 1.158] | 13210.8 | 1.064 / 1.073 | 0.941 / 0.933 |

Per-category S-greedy speedup final vs R (per-prompt tg ratios, min–max over the 3 prompts of each category): chat: 1.72–1.95; code: 1.75–2.07; creative: 1.64–1.79; math: 1.99–2.12; summarization: 1.76–2.06

Long-context per prompt (final vs R): L-4096: tg 154.8 vs 84.2 t/s, TTFT 3.33 vs 3.13 s; L-16384: tg 139.4 vs 79.3 t/s, TTFT 13.21 vs 12.41 s; L-32768: tg 133.0 vs 73.5 t/s, TTFT 29.49 vs 27.48 s

### Qwen3.5-9B Q4_K_M — holdout, session `results/raw/20261001-005450_phase3-holdout-eval2-qwen35-9b`

Canary (llama-bench tg128, R): start 89.48 t/s, end 89.61 t/s, drift +0.14 %, session valid: True. Sources: `results/raw/20261001-005450_phase3-holdout-eval2-qwen35-9b/summary_vs_ref.json`, `results/raw/20261001-005450_phase3-holdout-eval2-qwen35-9b/summary_vs_stock.json`.

| Workload | Engine | tg aggregate t/s: median [IQR] (min–max), CV, n passes | Speedup vs R [95 % CI] | Speedup vs S [95 % CI] | TTFT median over prompts (ms) | TTFT ratio vs R (median / max over prompts) | pp ratio vs R (median / min) |
|---|---|---|---|---|---|---|---|
| S-greedy | ref-vulkan | 87.51 [87.47–87.53] (87.43–87.61), 0.08 %, n=5, outliers flagged: 87.61 | — | 0.610× [0.593, 0.628] | 162.5 | — | — |
| S-greedy | stock-best | 143.20 [143.09–143.58] (142.76–143.93), 0.32 %, n=5 | **1.639×** [1.592, 1.687] | — | 164.9 | 1.022 / 1.072 | 0.947 / 0.929 |
| S-greedy | final-v2 | 166.68 [166.42–167.36] (165.39–167.82), 0.56 %, n=5 | **1.909×** [1.820, 2.005] | 1.165× [1.141, 1.190] | 163.6 | 1.028 / 1.124 | 0.955 / 0.912 |
| S-sampled | ref-vulkan | 82.96 [82.93–83.00] (82.90–83.01), 0.06 %, n=5 | — | 0.672× [0.647, 0.698] | 157.3 | — | — |
| S-sampled | stock-best | 123.22 [122.84–123.26] (122.77–124.24), 0.48 %, n=5, outliers flagged: 124.24 | **1.489×** [1.434, 1.545] | — | 162.1 | 1.026 / 1.061 | 0.955 / 0.928 |
| S-sampled | final-v2 | 140.61 [140.53–144.80] (139.75–144.97), 1.78 %, n=5 | **1.706×** [1.620, 1.795] | 1.146× [1.120, 1.172] | 165.1 | 1.056 / 1.079 | 0.945 / 0.922 |
| L | ref-vulkan | 79.22 [79.20–79.22] (79.12–79.27), 0.06 %, n=5, outliers flagged: 79.27, 79.12 | — | 0.629× [0.609, 0.662] | 12324.4 | — | — |
| L | stock-best | 126.19 [126.10–126.43] (125.55–126.47), 0.29 %, n=5, outliers flagged: 125.55 | **1.590×** [1.510, 1.642] | — | 13094.8 | 1.063 / 1.067 | 0.943 / 0.937 |
| L | final-v2 | 141.09 [139.10–141.22] (138.95–141.30), 0.85 %, n=5 | **1.766×** [1.685, 1.881] | 1.111× [1.067, 1.158] | 13134.4 | 1.066 / 1.070 | 0.940 / 0.935 |

Per-category S-greedy speedup final-v2 vs R (per-prompt tg ratios, min–max over the 3 prompts of each category): chat: 1.66–2.06; code: 1.75–2.09; creative: 1.67–1.89; math: 2.07–2.23; summarization: 1.88–2.22

Long-context per prompt (final-v2 vs R): L-4096: tg 159.8 vs 85.0 t/s, TTFT 3.27 vs 3.08 s; L-16384: tg 134.7 vs 79.9 t/s, TTFT 13.13 vs 12.32 s; L-32768: tg 129.1 vs 73.7 t/s, TTFT 29.31 vs 27.40 s

### Qwen3.5-9B Q4_K_M — holdout, session `results/raw/20261001-181639_phase3-holdout-eval3-qwen35-9b`

Canary (llama-bench tg128, R): start 89.33 t/s, end 89.34 t/s, drift +0.01 %, session valid: True. Sources: `results/raw/20261001-181639_phase3-holdout-eval3-qwen35-9b/summary_vs_ref.json`, `results/raw/20261001-181639_phase3-holdout-eval3-qwen35-9b/summary_vs_stock.json`.

| Workload | Engine | tg aggregate t/s: median [IQR] (min–max), CV, n passes | Speedup vs R [95 % CI] | Speedup vs S [95 % CI] | TTFT median over prompts (ms) | TTFT ratio vs R (median / max over prompts) | pp ratio vs R (median / min) |
|---|---|---|---|---|---|---|---|
| S-greedy | ref-vulkan | 87.42 [87.38–87.44] (87.28–87.67), 0.17 %, n=5, outliers flagged: 87.67 | — | 0.612× [0.594, 0.630] | 164.3 | — | — |
| S-greedy | stock-best | 142.78 [142.54–142.81] (141.86–143.63), 0.44 %, n=5, outliers flagged: 141.86, 143.63 | **1.635×** [1.587, 1.682] | — | 166.4 | 1.034 / 1.153 | 0.944 / 0.907 |
| S-greedy | final-v3 | 165.45 [164.82–165.57] (164.50–167.31), 0.66 %, n=5, outliers flagged: 167.31 | **1.895×** [1.806, 1.992] | 1.159× [1.136, 1.185] | 132.1 | 1.000 / 1.074 | 0.961 / 0.895 |
| S-sampled | ref-vulkan | 82.95 [82.88–83.00] (82.88–83.00), 0.07 %, n=5 | — | 0.672× [0.647, 0.698] | 162.5 | — | — |
| S-sampled | stock-best | 123.14 [122.79–123.28] (122.69–124.18), 0.48 %, n=5, outliers flagged: 124.18 | **1.489×** [1.434, 1.544] | — | 166.6 | 1.035 / 1.149 | 0.957 / 0.930 |
| S-sampled | final-v3 | 140.57 [140.51–145.52] (139.24–145.79), 2.17 %, n=5 | **1.709×** [1.630, 1.795] | 1.148× [1.122, 1.173] | 137.0 | 1.037 / 1.074 | 0.960 / 0.906 |
| L | ref-vulkan | 78.95 [78.91–78.98] (78.86–78.99), 0.07 %, n=5 | — | 0.628× [0.609, 0.661] | 12718.5 | — | — |
| L | stock-best | 125.87 [125.64–126.10] (125.30–126.20), 0.29 %, n=5 | **1.592×** [1.513, 1.642] | — | 13426.8 | 1.060 / 1.067 | 0.947 / 0.939 |
| L | final-v3 | 132.81 [132.81–132.89] (132.39–132.98), 0.17 %, n=5, outliers flagged: 132.39 | **1.682×** [1.635, 1.768] | 1.056× [1.009, 1.087] | 13033.7 | 1.025 / 1.036 | 0.976 / 0.960 |

Per-category S-greedy speedup final-v3 vs R (per-prompt tg ratios, min–max over the 3 prompts of each category): chat: 1.63–2.06; code: 1.74–2.06; creative: 1.68–1.87; math: 2.05–2.23; summarization: 1.86–2.20

Long-context per prompt (final-v3 vs R): L-4096: tg 149.8 vs 84.7 t/s, TTFT 3.26 vs 3.15 s; L-16384: tg 130.0 vs 79.5 t/s, TTFT 13.03 vs 12.72 s; L-32768: tg 121.6 vs 73.4 t/s, TTFT 28.79 vs 28.20 s

### Gemma 4 E4B Q8_0 — holdout, session `results/raw/20260930-230128_phase3-holdout-gemma4-e4b`

Canary (llama-bench tg128, R): start 89.49 t/s, end 89.51 t/s, drift +0.02 %, session valid: True. Sources: `results/raw/20260930-230128_phase3-holdout-gemma4-e4b/summary_vs_ref.json`, `results/raw/20260930-230128_phase3-holdout-gemma4-e4b/summary_vs_stock.json`.

| Workload | Engine | tg aggregate t/s: median [IQR] (min–max), CV, n passes | Speedup vs R [95 % CI] | Speedup vs S [95 % CI] | TTFT median over prompts (ms) | TTFT ratio vs R (median / max over prompts) | pp ratio vs R (median / min) |
|---|---|---|---|---|---|---|---|
| S-greedy | ref-vulkan | 79.60 [79.53–79.74] (79.41–79.95), 0.26 %, n=5 | — | 0.481× [0.449, 0.514] | 81.4 | — | — |
| S-greedy | stock-best | 165.89 [165.48–165.95] (165.40–165.98), 0.17 %, n=5 | **2.078×** [1.944, 2.227] | — | 88.6 | 1.006 / 1.231 | 0.985 / 0.867 |
| S-greedy | final | 164.30 [163.42–165.53] (158.95–166.10), 1.73 %, n=5, outliers flagged: 158.95 | **2.066×** [1.932, 2.217] | 0.994× [0.992, 0.996] | 89.8 | 1.089 / 1.395 | 0.964 / 0.884 |
| S-sampled | ref-vulkan | 79.66 [79.64–79.79] (79.62–79.85), 0.13 %, n=5 | — | 0.512× [0.476, 0.547] | 84.0 | — | — |
| S-sampled | stock-best | 157.46 [151.51–157.67] (151.47–157.79), 2.17 %, n=5 | **1.955×** [1.827, 2.096] | — | 81.7 | 1.024 / 1.436 | 0.979 / 0.791 |
| S-sampled | final | 156.56 [151.45–157.77] (151.28–157.85), 2.15 %, n=5 | **1.956×** [1.827, 2.102] | 1.001× [0.999, 1.002] | 92.2 | 1.080 / 1.361 | 0.969 / 0.855 |
| L | ref-vulkan | 66.93 [66.93–67.22] (66.78–67.31), 0.33 %, n=5 | — | 0.557× [0.542, 0.580] | 20450.4 | — | — |
| L | stock-best | 120.05 [119.83–120.23] (119.83–120.90), 0.37 %, n=5, outliers flagged: 120.90 | **1.795×** [1.724, 1.845] | — | 20576.9 | 1.006 / 1.017 | 0.994 / 0.992 |
| L | final | 120.51 [120.44–121.48] (120.03–121.66), 0.59 %, n=5 | **1.802×** [1.731, 1.848] | 1.004× [1.002, 1.006] | 20572.5 | 1.004 / 1.006 | 0.993 / 0.989 |

Per-category S-greedy speedup final vs R (per-prompt tg ratios, min–max over the 3 prompts of each category): chat: 1.78–2.00; code: 2.00–2.37; creative: 1.72–1.78; math: 2.34–2.50; summarization: 1.95–2.42

Long-context per prompt (final vs R): L-4096: tg 135.4 vs 73.3 t/s, TTFT 2.46 vs 2.45 s; L-16384: tg 115.8 vs 66.9 t/s, TTFT 20.57 vs 20.45 s; L-32768: tg 112.9 vs 61.6 t/s, TTFT 71.95 vs 71.72 s

### Gemma 4 E4B Q8_0 — holdout, session `results/raw/20261001-185318_phase3-holdout-eval3-gemma4-e4b`

Canary (llama-bench tg128, R): start 89.39 t/s, end 88.77 t/s, drift -0.70 %, session valid: True. Sources: `results/raw/20261001-185318_phase3-holdout-eval3-gemma4-e4b/summary_vs_ref.json`, `results/raw/20261001-185318_phase3-holdout-eval3-gemma4-e4b/summary_vs_stock.json`.

| Workload | Engine | tg aggregate t/s: median [IQR] (min–max), CV, n passes | Speedup vs R [95 % CI] | Speedup vs S [95 % CI] | TTFT median over prompts (ms) | TTFT ratio vs R (median / max over prompts) | pp ratio vs R (median / min) |
|---|---|---|---|---|---|---|---|
| S-greedy | ref-vulkan | 80.00 [79.98–80.18] (79.94–80.21), 0.15 %, n=5 | — | 0.483× [0.450, 0.516] | 86.9 | — | — |
| S-greedy | stock-best | 165.80 [165.72–165.95] (165.61–166.00), 0.10 %, n=5 | **2.072×** [1.938, 2.221] | — | 89.2 | 1.024 / 1.201 | 0.991 / 0.947 |
| S-greedy | final-v3 | 164.34 [163.83–166.03] (159.08–166.31), 1.77 %, n=5, outliers flagged: 159.08 | **2.060×** [1.926, 2.211] | 0.994× [0.992, 0.996] | 94.1 | 1.007 / 1.092 | 1.000 / 0.938 |
| S-sampled | ref-vulkan | 79.92 [79.90–80.12] (79.83–80.13), 0.17 %, n=5 | — | 0.513× [0.477, 0.548] | 87.7 | — | — |
| S-sampled | stock-best | 157.20 [151.72–157.76] (151.45–157.76), 2.12 %, n=5 | **1.951×** [1.823, 2.092] | — | 91.2 | 1.009 / 1.104 | 0.984 / 0.946 |
| S-sampled | final-v3 | 156.32 [151.80–157.73] (151.44–157.99), 2.07 %, n=5 | **1.951×** [1.823, 2.097] | 1.000× [0.998, 1.002] | 91.7 | 0.996 / 1.132 | 0.993 / 0.958 |
| L | ref-vulkan | 66.92 [66.81–66.95] (66.30–67.01), 0.43 %, n=5, outliers flagged: 66.30 | — | 0.553× [0.541, 0.574] | 20993.7 | — | — |
| L | stock-best | 120.97 [120.77–121.01] (120.47–121.12), 0.21 %, n=5 | **1.809×** [1.741, 1.850] | — | 21096.5 | 1.005 / 1.012 | 0.994 / 0.985 |
| L | final-v3 | 120.82 [120.82–120.84] (119.85–121.11), 0.40 %, n=5, outliers flagged: 121.11, 119.85 | **1.806×** [1.735, 1.850] | 0.998× [0.996, 1.000] | 21087.7 | 1.004 / 1.020 | 0.996 / 0.984 |

Per-category S-greedy speedup final-v3 vs R (per-prompt tg ratios, min–max over the 3 prompts of each category): chat: 1.78–1.99; code: 1.99–2.37; creative: 1.70–1.77; math: 2.35–2.49; summarization: 1.94–2.42

Long-context per prompt (final-v3 vs R): L-4096: tg 135.7 vs 73.4 t/s, TTFT 2.51 vs 2.46 s; L-16384: tg 116.0 vs 66.9 t/s, TTFT 21.09 vs 20.99 s; L-32768: tg 113.1 vs 61.5 t/s, TTFT 74.01 vs 73.85 s

### Quality gates on the holdout corpus

**Q1 Qwen3.5-9B Q4_K_M** (`results/raw/q1/gate_holdout_qwen35-9b_final-v3.gate.json`), envelope: mean KLD ≤ 5.137e-04, p99 ≤ 4.045e-03, top-1 ≥ 98.93 %, |lnPPL| ≤ 8.45e-04. Gate PASS: **False**

| Candidate path | mean KLD | p99 KLD | top-1 | abs(ln PPL ratio) | pass |
|---|---|---|---|---|---|
| holdout_final-v3_qwen35-9b_ub1 | 0.000e+00 | 0.000e+00 | 100.00 % | 0.00e+00 | True |
| holdout_final-v3_qwen35-9b_ub4 | 3.689e-04 | 3.273e-03 | 99.06 % | 3.15e-04 | True |
| holdout_final-v3_qwen35-9b_ub512 | 5.137e-04 | 4.045e-03 | 98.93 % | 4.25e-04 | True |
| holdout_final-v3_qwen35-9b_ub16 | 5.206e-04 | 4.269e-03 | 98.93 % | 1.79e-04 | False |

**Q1 Qwen3.5-9B Q4_K_M** (`results/raw/q1/gate_holdout_qwen35-9b_final.gate.json`), envelope: mean KLD ≤ 5.137e-04, p99 ≤ 4.045e-03, top-1 ≥ 98.93 %, |lnPPL| ≤ 8.45e-04. Gate PASS: **True**

| Candidate path | mean KLD | p99 KLD | top-1 | abs(ln PPL ratio) | pass |
|---|---|---|---|---|---|
| holdout_final_qwen35-9b_ub1 | 0.000e+00 | 0.000e+00 | 100.00 % | 0.00e+00 | True |
| holdout_final_qwen35-9b_ub4 | 3.689e-04 | 3.273e-03 | 99.06 % | 3.15e-04 | True |
| holdout_final_qwen35-9b_ub512 | 5.137e-04 | 4.045e-03 | 98.93 % | 4.25e-04 | True |

**Q1 Qwen3.5-9B Q4_K_M** (`results/raw/q1/gate_holdout_qwen35-9b_stock-ub16.gate.json`), envelope: mean KLD ≤ 5.137e-04, p99 ≤ 4.045e-03, top-1 ≥ 98.93 %, |lnPPL| ≤ 8.45e-04. Gate PASS: **False**

| Candidate path | mean KLD | p99 KLD | top-1 | abs(ln PPL ratio) | pass |
|---|---|---|---|---|---|
| holdout_stock-ub16_qwen35-9b | 5.206e-04 | 4.269e-03 | 98.93 % | 1.79e-04 | False |

**Q1 Gemma 4 E4B Q8_0** (`results/raw/q1/gate_holdout_gemma4-e4b_final-v3.gate.json`), envelope: mean KLD ≤ 1.749e-03, p99 ≤ 2.107e-02, top-1 ≥ 98.36 %, |lnPPL| ≤ 2.44e-03. Gate PASS: **False**

| Candidate path | mean KLD | p99 KLD | top-1 | abs(ln PPL ratio) | pass |
|---|---|---|---|---|---|
| holdout_final-v3_gemma4-e4b_ub1 | 0.000e+00 | 0.000e+00 | 100.00 % | 0.00e+00 | True |
| holdout_final-v3_gemma4-e4b_ub4 | 1.665e-03 | 1.907e-02 | 98.48 % | 2.44e-03 | True |
| holdout_final-v3_gemma4-e4b_ub512 | 1.749e-03 | 2.107e-02 | 98.36 % | 1.85e-03 | True |
| holdout_final-v3_gemma4-e4b_ub16 | 2.325e-03 | 3.129e-02 | 98.55 % | 2.02e-04 | False |

**Q1 Gemma 4 E4B Q8_0** (`results/raw/q1/gate_holdout_gemma4-e4b_final.gate.json`), envelope: mean KLD ≤ 1.749e-03, p99 ≤ 2.107e-02, top-1 ≥ 98.36 %, |lnPPL| ≤ 2.44e-03. Gate PASS: **True**

| Candidate path | mean KLD | p99 KLD | top-1 | abs(ln PPL ratio) | pass |
|---|---|---|---|---|---|
| holdout_final_gemma4-e4b_ub1 | 0.000e+00 | 0.000e+00 | 100.00 % | 0.00e+00 | True |
| holdout_final_gemma4-e4b_ub4 | 1.665e-03 | 1.907e-02 | 98.48 % | 2.44e-03 | True |
| holdout_final_gemma4-e4b_ub512 | 1.749e-03 | 2.107e-02 | 98.36 % | 1.85e-03 | True |

**Q1 Gemma 4 E4B Q8_0** (`results/raw/q1/gate_holdout_gemma4-e4b_stock-ub16.gate.json`), envelope: mean KLD ≤ 1.749e-03, p99 ≤ 2.107e-02, top-1 ≥ 98.36 %, |lnPPL| ≤ 2.44e-03. Gate PASS: **False**

| Candidate path | mean KLD | p99 KLD | top-1 | abs(ln PPL ratio) | pass |
|---|---|---|---|---|---|
| holdout_stock-ub16_gemma4-e4b | 2.325e-03 | 3.129e-02 | 98.55 % | 2.02e-04 | False |

**Q2** `results/raw/q2/holdout_eval2_final-v2_qwen35-9b.json`: items 18, exact full-sequence matches 7, hard divergences **0**, undetermined 0, mean identical-token share 74.5 %, PASS **True**
**Q2** `results/raw/q2/holdout_eval3_final-v3_gemma4-e4b.json`: items 18, exact full-sequence matches 4, hard divergences **0**, undetermined 0, mean identical-token share 58.8 %, PASS **True**
**Q2** `results/raw/q2/holdout_eval3_final-v3_qwen35-9b.json`: items 18, exact full-sequence matches 8, hard divergences **0**, undetermined 0, mean identical-token share 75.3 %, PASS **True**
**Q2** `results/raw/q2/holdout_final_gemma4-e4b.json`: items 18, exact full-sequence matches 4, hard divergences **0**, undetermined 0, mean identical-token share 58.8 %, PASS **True**
**Q2** `results/raw/q2/holdout_final_qwen35-9b.json`: items 18, exact full-sequence matches 7, hard divergences **0**, undetermined 0, mean identical-token share 73.0 %, PASS **True**

### Plain decoding without speculation (llama-bench, 5 repetitions, mean ± stddev)

| Model | Test | R: stock b11284 (t/s) | Final build (t/s) | Final / R | Source |
|---|---|---|---|---|---|
| Qwen3.5-9B Q4_K_M | pp512 @ depth 0 | 1438.14 ± 13.79 | 1431.66 ± 9.76 | 0.995 | `results/raw/20261001-013721_micro_ref-vulkan_qwen35-9b`, `results/raw/20261001-014050_micro_final_qwen35-9b` |
| Qwen3.5-9B Q4_K_M | tg128 @ depth 0 | 89.75 ± 0.08 | 89.67 ± 0.07 | 0.999 | `results/raw/20261001-013721_micro_ref-vulkan_qwen35-9b`, `results/raw/20261001-014050_micro_final_qwen35-9b` |
| Qwen3.5-9B Q4_K_M | pp512 @ depth 4096 | 1343.67 ± 6.34 | 1335.77 ± 14.21 | 0.994 | `results/raw/20261001-013721_micro_ref-vulkan_qwen35-9b`, `results/raw/20261001-014050_micro_final_qwen35-9b` |
| Qwen3.5-9B Q4_K_M | tg128 @ depth 4096 | 86.86 ± 0.07 | 86.71 ± 0.07 | 0.998 | `results/raw/20261001-013721_micro_ref-vulkan_qwen35-9b`, `results/raw/20261001-014050_micro_final_qwen35-9b` |
| Qwen3.5-9B Q4_K_M | pp512 @ depth 16384 | 1137.08 ± 6.65 | 1127.94 ± 3.67 | 0.992 | `results/raw/20261001-013721_micro_ref-vulkan_qwen35-9b`, `results/raw/20261001-014050_micro_final_qwen35-9b` |
| Qwen3.5-9B Q4_K_M | tg128 @ depth 16384 | 81.75 ± 0.07 | 81.67 ± 0.08 | 0.999 | `results/raw/20261001-013721_micro_ref-vulkan_qwen35-9b`, `results/raw/20261001-014050_micro_final_qwen35-9b` |
| Gemma 4 E4B Q8_0 | pp512 @ depth 0 | 3000.43 ± 25.38 | 3010.43 ± 22.89 | 1.003 | `results/raw/20261001-013832_micro_ref-vulkan_gemma4-e4b`, `results/raw/20261001-014204_micro_final_gemma4-e4b` |
| Gemma 4 E4B Q8_0 | tg128 @ depth 0 | 82.93 ± 0.08 | 82.94 ± 0.07 | 1.000 | `results/raw/20261001-013832_micro_ref-vulkan_gemma4-e4b`, `results/raw/20261001-014204_micro_final_gemma4-e4b` |
| Gemma 4 E4B Q8_0 | pp512 @ depth 4096 | 1197.07 ± 3.88 | 1194.47 ± 2.18 | 0.998 | `results/raw/20261001-013832_micro_ref-vulkan_gemma4-e4b`, `results/raw/20261001-014204_micro_final_gemma4-e4b` |
| Gemma 4 E4B Q8_0 | tg128 @ depth 4096 | 75.78 ± 0.21 | 75.89 ± 0.21 | 1.001 | `results/raw/20261001-013832_micro_ref-vulkan_gemma4-e4b`, `results/raw/20261001-014204_micro_final_gemma4-e4b` |
| Gemma 4 E4B Q8_0 | pp512 @ depth 16384 | 443.15 ± 2.15 | 441.64 ± 1.18 | 0.997 | `results/raw/20261001-013832_micro_ref-vulkan_gemma4-e4b`, `results/raw/20261001-014204_micro_final_gemma4-e4b` |
| Gemma 4 E4B Q8_0 | tg128 @ depth 16384 | 69.16 ± 0.15 | 69.19 ± 0.15 | 1.000 | `results/raw/20261001-013832_micro_ref-vulkan_gemma4-e4b`, `results/raw/20261001-014204_micro_final_gemma4-e4b` |
