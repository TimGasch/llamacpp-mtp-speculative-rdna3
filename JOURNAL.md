# JOURNAL

Chronological log. Every entry records: hypothesis → change → measurement (numbers only from
files under `results/raw/`) → conclusion. Failures and dead ends are logged with the same care
as successes.

---

## 2026-09-30 — Entry 000 — Phase 0: survey and protocol draft

**What:** Read-only survey of the machine, directory layout created, PROTOCOL.md drafted.

**Findings (raw output in `env/`):**
- GPU: AMD Radeon RX 7800 XT (PCI device 0x747E), Windows driver 32.0.31041.1004 (dated
  2026-08-17), Vulkan driverInfo "26.8.1 (LLPC)", Vulkan API 1.4.349. The following device
  extensions are relevant:
  - `VK_KHR_cooperative_matrix`
  - `VK_KHR_shader_integer_dot_product`
  - `VK_KHR_shader_bfloat16`
  - `VK_EXT_subgroup_size_control` (subgroup 32–64)
  - `VK_AMD_shader_core_properties2`
  - `VK_EXT_memory_budget`
  - `maxComputeSharedMemorySize` = 32768
- CPU: Ryzen 5 7500F, 6 cores / 12 threads. RAM: 2 × 16 GB, configured at 6000 MT/s.
  OS: Windows 11 Pro build 26200. Power plan: "Balanced" (will not be changed).
- Toolchains:
  - present: git 2.55, Python 3.13.6, uv, Vulkan SDK 1.4.350 (`glslc`)
  - **missing:** C/C++ compiler, CMake, Ninja, HIP SDK
- Target model blobs in the local Ollama store (text model only; vision projectors excluded):
  - `unsloth/gemma-4-E4B-it-GGUF:Q8_0`: 7.63 GB (sha256 prefix a2232a649523)
  - `unsloth/Qwen3.5-9B-GGUF:Q4_K_M`: 5.29 GB (sha256 prefix 03b74727a860)
- Potentially useful for speculative decoding (also local):
  - `unsloth/Qwen3.5-9B-MTP-GGUF:Q4_K_M`: 5.47 GB, contains MTP weights
  - `unsloth/gemma-4-E2B-it-GGUF:Q4_0`: 2.83 GB
- No Ollama or LM Studio server was running during the survey.

**Conclusion:** Building anything needs a compiler first. PROTOCOL.md §3.1 lists the proposed
downloads and asks for approval. The default is a portable LLVM-MinGW toolchain with no system
changes.

**Status:** Waiting for approval of PROTOCOL.md, the budget, and the downloads/installs.

---

## 2026-09-30 18:07 — Entry 001 — Protocol approved; Phase 1 starts

The user approved the protocol ("I think you can go on"). PROTOCOL.md is now v1.0 (frozen).
The budget clock starts now: 8 h of active work, midpoint status at about 4 h. No system-wide
installs will be made. The toolchain is portable LLVM-MinGW plus a local `.venv`.

---

## 2026-09-30 ~18:10–18:45 — Entry 002 — Phase 1: toolchain, reference build, harness, freeze

**Toolchain (approved downloads D1–D5 only; no system changes):**
- **llama.cpp** pinned to release tag **b11284** = `25747b08e7a0f9a59a2089ce6b98d2229b76042a`
  (2026-09-30). The first clone of `master` HEAD (`05af0d2b`) was replaced, because HEAD had no
  release tag, which ruled out the official-build validation (§5.5).
- **LLVM-MinGW 20260922** (clang 23.1.2), zip sha256 `e3ad77d1…`.
- **CMake 4.4.3 and Ninja 1.13.2** in `.venv`.
- **Official llama-b11284-bin-win-vulkan-x64.zip**, sha256 `69c70371…`.

**Reference build** (`scripts/build_llama.sh`, `build/ref-vulkan/BUILDINFO.txt`):
- The source is unmodified (the diff hash equals the SHA-256 of an empty diff).
- Two build-environment fixes were needed. Neither changes the source:
  1. `-D_WIN32_WINNT=0x0A00`, because MinGW defaults to an older Windows API level and the
     vendored cpp-httplib requires Windows 10 APIs.
  2. Copying the LLVM-MinGW runtime DLLs next to the binaries.
- Build log: `results/raw/phase1/build-ref.log`.

**Models:** copied from the Ollama store into `models/`. The SHA-256 values match the
content-addressed blob names (see `models/MODELS.md`). Both files declare Apache-2.0 in their
metadata.

**Tensor inventory** (`results/raw/phase1/gguf_inventory_*.json`): weight bytes that must be
streamed per generated token (everything except lookup-only embedding tables):
- Gemma 4 E4B Q8_0: 5,182,392,488 B, including the tied 713 MB output head. The 2.99 GB of
  per-layer embeddings plus the token-embedding lookup are excluded.
- Qwen3.5-9B Q4_K_M: 5,097,424,896 B.

**Exploratory llama-bench** (not the formal reference; `results/raw/phase1/explore/`):

| Model | pp512 (tok/s) | tg128 (tok/s) |
|---|---|---|
| Qwen3.5-9B | 1437.87 ± 3.36 | 89.55 ± 0.06 |
| Gemma 4 E4B | 3031.73 ± 39.32 | 83.25 ± 0.30 |

Multiplying tg128 by the streamed bytes gives about 456 GB/s (Qwen) and about 431 GB/s (Gemma).
That is 73 % and 69 % of the spec-sheet 624 GB/s. **Implication:** even a perfect kernel at 100 %
of the spec bandwidth would be only 1.37× (Qwen) and 1.45× (Gemma) faster. Kernel work alone
cannot reach 2×. This confirms the prior in §9.1. The formal roofline follows after the
bandwidth measurement.

**Discovery about stock llama.cpp b11284:** it already implements many speculative decoding
modes:
- `draft-simple`
- `draft-eagle3`
- `draft-mtp`
- `draft-dflash`
- `draft-dspark`
- five n-gram variants
- a `gemma4-assistant` drafter architecture

The server supports speculation on hybrid/recurrent targets through context checkpoints and
replay. Consequence: the secondary reference in §5.5 ("stock llama.cpp + its own best
speculation") is essential for honest attribution.

**Qwen3.5 MTP file:** the local `unsloth/Qwen3.5-9B-MTP-GGUF:Q4_K_M` is **not** byte-identical
to the target in its main weights. 248 of 427 common tensors differ, e.g. a different quant mix
(`results/raw/phase1/tensor_diff_qwen35_vs_mtp.json`). Using it directly would change the target
weights. The option is to graft only its 15 `blk.32.*` MTP tensors onto the unchanged target
file.

**Harness** (`bench/`) consists of:
- `session.py`: interleaved blocks, 2 warm-ups, streaming per-token timestamps, canary
  llama-bench at the start and end, env/VRAM snapshots
- `prepare_tokens.py`: token IDs from the reference server's own chat template and tokenizer,
  so every engine receives identical input
- `qdump` (C++): teacher-forced full-vocabulary logits, with context params parsed exactly
  like llama-server
- `q1.py`: KLD, top-1, PPL gates
- `q2.py`: first-divergence Δ classification
- `summarize.py`: median, IQR, CV, bootstrap CI

**Validation runs** (unfrozen, flagged as validation):
- `results/raw/20260930-182331_smoke`, `…183227_validate-q2`:
  - The reference greedy run was identical to the reference Q2 run on 15/15 prompts: generation
    is deterministic and `n_probs` does not change the tokens.
  - `q1.py`: two independent reference dumps at ub=1 were bit-identical (5120/5120 rows).
  - Stock `ngram-simple` speculation showed 5 soft divergences (Δ ≤ 0.18 nats), 0 hard.
    Speedup 0.973× [0.923, 1.007] on dev chat prompts, not significant.
    `results/raw/q2/validate_ngram_vs_ref.json`.
- VRAM capture works. Qwen3.5 at c=40960 uses about 6.4 GB.

**Operational decisions** (within the protocol; no thresholds touched):
- **Pinned server args for all engines:** `-ngl 99 -c 40960 -np 1`. Everything else is default
  (flash attention `auto`).
- **Dev prompt set:** 15 prompts (3 per category × 5 categories). Each workload needs at least
  5 repetitions per configuration, e.g. blocks R(3) C(3) C(2) R(2). The full matrix runs at
  milestones and in Phase 3. Individual iterations run the workloads relevant to the change,
  plus the full Q1/Q2 gates.
- **Qwen3.5 sampling** for S-sampled: temp 1.0, top_p 0.95, top_k 20, min_p 0,
  presence_penalty 1.5 (model card, thinking mode). **Gemma 4:** temp 1.0, top_k 64,
  top_p 0.95 (GGUF `general.sampling.*`).

**Freeze:** `bench/MANIFEST.sha256` is written, with manifest sha256
`430b907b4557f813992943d5c6163c0c779d7e3e5b74926c6560302b4576994b`. The bench files are
read-only. `.gitattributes` disables line-ending conversion so checksums and raw data stay
byte-identical. Git tag: `bench-frozen`.

---

## 2026-09-30 ~18:45–19:00 — Entry 003 — Additional downloads approved; drafter research

**User approval (chat):** "yes, download D6a, D6b and D7". All three were verified against the
publisher's SHA-256 (Hugging Face LFS oid, GitHub release digest):

| # | File | Bytes |
|---|---|---|
| D6a | `models/mtp-gemma-4-E4B-it.gguf` | 98,653,248 |
| D6b | `models/Qwen3.5-0.8B-Q8_0.gguf` | 811,843,840 |
| D7 | `toolchain/llama-b11284-bin-win-rocm-10.0-x64.zip` | 255,700,814 |

D7 was extracted to `toolchain/official-b11284-rocm/`. It is self-contained (it bundles
`amdhip64_7.dll`, `amd_comgr.dll` and `rocm_kpack.dll`), so no system install was needed.
Details are in `models/MODELS.md`.

**Findings:**
- The local Gemma target is an **older revision** than the current upstream file. It stays the
  target, as the protocol defines.
- The Qwen target equals the upstream file byte for byte.
- There is no MTP sidecar in the unsloth Qwen3.5-9B-GGUF repo.
- **Qwen MTP plan:** stock llama.cpp can load an "MTP-only" sidecar via `-md` (it is detected
  when `blk.0.attn_norm` is absent). `scripts/make_mtp_sidecar.py` builds such a sidecar locally.
  It takes `token_embd`/`output_norm`/`output` from the target, byte-identical, and the `blk.32.*`
  MTP block from the local unsloth MTP file. The target file used with `-m` stays untouched.
- **Cost note (hypothesis for later):** every MTP draft step also multiplies with the full
  248k-vocabulary output head, roughly 16 % of a full target step's bytes. A reduced-vocabulary
  draft head would cut that. It is lossless, because the target verifies every token.

**Code reading: speculative decoding on hybrid targets in stock b11284.** Qwen3.5 is a hybrid:
24 of its 32 layers are Gated-DeltaNet (recurrent state), and every 4th layer is full attention.
Rejected draft tokens must therefore be rolled back in the recurrent state. Stock llama.cpp has
two mechanisms:
1. **`n_rs_seq` snapshots**, experimental: one recurrent-state snapshot per draft position on
   the GPU, which gives cheap partial rollback.
2. **Full checkpoint + replay**: the sequence state is copied to host memory with
   `llama_state_seq_get_data_ext`. On partial acceptance the state is restored and the accepted
   tokens are re-decoded.

`common_params_speculative::need_n_rs_seq()` enables (1) **only** for draft-mtp, draft-eagle3,
draft-dflash and draft-dspark (n_rs_seq = draft n_max). **draft-simple** (a separate draft
model) and all **n-gram** types fall back to (2) on Qwen3.5. `QWEN35` is listed in
`llm_arch_supports_rs_rollback`, and no CLI flag exists to force (1).
→ **Hypothesis H-rs:** enabling snapshots for draft-simple (bounded n_max) removes the
checkpoint/replay overhead for Qwen3.5 draft-model speculation. This may also explain the
0.973× of the n-gram validation run.

**Phase 2 plan (ordered by expected value):**
1. **Secondary reference (stock features only):** Qwen = draft-mtp with a locally built sidecar,
   and draft-simple with Qwen3.5-0.8B. Gemma = the official MTP drafter. Tune n_max on dev.
   Run the quality gates Q1 (verify path) and Q2.
2. **Own improvements on top of the best stock configuration:**
   - H-rs (above)
   - a reduced-vocabulary draft head for MTP drafting
   - the verification-batch cost c(k) = t(k tokens)/t(1 token) in the Vulkan backend
   - host overhead per step
3. **Kernel-level decode work**, only if profiling shows clear headroom. The ceiling is about
   1.4× (Entry 002).

---

## 2026-09-30 ~19:00–19:30 — Entry 004 — Formal reference measured; Q1 noise floor exceeds the thresholds (STOP per §4.6)

**Reference session** `results/raw/20260930-183829_ref-baseline` (frozen tooling, dev split,
5 reps per workload). Canary 89.15 → 89.42 t/s (drift +0.30 %, valid). Summary:
`…/summary.json`.

| Model | S-greedy tg (median, IQR, CV) | S-sampled tg | L tg | TTFT short (median) |
|---|---|---|---|---|
| Qwen3.5-9B | 86.67 [86.56–86.84], CV 0.45 % | 82.79 | 78.85 | 144.4 ms |
| Gemma 4 E4B | 79.95 [79.95–80.03], CV 0.24 % | 79.44 | 67.30 | 88.4 ms |

Per-prompt L results for Gemma: pp is 1798 t/s at 4k, 807 t/s at 16k and 459 t/s at 32k, so
TTFT at 32k is 71.5 s. Qwen: 1394, 1303 and 1174 t/s.
Exploratory llama-bench at depth 16k for Gemma (`results/raw/phase1/explore/gemma_fa_depth16k.jsonl`):

| Flash attention | pp2048 (t/s) | tg32 (t/s) |
|---|---|---|
| off | 2017.8 | 64.5 |
| on (the default via `auto`) | 433.6 | 68.7 |

→ **H-fa-gemma:** the Vulkan flash-attention path for Gemma's head size 512 is about 4.65× slower
for prefill at depth. This is a TTFT opportunity.

**Q1 noise floor** (`results/raw/q1/noisefloor_*`, reference ub=1 decode path vs llama.cpp's own
legitimate variants) and **lossy calibrators** (`results/raw/q1/calib_*`):

| Comparison (vs R ub=1) | Qwen mean KLD | Qwen p99 | Qwen top1 | Qwen \|lnPPL\| | Gemma mean KLD | Gemma p99 | Gemma top1 | Gemma \|lnPPL\| |
|---|---|---|---|---|---|---|---|---|
| R ub=512 (prompt path) | 2.24e-3 | 4.14e-2 | 98.55 % | 8.86e-4 | 1.84e-3 | 2.28e-2 | 98.14 % | 4.55e-3 |
| R ub=4 (verify path) | 1.82e-3 | 3.72e-2 | 98.54 % | 5.53e-4 | 1.59e-3 | 1.91e-2 | 98.18 % | 1.81e-3 |
| R ub=1, FA off | 2.04e-3 | 3.66e-2 | 98.44 % | 3.62e-4 | 5.61e-4 | 3.78e-3 | 99.59 % | 8.49e-5 |
| calib: KV cache q8_0 | 1.93e-3 | 3.54e-2 | 98.71 % | 6.86e-4 | 4.00e-4 | 5.88e-3 | 99.06 % | 1.29e-3 |
| calib: KV cache q4_0 | 9.87e-3 | 1.81e-1 | 96.66 % | 6.57e-3 | 4.52e-2 | 5.39e-1 | 92.07 % | 2.53e-2 |
| calib: other Q4_K_M quant (MTP file main weights) | 1.75e-2 | 3.16e-1 | 95.86 % | 3.20e-3 | — | — | — | — |
| **Protocol thresholds** | ≤ 5e-4 | ≤ 5e-3 | ≥ 99.5 % | ≤ 1e-3 | ≤ 5e-4 | ≤ 5e-3 | ≥ 99.5 % | ≤ 1e-3 |

The reference is exactly reproducible: two ub=1 dumps per model are bit-identical (sha256 of the
Qwen dump `55017757…` in both runs).

**Analysis:**
- **The prior in §4.1 was wrong.** I assumed kernel-numerics noise would be 1–2 orders of
  magnitude below 1e-3. Measured llama.cpp noise between its own configuration choices is
  about 1.6–2.2e-3 mean KLD. That is 3–4.5× my mean-KLD threshold and 4–8× the p99 threshold,
  and top-1 agreement is 98.1–98.6 %.
- **Mechanism, part 1 (from the code):** on AMD, `ggml_vk_should_use_mmvq`
  (`ggml-vulkan.cpp:6543`) quantizes activations to int8 (q8_1) for every batched matmul
  (n > 1), except for Q6_K weights. For n = 1 it keeps float activations for Q8_0 weights, which
  covers Gemma. For K-quants with k ≥ 2048 it uses int8, which covers most of Qwen. The MMQ
  prompt path also quantizes activations.
- **Mechanism, part 2:** for Qwen the long segment dominates (mean KLD 7–9e-3 after a
  15k-token prefix). Small differences accumulate through the recurrent DeltaNet state and long
  attention.
- **KV q8_0 falls inside llama.cpp's own noise envelope** for both models. At this numerical
  precision, 8-bit KV is indistinguishable from llama.cpp's own path choices by the Q1 metrics.
  Clearly lossy changes, such as a different weight quantization or KV q4_0, lie 5–25× outside
  the envelope.
- **Consequence:** under the original thresholds, **stock llama.cpp fails its own quality gate**.
  Its standard batched verification path (ub=4) and its prompt path both fail. Every speculative
  method that verifies in batches would fail by construction. So would any kernel that is not
  bit-exact with the decode path.

**Action (per §4.6):** stop before Phase 2 and ask the user. No thresholds were changed. No
optimization results exist yet; the only speculative run so far was the pre-freeze n-gram
validation of the Q2 tool.

---

## 2026-09-30 ~20:05 — Entry 005 — Amendment 1 (user chose option A)

**User decision (chat):** "Go with option A". This became PROTOCOL §12, Amendment 1:
- **A1.1:** Q1 becomes a noise-envelope gate. A candidate must be no further from R(ub=1) than
  the worst of llama.cpp's stock variants on every metric. The variants are ub=512, ub=4 and
  FA-off.
- **A1.2:** design rule. Only numeric techniques that stock llama.cpp already applies by default
  are allowed. No weight or KV quantization changes, no approximations, no skipping.
- **A1.3:** Q2 and all other criteria are unchanged.
- **A1.4:** tooling amendment. `bench/q1_gate.py` was added. The manifest diff is exactly one
  added line, and all measurement-code hashes are unchanged. Tag `bench-frozen-a1`, manifest
  sha256 `65baadf4…`.
- **A1.5:** the reference is Vulkan only. The official ROCm build's `ggml-hip.dll` imports
  `hipblas.dll`, which the zip does not ship; a system HIP SDK is required (S2, not approved).
  Ollama's bundled ROCm 7.1 uses a different file naming (`libhipblas.dll`) and a different
  version, so it would not be "stock".

**Envelope, dev corpus** (`results/raw/q1/envelope-check_*_dev.gate.json`):

| Model | mean KLD ≤ | p99 KLD ≤ | top-1 ≥ | \|lnPPL\| ≤ |
|---|---|---|---|---|
| Qwen3.5-9B | 2.240e-3 | 4.141e-2 | 98.44 % | 8.86e-4 |
| Gemma 4 E4B | 1.839e-3 | 2.284e-2 | 98.14 % | 4.55e-3 |

**Sanity check of the gate against the calibrators:**
- KV q4_0 fails all four metrics on both models, and so does Qwen's alternative Q4_K_M quant.
- KV q8_0 **passes** on both models, which confirms that A1.2 is needed. A1.2 excludes it.

---

## 2026-09-30 ~20:05–20:40 — Entry 006 — Phase 1 closed; first Phase 2 exploration (stock speculation, verify-cost pathology)

**Build validation** (`results/raw/20260930-195818_buildval`, interleaved R C C R, canary drift
−0.80 %, valid). The official prebuilt b11284 Vulkan build compared with my build:

| Model | tg ratio (official / mine) | 95 % CI | Greedy tokens identical |
|---|---|---|---|
| Qwen3.5-9B | 0.987× | [0.985, 0.988] | 15/15 |
| Gemma 4 E4B | 0.994× | [0.992, 0.995] | 15/15 |

My build is within ±3 %, so it is **validated** and not handicapped.

**Reference determinism:** Qwen's greedy output repeats exactly across fresh-server first passes.
Within one server process, however, passes 2–5 diverge from pass 1 on 5/15 prompts, at the same
position every time. These are near-ties: Δ = 0.012–0.086 nats from R's log-probs
(`refdeterminism_qwen35-9b`). The effect is benign and history-dependent, probably from KV cell
placement. Gemma is fully deterministic. Q2 compares first passes on a fresh server, so it is
unaffected.

**Bandwidth test:** invalid as a DRAM ceiling. The `test-backend-ops` MUL_MAT perf cases use one
33–62 MB weight matrix, which stays resident in the 64 MB Infinity Cache. For example, q8_0
4096×14336 comes out at about 1027 GB/s, above the DRAM spec. The roofline therefore uses the
624 GB/s spec value, the most generous ceiling. Raw data: `results/raw/*_bandwidth/`.

**Micro workload (llama-bench, §5.3):** the first attempt failed because of an MSYS path bug in
`scripts/run_llama_bench.sh`, which is now fixed. It will be run later; it is not needed for any
decision so far.

**Qwen MTP sidecar** (`models/Qwen3.5-9B-MTP-sidecar.gguf`, sha256 `e14ead8d…`,
`results/raw/phase1/mtp_sidecar_build.txt`):
- `token_embd`, `output_norm` and `output` come from the target, byte-identical.
- The `blk.32` MTP block comes from the unsloth file.
- One draft step reads about 167 MB (MTP block) plus 834 MB (Q6_K 248k-vocab head), roughly
  20 % of a target step.

**Stock speculation sweep** (exploratory, 1 pass each, not interleaved; baseline from the
ref-baseline session). Sources: `…202032_smoke-stock-mtp`, `…202224_sweep-stock-mtp`,
`summary_vs_ref.json`. Cells show S-greedy tg speedup [95 % CI], then acceptance. "TTFT ×" is
TTFT relative to the baseline; above 1 is worse.

| Stock config | Qwen speedup | Qwen accept | Qwen TTFT × | Gemma speedup | Gemma accept | Gemma TTFT × |
|---|---|---|---|---|---|---|
| draft-mtp n=1 | 1.419 [1.402, 1.436] | 0.897 | 1.23 | 1.529 [1.497, 1.563] | — | 0.94 |
| n=2 | 1.670 [1.618, 1.724] | 0.822 | 1.14 | 1.881 [1.804, 1.965] | — | 0.93 |
| n=3 | 1.639 [1.561, 1.719] | 0.724 | 1.34 | **2.039 [1.911, 2.172]** | 0.573 | 1.09 |
| n=4 | 1.081 [1.009, 1.160] | 0.652 | 1.19 | 1.981 [1.823, 2.162] | — | 0.98 |
| n=6 | **0.403** [0.369, 0.444] | 0.515 | 1.13 | 1.609 [1.377, 1.853] | — | 1.01 |
| n=3 with `-bs` | 1.667 | — | **1.57** | 2.127 | — | **1.36** |

**Findings:**
1. **Stock llama.cpp with the official Gemma drafter already reaches about 2× on greedy dev
   prompts.** The secondary reference is strong.
2. **Qwen collapses for n ≥ 4, although acceptance stays high.** With 3840 tokens per pass, the
   derived time per verify step is:

   | n | 2 | 3 | 4 | 6 |
   |---|---|---|---|---|
   | ms per step | ~18 | ~22 | ~38 | ~114 |

3. **Root cause: the verification cost c(k) of the Vulkan backend.** Exploratory llama-bench
   pp=k at d=512, 10 reps (`results/raw/phase1/explore/ubatch_cost_r10_qwen.jsonl`). Median ms
   per k-token ubatch:

   | k | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
   |---|---|---|---|---|---|---|---|---|
   | ms | 11.4 | 16.0 | 14.6 | 18.4 | 28.7 | 62.3 | 96.7 | 23.6 |

   At k ≥ 9 the cost is about 88 ms (the MMQ matmul path). Per-op profile
   (`perflog_qwen_k{1,4,6,8}.txt`): `MUL_MAT_VEC q4_K m=12288 k=4096` takes 58 µs at n=1,
   115 µs at n=4, **622 µs at n=6** and 120 µs at n=8. So the MMVQ kernel is pathological for
   5–7 columns, and even at n=4 it no longer runs at bandwidth. Gemma shows the same effect
   milder: c(4) = 1.43, and k ≥ 9 costs about 3.3×.
4. **The perf logger distorts absolute times** (it adds a sync per op). An apparent q5_K
   anomaly at n=1 did not survive an A/B test with `GGML_VK_DISABLE_MMVQ=1`: tg128 was 89.2
   with and without it.
5. **MTP raises TTFT.** Qwen: +14–34 %. Gemma: about ±10 % (noisy on short prompts). This
   conflicts with the ≤5 % requirement for full success.

**Revised Phase 2 priorities:**
- **P1:** multi-column mat-vec (verify-path) efficiency in the Vulkan backend, including the
  5–7-column pathology.
- **P2:** a reduced-vocabulary MTP draft head for Qwen.
- **P3:** the TTFT overhead of MTP.
- **P4:** Gemma long-context prefill with FA.

---

## 2026-09-30 ~20:40–21:15 — Iterations 1 and 2 (Vulkan MMVQ verify path)

### Iteration 1 — MMVQ decode-once (llama.cpp-dev `5ac7610`, `patches/llama.cpp/0001-*.patch`)

- **Hypothesis:** batched mat-vec (n = 2..8, the speculative verification path) is ALU-bound on
  RDNA3. `mul_mat_vecq.comp` re-runs the A-block unpacking (`repack4` + scale decode) for every
  B column.
- **Change:** for Q4_K, Q5_K and Q6_K, each A block is decoded once per row and dotted against all
  cached B columns. The integer dots and float expressions are unchanged and run in the same
  order.
- **Quality:** qdump dev ub=4 and ub=1 are **bit-identical** to stock. Dump sha256
  `42a691aa…` (ub=4) and `55017757…` (ub=1) match the frozen reference dumps
  (`results/raw/q1/it01_bitcheck_*`). Q1 is therefore trivially inside the envelope, and Q2 is
  unaffected by construction.
- **Measurement:** exploratory k-sweep, Qwen, llama-bench pp=k at d=512, 10 reps
  (`results/raw/phase1/explore/ubatch_cost_r10_qwen_dev-decodeonce.jsonl`). Median ms per
  k-token ubatch:

  | k | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
  |---|---|---|---|---|---|---|---|---|
  | stock | 11.4 | 16.0 | 14.6 | 18.4 | 28.7 | 62.3 | 96.7 | 23.6 |
  | iteration 1 | 11.4 | 15.8 | 11.8 | 13.1 | 20.7 | 22.4 | 24.2 | 28.4 |

- **Caveat:** repeat runs of the same binary show that these llama-bench micro tests are noisy.
  Each test is a ~15 ms burst, so the clocks never settle. Within-run ranges are ±30 %
  (`…_rows1_rerun{a,b}.jsonl`). Only the large effects are trustworthy. From here on, decisions
  use end-to-end server sessions.
- **End-to-end** (exploratory session `…204937_it01-e2e-explore`, 1 pass each, canary drift
  −0.23 %). S-greedy speedup vs R [95 % CI]:

  | Config | Qwen | Gemma |
  |---|---|---|
  | stock n=3 | 1.614 [1.545, 1.682] | 2.020 [1.899, 2.150] |
  | it01 n=3 | 1.600 | 2.030 (Q8_0 is unchanged by this iteration) |
  | it01 n=4 | 1.317 | — |
  | it01 n=6 | 1.156 | — |

- **Conclusion:** the pathological collapse at n ≥ 4 is mostly removed. Stock gave 1.08 at n=4
  and 0.40 at n=6. For Qwen, however, n=3 does not improve end to end, so the remaining per-step
  cost is elsewhere (see iteration 3).

### Iteration 2 — drop the RDNA3 4-row MMVQ override for more than 4 columns (llama.cpp-dev `48424f6`, `patches/llama.cpp/0002-*.patch`)

- **Hypothesis:** the static 4 rows per workgroup for more than 4 columns was tuned for the old
  per-column decode. With decode-once, the default row count is better.
- **Measurement:** same exploratory session, build `exp-rows1`. S-greedy speedup vs R:

  | Config | Qwen | Gemma |
  |---|---|---|
  | n=4 | **1.550** (it01: 1.317) | **2.204 [2.039, 2.394]** |
  | n=6 | 1.330 (it01: 1.156) | — |
  | n=3 | — | 2.032 |

- **Quality:** qdump ub=4 and ub=5 are **bit-identical** to stock for both models
  (`results/raw/q1/it02_bitcheck_*`; Gemma ub=5 dump sha `5ca63300…` equals the reference).
- **Conclusion:** kept. Gemma now beats the best stock configuration (2.02×) at n=4. The
  exploratory results still need confirmation with a formal interleaved measurement.

### Diagnosis for Qwen (motivates iteration 3)

Stock MTP at n=3 takes about 22.5 ms per speculative step (3840 tokens, about 1228 steps per
pass). The micro verify cost for k=4 is about 13 ms after iteration 1. Each of the 3 MTP draft
steps multiplies with the full 248,320-row Q6_K output head (834 MB) plus the MTP block
(167 MB), which is about 1 GB of reads per draft token. The draft head is the dominant remaining
cost.

The k=2 anomaly (pp2 slower than pp3) is not GPU time: the GPU perf log shows k=2 at 41 ms total
and k=3 at 44 ms. It is host-side and was deprioritized, because it affects only n=1.

---

## 2026-09-30 ~21:15–21:55 — Iterations 3 and 4; FA-off dead end; midpoint

### Iteration 3 — reduced draft vocabulary for the Qwen MTP head (llama.cpp-dev `2bdfca4`, `patches/llama.cpp/0003-*.patch`)

- **Hypothesis:** each Qwen MTP draft step reads about 1 GB, and the full 248k-row Q6_K head
  (834 MB) dominates that. A frequency-ranked draft vocabulary (FR-Spec style) cuts draft cost
  without affecting outputs, because the target verifies every token.
- **Change:**
  - `src/models/qwen35.cpp`: MTP-only sidecars may carry `output` with K rows plus a `d2t` I64
    mapping (the existing EAGLE3 convention). `graph_mtp` scatters the K logits into a −inf
    full-vocabulary row (`ggml_fill` + `ggml_set_rows`, the same code pattern as `eagle3.cpp`).
  - `scripts/make_mtp_sidecar_rv.py` builds sidecars. Head rows are byte-identical copies of
    target rows.
  - Token ranking: `scripts/tokfreq` counts over WikiText-2 *train* (not used anywhere else) and
    600 site-packages `.py` files (5.54 M tokens), plus 5 × the counts of the model's own
    dev-split generations (42,240 tokens). All 27 control/EOG tokens are always kept.
  - Corpus hashes: `build/it03-corpus/SHA256SUMS.txt`, tokfreq csv `9f302fd8…`.
- **Cross-validated coverage** (rank on half of the dev prompts, measure on the other half),
  as a percentage of generated tokens:

  | K | W=0 | W=5 |
  |---|---|---|
  | 16k | 84.6 % | 89.3 % |
  | 32k | 92.2 % | 94.4 % |
  | 49k | 96.0 % | 97.1 % |
  | 64k | 97.8 % | **98.45 %** |

  Sidecars: rv64k sha `4583cf13…` (head 220 MB), rv32k `41e9d998…` (head 110 MB).
- **Traceability:** `git diff 48424f6 2bdfca4 | sha256sum` = `96e8b352…`, which equals the
  `dirty-diff-sha256` in `build/it03/BUILDINFO.txt`.
- **Measurement** (exploratory `…211738_it03-explore`, 1 pass each, canary −0.32 %). Qwen
  S-greedy vs R [95 % CI]:

  | Sidecar | n=3 | n=4 | n=5 |
  |---|---|---|---|
  | full head | 1.601 [1.459, 1.732] | — | — |
  | rv64k | **1.932 [1.830, 2.036]** | 1.927 | 1.779 |
  | rv32k | 1.986 [1.879, 2.098] | 1.956 | — |

  TTFT ratio 1.41 with the full head, 1.11 with rv64k and 1.12 with rv32k. Part of MTP's TTFT
  overhead was the head.
- **Quality:** Q2 on the explore runs has 0 hard divergences for every configuration
  (`results/raw/q2/explore_q2_*`). The identical-token share is 55–70 %, in the same range as
  stock speculation (Gemma stock n=3: 59.0 %). The target graph is unchanged by construction.
- **Decision:** keep **rv64k**. rv32k was slightly faster on dev, but its coverage advantage is
  partly in-sample, and rv64k has better out-of-sample coverage.

### Dead end — FA off for Gemma prefill (stock option; exploratory `…212446_it03-gemma-fa`)

Measured with MTP n=4:

| Metric | FA on | FA off |
|---|---|---|
| L TTFT at 16k | 20.9 s | 9.9 s |
| L TTFT at 32k | 73.5 s | 19.2 s |
| S-greedy TTFT | 108 ms | **1463 ms** |
| S-greedy speedup | — | 1.99× |
| tg at 32k | 73.4 | 50.0 |

→ Not viable as a blanket switch. The real fix is the FA prefill kernel for head size 512 on
32 KB-shmem RDNA3.

### Gate finding — Gemma n=4 is not admissible with stock numerics

Q1 gate (`results/raw/q1/gate_dev_*_verify-ub4-ub5.gate.json`): stock R at ub=5 vs R ub=1 for
Gemma gives mean KLD 2.060e-3 against a limit of 1.839e-3 (FAIL) and |lnPPL| 4.82e-3 against a
limit of 4.55e-3 (FAIL). So stock-numerics MTP n=4 for Gemma fails A1.1, even though it is
stock llama.cpp's own ub=5 path. Qwen ub=5 passes.

### Iteration 4 — small batches use the decode-path activation-precision rule (llama.cpp-dev `991c2e6`, `patches/llama.cpp/0004-*.patch`)

- **Hypothesis:** `ggml_vk_should_use_mmvq` returns true for every n > 1. So batched mat-vec
  quantizes activations to q8_1, while decode keeps them in float for Q8_0 on RDNA. This is
  where Gemma's verify-vs-decode divergence comes from.
- **Probe:** `GGML_VK_DISABLE_MMVQ=1` at ub=5 gave mean KLD 2.64e-5.
- **Change:** removed the `n > 1 → MMVQ` early return, so the per-type and per-k rule of n=1
  applies to all n ≤ 8. The build's diff sha `cf2ebb23…` equals the commit diff.
- **Quality** (`results/raw/q1/it04_*`, `gate_dev_*_it04-verify.gate.json`, all vs R ub=1):

  | Path | mean KLD | top-1 | \|lnPPL\| |
  |---|---|---|---|
  | Gemma ub4 | 1.80e-6 | 99.98 % | 3.9e-5 |
  | Gemma ub5 | 2.64e-5 | 99.84 % | 7.8e-5 |
  | Qwen ub4 | 2.18e-3 | 98.61 % | — |
  | Qwen ub5 | 1.56e-3 | 98.73 % | — |

  - The Gemma paths even meet the original §4.3 thresholds.
  - Qwen is essentially unchanged: its remaining verify-vs-decode difference comes from
    attention and DeltaNet, not from Q8_0 matmuls.
  - All four pass the A1.1 gate.
- **Measurement:** end-to-end exploratory session `…it04-explore`, results in the next entry.

### Midpoint status (about 3 h 50 min of 8 h), given to the user in chat

Exploratory best so far, S-greedy vs stock without speculation:

| Model | Best config | Speedup | Stock with its own MTP |
|---|---|---|---|
| Qwen | rv64k head, n=3 | about 1.93–1.99× | 1.61–1.67× |
| Gemma | n=4 | about 2.14–2.20× | 2.02–2.04× |

Open items:
- MTP's TTFT overhead (+6–15 %)
- slow stock prefill for short prompts (9–64 tokens: MMQ tile path + FA) and for Gemma's
  long-context FA
- S-sampled, L, and the formal interleaved measurement
- holdout

---

## 2026-09-30 ~21:55–22:20 — Iterations 5 and 6 (dead ends); Phase 2 closed

### Iteration 4 result + iteration 5: the float verify path is too slow

- **Iteration 4, end-to-end** (exploratory `…it04-explore`, canary −0.50 %). Gemma vs R, same
  session:

  | Config | Speedup |
  |---|---|
  | it03 n4 | 2.183 |
  | it04 n3 | 1.801 |
  | it04 n4 | 1.635 |
  | it04 n5 | 1.448 |

  Qwen: it04 n3 1.865, n4 1.901, against it03-rv64k n3 at 1.877. Float Q8_0 activations in the
  verify path cost Gemma 14–25 %.
- **Iteration 5 hypothesis:** the float dequant mat-vec (`mul_mat_vec.comp`, K_PER_ITER 8 path)
  also re-dequantizes A per column. It was restructured to decode once
  (`patches/llama.cpp/exp-it05-dmmv-decode-once.diff`).
- **Iteration 5 quality:** bit-identical to it04 (Gemma ub5 sha `bc5d1922…`); ub1 is
  bit-identical to R (`e92505ec…`).
- **Iteration 5 speed** (`…220424_it05-explore`, same session): it03-full-n4 1.876 vs it05-n4
  1.621. No recovery.
- **Session-to-session variance:** it03-full-n4 measured 2.183 in `it04-explore` and 1.876 in
  `it05-explore`. Single-pass exploratory numbers are only comparable **within** a session.
- **Decision:** iteration 4 was reverted (dev `fcaa251`, `patches/llama.cpp/0005-*`), and
  iteration 5 was not committed. Gemma n=3 with stock numerics (verify ub=4 = envelope variant
  V2) is admissible and faster. The fidelity result is still worth reporting: float activations
  in batched verification make Gemma's speculative verification near-identical to decode
  (mean KLD 2.6e-5 against 2.1e-3).

### Iteration 6 — MMVQ decode-once for Q8_0 in the int8 path (dead end)

- **Change:** the decode-once split for Q8_0 in `mul_mat_vecq` (K_PER_ITER 8), saved as
  `patches/llama.cpp/exp-it06-mmvq-q8_0-decode-once.diff`, not committed.
- **Quality:** bit-identical to stock (Gemma ub4 `335b8601…`, ub5 `5ca63300…`).
- **Speed** (`…221458_it06-explore`, ABBA with 2 passes each, canary −0.14 %): it06 vs it03 at
  Gemma n3 = **1.003× [0.997, 1.009]**, not significant. Q8_0 A-decode is already cheap.
- **Observation:** in the same ABBA session, TTFT medians for numerically identical builds
  differed by about 20 % (87.1 vs 106.9 ms). Short-prompt TTFT is noisy.

### Phase 2 closed — final configuration

- **Code:** llama.cpp b11284 plus `patches/llama.cpp/0001` (MMVQ decode-once for K-quants),
  `0002` (RDNA3 rows) and `0003` (qwen35 reduced-vocabulary MTP head). `0004` and `0005` cancel
  out (iteration 4 and its revert). The dev HEAD tree equals `2bdfca4`.
- **Qwen3.5-9B:** `-md Qwen3.5-9B-MTP-sidecar-rv64k.gguf --spec-type draft-mtp --spec-draft-n-max 3`.
  - rv64k was chosen over rv32k for out-of-sample coverage.
  - n=3 was chosen because n=4 was tied, and the n=3 verify path equals envelope variant V2.
- **Gemma 4 E4B:** `-md mtp-gemma-4-E4B-it.gguf --spec-type draft-mtp --spec-draft-n-max 3`.
  n=4 is not admissible with stock verify numerics (ub5 is outside the envelope).
  → For Gemma the final configuration is **functionally identical to stock MTP n=3**. None of my
  kernel changes (K-quant decode-once, rows for 5+ columns) touch its Q8_0 path at 4 columns.
- **Secondary reference (stock-best on dev):** Qwen stock draft-mtp n=2 with the full-head
  sidecar (1.670 on dev, vs 1.639 at n=3); Gemma stock n=3 (2.039).

---

## 2026-09-30 ~22:20 — Entry — Phase 3 started

**Clean rebuild of the final version:**
1. Fresh clone of b11284 (`src/llama.cpp-final`).
2. `git am patches/llama.cpp/0001..0003` gives commits `06990a9`, `2a649b4` and `865c8bf`.
3. The resulting tree hash `4f2d9bdb…` is **identical** to the dev HEAD tree, so the patches
   reproduce the tested code exactly.
4. Built into the fresh directory `build/final-vulkan`. The diff hash is that of an empty diff
   (clean tree). Log: `results/raw/phase3/build-final.log`.

**Engine configs:**
- `configs/engines/final.json`: final build, draft-mtp n=3, Qwen rv64k sidecar, Gemma official
  drafter.
- `final-nospec.json`: for qdump checks.
- `stock-best.json`: the secondary reference. Stock build; Qwen n=2 with the full-head sidecar,
  Gemma n=3.

**Holdout:** first access at 22:22:56 via `prepare_tokens.py --phase3-holdout`. Before that,
`results/holdout_access.log` did not exist, which confirms there was no earlier access.
Holdout prompt lengths:
- Qwen: 21–440 tokens
- Long prompts: 4097, 16385 and 32769 tokens

**Formal holdout speed sessions** (running): one per model. Each has a canary; each workload
(S-greedy, S-sampled, L) is interleaved as R(3) C(3) S(3) S(2) C(2) R(2), giving 5 reps per
engine. An R Q2 pass follows.

**Qwen holdout session** `results/raw/20260930-222320_phase3-holdout-qwen35-9b`: canary
88.91 → 89.47 t/s (+0.63 %, valid). Summaries are in `summary_vs_ref.json` and
`summary_vs_stock.json` in that directory. Speedups (C = final, S = stock-best):

| Workload | C vs R [95 % CI] | S vs R | C vs S [95 % CI] | TTFT ratio C/R (median) |
|---|---|---|---|---|
| S-greedy | 1.858 [1.782, 1.939] | 1.630 | 1.140 [1.120, 1.161] | 1.017 |
| S-sampled | 1.685 [1.591, 1.786] | 1.495 | 1.127 | 0.988 |
| L | 1.801 [1.758, 1.839] | 1.596 | 1.129 | **1.064** |

**Q2 holdout** (`results/raw/q2/holdout_final_qwen35-9b.json`): 18 items, **0 hard**, 11 soft
(Δ ≤ 0.153 nats), identical-token share 73.0 %. Stock-best for context: 73.9 %, 0 hard.

---

## 2026-09-30 ~23:05 — Budget extension (user)

**User (chat):** "i wanted to tell you, that you can go over the limit, but ONLY if you believe
that it could make the results better. Go on"

**Handling:**
1. The Phase 3 holdout evaluation now running is **final evaluation #1** and will be reported
   unchanged.
2. Any further optimization ("Phase 2b") is decided on the **dev split only**.
3. A possible second holdout evaluation is reported separately and labeled as such, alongside
   evaluation #1. The holdout has been looked at once (aggregate results only, no content), so
   evaluation #2 is less clean, and the report will say so.
4. Extra time is spent only on hypotheses with a credible expected gain.

**Gemma holdout session** `results/raw/20260930-230128_phase3-holdout-gemma4-e4b`: canary
89.49 → 89.51 t/s (+0.02 %, valid).

| Workload | C vs R [95 % CI] | S vs R | C vs S | TTFT ratio C/R (median) |
|---|---|---|---|---|
| S-greedy | 2.066 [1.932, 2.217] | 2.078 | 0.994 | 1.089 |
| S-sampled | 1.956 [1.827, 2.102] | 1.955 | 1.001 | 1.080 |
| L | 1.802 [1.731, 1.848] | 1.795 | 1.004 | 1.004 |

For Gemma, C and S are the same code path, as expected. Their TTFT difference (C/R 1.089 vs
S/R 1.006) is therefore noise plus the fixed MTP prompt-pass overhead. **Q2 holdout**
(`results/raw/q2/holdout_final_gemma4-e4b.json`): 18 items, **0 hard**, identical-token share
58.8 % (stock-best: 58.8 %).

**Holdout Q1 dumps** (`results/phase3-q1-dumps.console.log`, records in
`results/raw/q1/*holdout*.dump.json`): the final build's target paths are **bit-identical** to the
reference for both models at ub=1, ub=4 and ub=512.

| Model | ub=1 sha | ub=4 sha | ub=512 sha |
|---|---|---|---|
| Qwen | `d1872e6c…` | `e3917e19…` | `87a328b5…` |
| Gemma | `5144bf1f…` | `25d9339f…` | `0ad7ab74…` |

**TTFT investigation:** MTP's TTFT overhead is not caused by logits for every prompt position.
`task->need_embd()` is false for completions, so only the last prompt token is an output; the
server comment claiming otherwise is stale. The overhead is the drafter's own prompt pass (the
Qwen MTP layer over the whole prompt) plus a fixed amount (Gemma about 8 ms, which stock MTP
shows too). No fix was attempted in this budget.

**Phase 2b (dev only):**
- Draft-side variants for Qwen. The draft is exempt from A1.2 because the target verifies
  everything.
  - rv64k sidecar requantized to Q4_K with `llama-quantize --pure` (sha `178e5018…`; head 210 →
    144 MiB)
  - rv32k in Q6_K and in Q4_K (sha `cd7dc8a9…`)
- Stock `--spec-draft-p-min` dynamic draft length: n_max 4–8 with p_min 0.5–0.85; also n3 with
  p0.3.
- Screening session `…p2b-screen`.

### Phase 2b screening (dev, `results/raw/20261001-001024_p2b-screen`, canary +1.15 %, valid)

Single pass per candidate, relative to the within-session `final` control. Qwen final: 2 passes,
166.52 t/s, CV 0.26 %.

**Qwen draft-side variants:**

| Draft sidecar | vs final [95 % CI] | Acceptance |
|---|---|---|
| rv64k Q4_K | 1.024 [1.007, 1.041] | 0.708 |
| rv32k Q6_K | 1.034 [1.023, 1.044] | 0.714 |
| **rv32k Q4_K** | **1.059 [1.049, 1.070]** | 0.720 |
| final (rv64k Q6_K) | 1.000 | 0.717 |

**Qwen dynamic draft length** (`--spec-draft-p-min`):

| Setting | vs final [95 % CI] | Acceptance |
|---|---|---|
| n3 p0.3 | 1.010 [1.000, 1.021] | 0.771 |
| n4 p0.5 | 1.000 | 0.830 |
| n5 p0.6 | 0.969 | 0.867 |
| n6 p0.75 | 0.910 | 0.927 |
| n8 p0.85 | **0.730** | 0.962 |

Higher acceptance does not pay. The confidence-gated drafts are shorter on average, so fewer
tokens are produced per step. For n8, every full-length draft also creates a 9-token verify
batch, which falls onto the slow MMQ tile path used for batches above 8 tokens (see entry 006).
That explains the steep drop at n8.

**Gemma** (n capped at 3): p0.3 gave 1.078× and p0.5 gave 1.027× against a **noisy** control
(its two passes: 141.89 and 162.03 t/s, CV 9.4 %).
→ Confirmation session with ABBA and 2+2 passes (`…p2b-confirm`):
- v2a: Qwen rv32k-Q4_K; Gemma p0.3
- v2b: Qwen rv32k-Q4_K + p0.3; Gemma p0.5

**Caveat:** the rv32k vocabulary ranking includes dev generations (W=5). Its cross-validated
coverage is 94.4 %, against 98.45 % for rv64k. Holdout evaluation #2 decides whether it
generalizes.

### Phase 2b confirmation (dev, `results/raw/*_p2b-confirm`, ABBA with 4 passes per engine, canary −0.07 %)

| Model | Config | Speedup vs within-session final [95 % CI] | Significant |
|---|---|---|---|
| Qwen | **v2a (rv32k-Q4_K draft, n3)** | **1.062 [1.050, 1.077]** | yes |
| Qwen | v2b (v2a + p_min 0.3) | 1.050 [1.038, 1.062] | yes |
| Gemma | p_min 0.3 | 0.994 [0.980, 1.013] | no |
| Gemma | p_min 0.5 | 0.949 | — (slower) |

The screening's +7.8 % for Gemma was an artifact of the noisy control.

**Decision (dev only):** `configs/engines/final-v2.json`.
- **Qwen:** rv32k-Q4_K draft sidecar with n=3.
- **Gemma:** unchanged.
- **Build:** unchanged. The target computation is identical to final, so the holdout Q1 results
  carry over unchanged. Q2 must be re-checked, because draft acceptance changes step boundaries.
- **Holdout evaluation #2:** Qwen only, same design as #1.

---

## 2026-10-01 ~00:35–01:45 — Holdout Q1 gates, evaluation #2 (Qwen v2), host-overhead diagnosis

**Holdout Q1** (`results/raw/q1/gate_holdout_*_final.gate.json`): **PASS** for both models.
The final build's ub=1, ub=4 and ub=512 paths are bit-identical to R's, so they equal envelope
variants V1 and V2, or R itself.

| Model | E mean KLD | E p99 | E top-1 | E \|lnPPL\| |
|---|---|---|---|---|
| Qwen | 5.14e-4 | 4.04e-3 | 98.93 % | 8.45e-4 |
| Gemma | 1.75e-3 | 2.11e-2 | 98.36 % | 2.44e-3 |

Qwen's holdout envelope is much tighter than on dev (2.24e-3). The dev long segment dominated
there.

**Holdout evaluation #2** (Qwen, final-v2 = rv32k-Q4_K draft; `results/raw/20261001-005450_phase3-holdout-eval2-qwen35-9b`, canary +0.14 %, valid):

| Workload | v2 vs R [95 % CI] | S vs R | v2 vs S [95 % CI] | TTFT ratio v2/R (median) |
|---|---|---|---|---|
| S-greedy | **1.909 [1.820, 2.005]** | 1.639 | **1.165 [1.141, 1.190]** | 1.028 |
| S-sampled | 1.706 [1.620, 1.795] | 1.489 | 1.146 | 1.056 |
| L | 1.766 [1.685, 1.881] | 1.590 | 1.111 | 1.066 |

Q2 (`results/raw/q2/holdout_eval2_final-v2_qwen35-9b.json`): 18 items, **0 hard**,
identical-token share 74.5 %.

**Host-overhead diagnosis** (diagnostic build `build/diag-timings`, final source plus
`-DDEBUG_TIMINGS`; session `results/raw/20261001-013410_diag-timings`, server logs):

| Phase (average per server loop iteration) | v2 speculation | No speculation |
|---|---|---|
| pre_decode (incl. drafting) | 2.50 ms | 0.06 ms |
| decode | 19.85 ms | 11.96 ms |
| post_decode | 0.96 ms | 0.18 ms |
| sampling | 0.42 ms | 0.17 ms |

These averages include the 15 prompt decodes (estimated +1.9 ms on the speculation decode
average). Per-op GPU profile of one speculative run
(`results/raw/phase1/explore/perflog_server_v2_qwen.log`):
- verify graph (n=4): about 14.4 ms of GPU time with the logger's sync overhead
- MTP draft graphs: about 0.58 ms each

→ About 3–5 ms per speculative step (roughly 20 %) is host-side: the synchronous MTP hook
decode, the logits and state handling, and submission. This is the most promising remaining
lever for Qwen, e.g. overlapping the draft work or reusing command buffers. It is not attempted:
it would take hours, and even with it, full success would still fail on the TTFT criterion.

**Stop decision:** optimization ends here. Remaining: plain-decode llama-bench check
(`results/phase3-micro.console.log`), then the report.

---

## 2026-10-01 ~01:50 — Phase 3 closed; REPORT.md written

- **Plain-decode check** (llama-bench, depths 0/4096/16384, 5 reps; `results/raw/2026100101*_micro_*`):
  the final build is 0.992–1.003× the reference on all 12 pp/tg tests. There is no regression
  from patch 0001's decode-path kernel change.
- **Report tables:** generated by `scripts/make_report_tables.py` →
  `results/raw/phase3/report_tables.md` (sha256 `e20c69a7…`) and inserted verbatim into
  REPORT.md §4.
- **Final integrity checks:**
  - `bench/` manifest verifies (`65baadf4…`) with no diff since tag `bench-frozen-a1`.
  - `results/holdout_access.log` contains only Phase 3 accesses: evaluation #1 from 22:22:56,
    evaluation #2 at 00:54:50.
- **Outcome by the protocol:** **partial success.**
  - Gemma S-greedy reaches 2.066×, which is ≥ 2.0×.
  - Qwen reaches 1.858× (evaluation #1) and 1.909× (evaluation #2).
  - Both models are ≥ 1.25×.
  - The quality gates pass. The TTFT side condition (≤ 5 %) is missed.
  - Most of the gain is stock llama.cpp MTP speculation. The own contribution is
    +14–16.5 % for Qwen over stock speculation, and none for Gemma.

---

## 2026-10-01 16:52 — Resumption after a Windows update; Phase 2c (extra time, dev-only decisions)

- **User (chat):** "Go on, Windows did an update". The machine rebooted at 16:18.
- **Environment check:**
  - GPU driver unchanged (32.0.31041.1004, Vulkan driverInfo "26.8.1 (LLPC)", API 1.4.349).
  - OS build 26200, power plan "Balanced".
  - Repo clean at `6f9f3f1`, and the tooling manifest verifies (`65baadf4…`).
  - Measurements before and after the update remain comparable. New comparisons still
    interleave R within each session anyway.
- **Goal of Phase 2c:** close the remaining gaps to "full success" (§6).
  1. Qwen greedy needs ≥ 2.0× (eval #2: 1.909×).
  2. TTFT ratio must be ≤ 1.05 at every tested length. Eval #1/#2 missed: Gemma S-greedy 1.089,
     Gemma S-sampled 1.080, Qwen S-sampled 1.056, Qwen L 1.066.
- **Idea for (2):** make my build's prompt processing faster than stock's, so that the drafter's
  prompt cost is outweighed. Measured stock cliffs:
  - flash attention at small n_rows (Qwen n=16: 3978 µs per call vs 128 µs at n=1)
  - the MMQ tile path for 9–64-token batches
- Decisions are made on dev. Any further holdout run will be labeled evaluation #3.

### Phase 2c — iteration 7: medium MMQ tile for small batches (dev tree, not yet committed at the time of writing)

- **Profile:** short-prompt prefill per op, from the last llama-bench block, i.e. after warm-up
  (`results/raw/phase2c/perflog_final_*`). In stock and final, the MMQ (`MUL_MAT`) path
  dominates; flash attention is negligible here. The earlier 31.8 ms FA figure at k=16 came
  from the warm-up and pipeline-compile block.

  | Model | k=16 | of which MMQ | k=64 | of which MMQ |
  |---|---|---|---|---|
  | Qwen | 97.7 ms | 93.5 ms | 69.6 ms | 63.1 ms |
  | Gemma | 44.8 ms | 41.3 ms | 31.7 ms | 26.7 ms |

- **Hypothesis:** the non-coopmat2 tile selector uses the small MMQ tile (32×32, one 32-wide
  subgroup) for n ≤ 32, and that tile is pathologically slow on this RDNA3 GPU.
- **Change:** in `matmul_tile_selector`, n ≤ 32 uses the medium tile when m > 32.
- **Quality:** qdump at ub=16 is **bit-identical** to stock (sha `57a47e79…` for both builds;
  `results/raw/q1/p2c_tile_bitcheck_qwen_ub16.summary.json`).
- **Micro** (llama-bench pp sweep at depth 0, 5 reps, `results/raw/phase2c/ppsweep_*`):
  - Qwen p9–p32: 89.2 → 57.0 ms
  - Gemma p9–p32: 40.3–41.0 → 31.9–32.9 ms
  - n ≥ 48 unchanged

### Session `…p2c-tile` — INVALID (not used)

The canary was 66.13 → 89.61 t/s, a drift of +35.5 %. The start canary ran right after the
post-update reboot, presumably during background work. Per §5.4 the session is invalid; its
numbers are not used. Two later canary checks gave 89.94 and 89.92 t/s, so the system is stable
again.

### Finding (stock behaviour, NOT changed) — checkpoint-driven prompt splitting

For hybrid (`COMMON_CONTEXT_SEQ_RM_TYPE_RS`) and SWA models, llama-server splits every prompt into
up to 3 decode batches, so that it can save context checkpoints for later prompt-cache reuse:
1. at the last user message
2. at `n − (4 + n_ubatch)`
3. at `n − 4`

(`tools/server/server-context.cpp:3531` ff.) Each extra batch costs a full weight pass. That
explains the server's ~60–75 ms prompt eval for 26-token Gemma prompts against ~40 ms in
llama-bench. The checkpoints are created even when `cache_prompt=false`. Skipping them in that
case would improve exactly this benchmark (which uses `cache_prompt=false`), but not real
default use. It is therefore **deliberately not changed** (anti-gaming), only documented.

### Phase 2c — iteration 8: MTP prompt window (draft-only; `common/speculative.cpp`)

- **Problem:** Qwen's L TTFT is +6.4–7.3 % with MTP. During prefill, the drafter decodes every
  prompt ubatch through its MTP layer.
- **Change:** during prompt processing, the MTP drafter only buffers (token, pos, target hidden
  state) for the last W prompt positions, in a ring buffer.
  - The buffer is decoded once in `begin()`, which the server calls when the prompt is complete,
    or before the first non-prompt batch.
  - Prompt batches are recognized by their output flags: verification batches request logits
    for every row.
  - W comes from the environment variable `FASTLLAMA_MTP_PROMPT_WINDOW` (default 2048; 0 =
    stock behaviour).
  - Not used when the drafter shares the target's KV (Gemma) or for chained heads.
- **Quality:** draft-only. The target's computation is untouched.
- **Smoke test** (`…p2c-tw-smoke`, dev L, 1 pass): TTFT 3.13 / 12.76 / 28.07 s, essentially
  equal to stock without speculation in the reference session (3.14 / 12.70 / 28.11 s). No
  errors.
- **ABBA session:** `…p2c-tw`.

### Phase 2c ABBA session (dev, `results/raw/*_p2c-tw`, canary −0.54 %, valid)

Speedup vs the within-session R, with TTFT ratio vs R in parentheses (median over prompts):

| Workload | final-v2 | + tile | + tile + MTP window 2048 |
|---|---|---|---|
| Qwen S-greedy | 2.020 (1.113) | 2.002 (1.060) | 2.001 (**0.999**) |
| Qwen L | 1.744 (1.071) | 1.744 (1.071) | 1.682 (**1.025**) |
| Gemma S-greedy | 2.049 (1.026) | 2.050 (**0.981**) | — (window n/a) |

Relative to final-v2 (`summary_vs_finalv2.json`):

| Change | Qwen S tg | Qwen S TTFT | Qwen L tg | Qwen L TTFT | Gemma tg | Gemma TTFT |
|---|---|---|---|---|---|---|
| tile | 0.991 [0.989, 0.993] | 0.970 | 1.000 | 1.000 | 1.000 | 0.978 |
| tile + window | 0.991 | 0.934 | 0.965 [0.913, 1.019] | 0.964 | — | — |

→ **Both changes remove the TTFT regressions on dev** (all TTFT ratios ≤ 1.025). Their costs:
- Qwen short-prompt tg: −0.9 % (tight CI; the cause is unclear, because the verify path
  does not use MMQ).
- Qwen long-context tg: −3.5 % (not significant). The windowed drafter sees less of the prompt
  and accepts slightly fewer tokens.

The dev2 binary was built from the uncommitted tree, which differed only by a comment ("EXPERIMENT")
from the committed iteration-7 code.

**Commits:** iteration 7 `de58964` (`patches/llama.cpp/0006-*`) and iteration 8 `277447c`
(`0007-*`). Next: Qwen draft n=4 vs n=3 on the tile+window build (`…p2c-n4`).

**Qwen draft n=4 vs n=3 on the tile+window build** (`results/raw/*_p2c-n4`, ABBA, canary
−0.08 %): S-greedy 0.996 [0.977, 1.017]; L 0.971 [0.955, 0.995] → **keep n=3.**

### v3 decided (dev only) and rebuilt cleanly

- **Patch set:** b11284 + `patches/llama.cpp/0001–0003, 0006, 0007`. 0004/0005 cancel out and
  are not applied.
- **Rebuild:** fresh clone `src/llama.cpp-final3`. The tree hash `8da52347…` is **identical** to
  the dev HEAD tree. Clean build `build/final3-vulkan`, commit `bf51daa`, empty-diff hash.
- **Engine config:** `configs/engines/final-v3.json`.
  - Qwen: rv32k-Q4_K draft sidecar, n=3.
  - Gemma: official drafter, n=3.
  - MTP prompt window: 2048 (code default).
- **Next:** holdout Q1 for v3 (ub=1/4/512, plus ub=16 for the tile path), then **holdout
  evaluation #3** (both models).

---

## 2026-10-01 ~18:00–20:45 — Holdout Q1 for v3, evaluation #3, Q1 finding on the ub=16 path, host-time diagnosis, stop

### Holdout Q1 dumps for v3 (`results/raw/q1/final-v3-nospec_*_holdout_ub{1,4,16,512}_holdout.dump.json`)

All four paths have the **same logit hashes as stock R**:

| Model | ub1 | ub4 | ub512 | ub16 |
|---|---|---|---|---|
| Qwen | `d1872e6c` | `e3917e19` | `87a328b5` | `050cfb3b` |
| Gemma | `5144bf1f` | `25d9339f` | `0ad7ab74` | `e3f93566` |

The ub=16 dumps of the evaluation #1 build (`results/raw/q1/final-nospec_*_holdout_ub16.dump.json`,
console log `results/phase3-q1-dumps-final-ub16.console.log`) have the same hashes as well.

### Holdout evaluation #3 (v3; sessions `results/raw/20261001-181639_phase3-holdout-eval3-qwen35-9b` and `…185318_…-gemma4-e4b`)

Canaries +0.01 % and −0.70 %, both valid.

| Model | Workload | v3 vs R [95 % CI] | S vs R | v3 vs S [95 % CI] | TTFT ratio v3/R (median / max) | pp ratio v3/R (median / min) |
|---|---|---|---|---|---|---|
| Qwen | S-greedy | **1.895 [1.806, 1.992]** | 1.635 | 1.159 [1.136, 1.185] | 1.000 / 1.074 | 0.961 / 0.895 |
| Qwen | S-sampled | 1.709 [1.630, 1.795] | 1.489 | 1.148 [1.122, 1.173] | 1.037 / 1.074 | 0.960 / 0.906 |
| Qwen | L | 1.682 [1.635, 1.768] | 1.592 | 1.056 [1.009, 1.087] | 1.025 / 1.036 | 0.976 / 0.960 |
| Gemma | S-greedy | **2.060 [1.926, 2.211]** | 2.072 | 0.994 [0.992, 0.996] | 1.007 / 1.092 | 1.000 / 0.938 |
| Gemma | S-sampled | 1.951 [1.823, 2.097] | 1.951 | 1.000 [0.998, 1.002] | 0.996 / 1.132 | 0.993 / 0.958 |
| Gemma | L | 1.806 [1.735, 1.850] | 1.809 | 0.998 [0.996, 1.000] | 1.004 / 1.020 | 0.996 / 0.984 |

**What evaluation #3 shows:**
- **TTFT/pp on medians:** every workload median is within 5 %, as is every long document.
- **Long-context Qwen pays for it:** 1.682× vs 1.766× in evaluation #2. This is the window
  trade-off; on dev the cost was −3.5 % and not significant.
- **Gemma:** v3 vs S is 0.994 on S-greedy, the same as evaluation #1's final vs S (0.994
  [0.992, 0.996]). It is small and reproducible; the cause was not investigated.
- **Q2:** `results/raw/q2/holdout_eval3_final-v3_{qwen35-9b,gemma4-e4b}.json`, **0 hard**
  divergences for both models. Identical-token share 75.3 % for Qwen and 58.8 % for Gemma.

**TTFT/pp noise** (post hoc from the same session files, `scripts/ttft_noise.py` →
`results/raw/phase3/ttft_noise_eval3.json`). Each engine was compared with itself across its two
blocks:
- **TTFT:** single short-prompt ratios range from 0.84 to 1.34, while the medians stay within
  0.968–1.006.
- **Engine-reported pp:** much steadier, within 0.966–1.037.
- **Consequence:** Qwen v3's worst short-prompt pp ratios (0.895, 0.906) are real, not noise.
  The drafter's prompt pass still costs something on short prompts.

### Q1 finding: stock's own ub=16 path lies outside the envelope

Gate files: `results/raw/q1/gate_holdout_{m}_final-v3.gate.json` (candidate paths ub1/4/512/16)
and `gate_holdout_{m}_stock-ub16.gate.json` (stock R at ub=16 as the candidate).

| Model | Path | mean KLD | E mean KLD | p99 | E p99 | Verdict |
|---|---|---|---|---|---|---|
| Qwen | stock R ub=16 = v3 ub=16 | 5.206e-4 | 5.137e-4 | 4.269e-3 | 4.045e-3 | FAIL |
| Gemma | stock R ub=16 = v3 ub=16 | 2.325e-3 | 1.749e-3 | 3.129e-2 | 2.107e-2 | FAIL |

- **What passes:** ub1, ub4 and ub512 pass for both models, exactly as in evaluation #1.
- **Where the excess comes from:**
  - Qwen: per segment, the ub=16 excess has the same size as the ub=512 variant's.
  - Gemma: concentrated in a few segments, e.g. corpus-03 at 3.19e-3 vs 0.82e-3 for ub=512.
- **Interpretation:** this is a property of stock llama.cpp b11284. R itself prefills every short
  prompt with batches of 9–32 tokens, and every build I made has the same ub=16 logits.
  Evaluations #1/#2 did not test this path; their "Q1 PASS" covers ub1/4/512 only.
- **Two readings of A1.1:**
  - Read literally ("every path … plus its prompt path"), Q1 fails for every engine, including
    stock.
  - Read by its intent (stock's own variation), v3 is bit-identical to stock on all measured
    paths.
- **Decision left to the user:** adding R(ub=16) to the envelope would be a post-hoc amendment
  after the results are known. I did **not** do it. REPORT §1 and §8 state the open decision.

### Host-time diagnosis (dev only; diagnostic branch `diag-host` in the worktree `src/llama.cpp-diag`, `patches/llama.cpp/diag-host-timers.diff`, build `build/diag-host`)

Wall-clock timers were added around the server's speculative step and the per-stage host work
inside `llama_context::decode`. The run used Qwen v3 on dev S-greedy with 1 pass
(`results/raw/20261001-201224_diag-host2`, summed by `scripts/fl_diag_sum.py`):

| Part of one step (17.77 ms) | ms |
|---|---|
| GPU wait for the 4-token verify (`llama_synchronize`) | 12.83 |
| Drafting: 3 MTP decodes plus backend top-k, including their GPU time | 2.45 |
| Verify `llama_process`: graph reused in 375–383 of every 400 calls; command recording 1.20–1.29, everything else < 0.15 | 1.39 |
| Target sampling (`common_sampler_sample_and_accept_n`, 4 rows) | 0.52 |
| MTP hook `common_speculative_process` (host; its decode is asynchronous) | 0.35 |
| `common_sampler_clone` (only needed for checkpoint restores) | 0.32 |

- **Plain decode for comparison** (same build and session, no speculation): `llama_process`
  1.05 ms plus sync 10.19 ms per token.
- **Run-to-run variation:** an earlier identical run (`…200626_diag-host`) measured 3.1 ms for
  the verify `llama_process`, so host time itself fluctuates between runs.
- **Kernel bandwidth:** in the existing per-op profile of a verify graph
  (`results/raw/phase1/explore/perflog_server_v2_qwen.log`, lines 265–301), the large mat-vecs
  reach 416–504 GB/s by weight bytes (`scripts/perflog_bandwidth.py` →
  `results/raw/phase3/verify_kernel_bandwidth_qwen.json`). That is the same regime as
  single-token decoding.

**Stop decision.** No large lever is left:
- The verify is bandwidth-bound.
- Drafting is 3 small dependent GPU round trips.
- The safely removable host work, deferring the sampler clone, is about 2 % of a step.
- A faster greedy sampling path would change tie-breaking semantics.
- Chaining the drafts into one GPU graph would take hours for about 3 %.

Qwen would need about +5.5 % to reach 2.0×. A gain of that size, measured on a fourth use of
the holdout set, would not be credible evidence. Optimization ends here; REPORT.md is updated
to evaluation #3.
