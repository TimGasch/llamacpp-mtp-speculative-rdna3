# PROTOCOL — Fast local LLM inference vs. llama.cpp

Status: **v1.0 — APPROVED by the user on 2026-09-30** ("I think you can go on"). The approval
was taken to cover the following: the protocol as drafted, the 8 h budget (§10), downloads
D1–D5 (§3.1), and the primary baseline without speculation (§5.5). The system-wide installs
S1/S2 were **not** explicitly approved and will not be done without asking again.
This file is frozen;
any later change is appended as a dated, numbered amendment in §12 and never applied retroactively
to results that were already measured.

---

## 1. Goal

Make batch-1 token generation of two target models on this machine **≥ 2× (stretch: ≥ 3×) faster
than unmodified llama.cpp**, with output quality unchanged as defined in §4. If that is not
achievable with reasonable effort, the deliverable is a clearly stated negative result
backed by measurements (in particular a roofline analysis, §9).

Prompt processing (pp) throughput and time to first token (TTFT) are tracked as secondary
metrics and must not regress beyond the limits in §6.

## 2. Scope

| Item | In scope |
|---|---|
| Hardware | AMD Radeon RX 7800 XT 16 GB (Navi 32 / gfx1101), Ryzen 5 7500F, 32 GB DDR5-6000, Windows 11 Pro 26200. Raw inventory: `env/` |
| Target model A | Gemma 4 E4B-it, **Q8_0** GGUF (unsloth), text model only (7.63 GB blob in the local Ollama store) |
| Target model B | Qwen3.5-9B, **Q4_K_M** GGUF (unsloth), text model only (5.29 GB blob in the local Ollama store) |
| Workload | Single interactive user, batch size 1, short (≤ 512-token) and long (4k / 16k / 32k-token) contexts |
| Primary metric | Generation throughput (tokens/s) on real prompts |
| Secondary metrics | pp throughput, TTFT, peak VRAM |
| Out of scope | Vision/audio encoders (mmproj), multi-user batching, CPU-only inference, model fine-tuning |

The exact GGUF files are copied into `models/` (read-only). Their SHA-256 values, source, and
license are recorded in `models/MODELS.md`. **The reference and every candidate use byte-identical
target weight files.** A candidate that needs a different file (e.g., a re-packed layout) must
derive it losslessly from that file or pass the quality gates in §4 like any other change.

## 3. Constraints (from the task, restated as rules I will follow)

1. Work only inside `H:\python-projects\Fast llama`. No changes to system settings, drivers,
   registry, power plan, or clocks. No overclocking or undervolting.
2. No system-wide installs without asking first. Python packages go into a local `.venv`,
   and portable tools go into `toolchain/`.
3. Only established sources, with licenses respected and recorded. No credentials or
   personal data in any file.
4. Risky or irreversible steps need explicit approval first.
5. All documentation, code comments, and commit messages are written in English.
6. The quality thresholds in §4 are frozen at approval. If the goal cannot be reached within
   them, the result is reported as missed. The thresholds will not be relaxed.

### 3.1 Planned downloads and installs (need your explicit approval)

The survey (`env/toolchain.txt`) found **no C/C++ compiler, no CMake/Ninja, and no HIP SDK**.
The Vulkan SDK 1.4.350 (incl. `glslc`), git, Python 3.13, and uv are present. Sizes are
approximate.

| # | What | Source | Size | Where | Needed for |
|---|---|---|---|---|---|
| D1 | llama.cpp source (shallow clone, current `master`, commit pinned) | github.com/ggml-org/llama.cpp (MIT) | ~50 MB | `src/` | Everything |
| D2 | CMake, Ninja, numpy, and a few small Python packages | PyPI, installed into local `.venv` via uv | ~100 MB | `.venv/` | Build + harness |
| D3 | **LLVM-MinGW** portable C/C++ toolchain (UCRT, x86_64 release zip) | github.com/mstorsjo/llvm-mingw releases (Apache-2.0 w/ LLVM exception) | ~170 MB zip | `toolchain/` | Compiling llama.cpp **without any system install** |
| D4 | Official prebuilt llama.cpp Windows Vulkan release for the pinned commit | github.com/ggml-org/llama.cpp releases | ~30–60 MB | `toolchain/` | Build validation (§5.5) |
| D5 | Eval data: WikiText-2 raw test, dolly-15k, GSM8K test, HumanEval, 2–3 Project Gutenberg public-domain books | Hugging Face datasets / GitHub / gutenberg.org | ~25 MB total | `eval/` | §7 |
| D6 | *(Phase 2, only if H-spec needs it; I will ask again with the exact file name and size)* Qwen3.5-0.8B GGUF | Qwen or unsloth on Hugging Face (Apache-2.0) | ~0.5–1 GB | `models/` | Draft model |

Optional **system-wide** installs, each needing a separate yes or no from you:

| # | What | Size | Why |
|---|---|---|---|
| S1 | Visual Studio 2022 Build Tools (C++ workload + Windows SDK), via winget; requires admin and the MS license | ~6–8 GB on C: | The toolchain llama.cpp's official Windows builds use. Only needed if LLVM-MinGW causes problems. |
| S2 | AMD HIP SDK for Windows (ROCm 6.4/7.x); requires admin | ~3 GB on C: | Allows a HIP/ROCm build of llama.cpp: a second reference backend, plus rocWMMA/hipBLASLt paths. If you decline, I will first check whether AMD's pip-distributed ROCm SDK ("TheRock") can be used inside the local `.venv` instead, and ask again before downloading it. |

The model files are copied from the local Ollama store, so no model download is needed for
the reference.

## 4. Quality definition (gates)

### 4.1 Rationale

Bit-identical logits cannot be the criterion, because any change to the kernels, the
accumulation order, or the batch shape changes floating-point results. The same is true
for llama.cpp itself (for example, a different micro-batch size or backend). "Unchanged
quality" is defined here as follows. The candidate's next-token distributions must be as
close to the reference as floating-point noise, and clearly closer than any lossy change,
such as re-quantizing the weights. In addition, free-running generation must show no
divergence that cannot be explained by near-ties.

As an anchor for scale: in llama.cpp's published KL-divergence tables, quantizing FP16
weights to Q8_0 typically costs a mean KLD on the order of 10⁻³ nats, and Q4_K_M costs about
10⁻². Pure kernel-numerics differences are expected to be one to two orders of magnitude
below the Q8_0 level. The thresholds below lie between those two regimes. They admit
numerically different but mathematically equivalent implementations. They reject anything
that removes information, such as lower-bit weights or KV cache, lossy pruning, or
approximate attention.

### 4.2 Reference for comparison

- **R** = unmodified llama.cpp at the pinned commit, built cleanly, with the same GGUF file.
- For **generation paths**, the reference logits are R in single-token decode (micro-batch 1),
  because that is how R generates tokens.
- For the **prompt path**, the reference logits are R at its default micro-batch (512).
- Each candidate execution path is tested separately. This covers the single-token decode
  path, any small-batch path used for speculative verification (at the batch size actually
  used), and the prompt path.

### 4.3 Gate Q1: teacher-forced distribution match (primary)

R and C both process the same fixed token sequences. For every position they emit the
full-vocabulary next-token log-probabilities. The corpora are the dev corpus during
Phase 2 and the holdout corpus in Phase 3 (see §7). Each corpus has at least 4,096 scored
positions per model, mixing prose, source code, and chat-formatted text. It also includes
one long-context segment: 1,024 scored positions after a prefix of about 15k tokens.

| Metric | Threshold (must hold for every path and both models) |
|---|---|
| Mean KL(P_R ‖ P_C) per position | **≤ 5 × 10⁻⁴ nats** |
| 99th percentile of per-position KL | **≤ 5 × 10⁻³ nats** |
| Top-1 agreement (argmax P_C == argmax P_R) | **≥ 99.5 %** |
| Perplexity ratio, abs(ln(PPL_C / PPL_R)) | **≤ 0.001** (±0.1 %) |

### 4.4 Gate Q2: free-running greedy generation (end-to-end)

This gate catches bugs in sampling, speculation acceptance, and state rollback that
teacher forcing cannot see. For each prompt in the set, generate up to 256 tokens greedily
(temperature 0) with R and with C, then compare the token sequences.

- At the **first divergent position** of each prompt, compute the gap
  Δ = log P_R(R's token) − log P_R(C's token) from R's logits, given the shared prefix.
- A divergence with **Δ > 0.25 nats is a hard divergence**. Justification: 0.25 nats means
  C chose a token that R rates at least 22 % less likely than its top choice. Floating-point
  noise within the Q1 thresholds cannot cause that, so a hard divergence indicates a
  logic error.
- **Gate: zero hard divergences** over the whole prompt set, for both models.
- The following are **reported but not gating**:
  - the exact-match rate of full sequences
  - the share of identical tokens (mean common-prefix length ÷ generated length)
  - the distribution of Δ at soft divergences

  The identical-token share is not a gate because it is chaotic. A single benign near-tie
  changes every token after it, so the metric mostly measures where the first near-tie
  happens. For context, it is always reported next to the same statistic for R against a
  legitimate R configuration (see §4.6).
- For speculative decoding, I additionally report whether the greedy outputs are
  **bit-identical** to R.

### 4.5 Sampling (temperature > 0)

Speculative methods must use an acceptance rule that preserves the distribution exactly,
namely standard rejection sampling or "sample from the target and compare". Correctness
rests on three things:

1. Gate Q1 on the verification path.
2. Gate Q2.
3. A code-level description of the acceptance rule in the journal.

### 4.6 Noise floor (measured in Phase 1, before any optimization)

I run Q1 and Q2 for R against legitimate R variants: a different micro-batch size, and the
HIP backend if it can be built. This gives llama.cpp's own numerical noise.
**If this noise floor exceeds 50 % of any Q1 threshold, I stop and bring it to you before
Phase 2.** I do not adjust anything silently, and I never reopen thresholds after seeing
optimization results.

## 5. Speed metrics and measurement method

### 5.1 Why a custom end-to-end harness

`llama-bench` measures generation on synthetic token streams. That is fine for kernel work
but meaningless for speculative decoding, whose speed depends on the text. The primary
metric therefore comes from an **engine-agnostic streaming harness** (`bench/`). It drives an
HTTP server (llama-server's `/completion` API with token-ID prompts, or an equivalent
endpoint in a custom engine) and timestamps every streamed token client-side with
`perf_counter_ns`. Engine-reported timings are logged alongside as a cross-check.
`llama-bench` (pp512, tg128, at several depths) is also recorded as a secondary,
kernel-level view.

### 5.2 Definitions

- **Generation throughput (primary)**, per request: tg = (N_gen − 1) / (t_last − t_first).
  The aggregate for a prompt set is total generated tokens ÷ total generation time.
- **TTFT**: time from sending the request to receiving the first token, with a cold prompt
  (no prompt-cache reuse).
- **pp throughput**: N_prompt ÷ engine-reported prompt time, cross-checked against TTFT.
- **VRAM**: peak dedicated GPU memory, read from Windows performance counters.

### 5.3 Workload matrix (per model)

| Name | Prompt | Generation | Purpose |
|---|---|---|---|
| S-greedy | Prompt set (§7), 20–300 tokens | 256 tokens, temperature 0 | **Primary** |
| S-sampled | Same prompts | 256 tokens, model-recommended sampling settings, fixed seeds | Honest view for speculative methods |
| L-4k / L-16k / L-32k | Long document plus task, about 4k / 16k / 32k tokens | 256 tokens, greedy | Long-context generation, pp, TTFT |
| micro | `llama-bench` pp512, tg128 at depth 0 / 4k / 16k | — | Kernel-level view |

### 5.4 Procedure and noise control

- **Warm-up:** after loading a model, run 2 warm-up requests and discard them. They absorb
  pipeline compilation and clock ramp-up. Load time is recorded separately.
- **Repetitions:** at least 5 per configuration. For the prompt sets, each prompt runs 3
  times per block and blocks are repeated (see interleaving below).
- **Interleaving:** R and C run in alternating blocks (R C C R …) within one session. This
  cancels slow thermal and clock drift. Only one engine is loaded at a time.
- **Canary:** a fixed `llama-bench` tg128 run of R at the start and end of every session.
  If the two runs differ by more than 3 %, the session is marked invalid and repeated.
- **Environment log per session:**
  - running processes
  - GPU memory in use before the start (other GPU applications must be closed; I cannot
    control this and record it instead)
  - active power plan (not changed)
  - driver version
  - tooling checksum

  Clock and temperature sensors are not readable without extra tools. If a sensor tool is
  needed, I will ask before installing one.
- **Statistics:** report the median together with the IQR, min/max, and coefficient of
  variation. Report speedup = median_C ÷ median_R with a 95 % bootstrap confidence interval
  (resampling prompts). Outliers (beyond 1.5 × IQR) are flagged but never deleted from the
  raw files. If an outlier is excluded from a summary, the summary says so.
- **Significance:** an iteration counts as an improvement only if its median speedup is
  at least 1.02 and the 95 % confidence interval excludes 1.0.

### 5.5 Fair baseline

- **Primary reference:** stock llama.cpp at the pinned commit, as a normal user would run
  it. That means full GPU offload, flash attention per llama.cpp's default or `auto`, and
  otherwise default flags. The reference value for each metric is the **best stock backend
  available** (Vulkan, and HIP if it can be built), so choosing a backend is never counted
  as a gain.
- **Secondary reference:** stock llama.cpp with its own best built-in speculative
  configuration, if that works for these models. This shows how much of any gain is new
  work and how much is just enabling an existing flag.
- **Build validation:** my reference build must be within ±3 % of the official prebuilt
  llama.cpp release for the same commit on `llama-bench`. This proves my own build is not
  handicapped.

## 6. Success and abort criteria

### Success levels

These are judged in Phase 3 on the **holdout** set, with a clean rebuild, and with all
quality gates passing.

| Level | Criterion |
|---|---|
| **Full success** | S-greedy aggregate tg speedup ≥ **2.0×** on **both** models, and no regression in pp or TTFT above 5 % at any tested length |
| Stretch | ≥ **3.0×** under the same conditions |
| Partial | ≥ 2.0× on one model, or ≥ 1.25× on both. Reported as partial, together with the gap |
| Not reached | Below that. Reported with the roofline evidence that explains why |

S-sampled and long-context results are always reported, whether they are good or bad. They
are not part of the pass criterion but will appear in the headline table.

### Abort and stop rules

1. **Budget exhausted** (§10): stop Phase 2 and go to Phase 3 with the best validated state.
2. **Approach dropped** after 3 consecutive iterations without a significant improvement
   (§5.4), or if it cannot pass the quality gates.
3. **Midpoint check** at 50 % of the budget: I give you a status report. If the best
   demonstrated or credibly projected combination is below 1.3×, I recommend stopping
   early and writing up the negative result.
4. **Measurement integrity:** a tooling checksum mismatch, or repeated canary failures,
   stops all measurements until the cause is found.
5. **Anything that needs system changes or new system-wide software:** I stop and ask.

## 7. Evaluation data

- **Sources** (planned; exact files, versions, and licenses go into `eval/SOURCES.md`):
  - Prose: WikiText-2 raw test set (CC BY-SA)
  - Chat, QA, and summarization: databricks-dolly-15k (CC BY-SA 3.0)
  - Math: GSM8K (MIT)
  - Code: HumanEval prompts (MIT) and CPython stdlib source (PSF license, already on disk)
  - Long documents: public-domain books from Project Gutenberg
- **Split:** `scripts/make_splits.py` samples a stratified split with a fixed seed into
  `eval/dev/` and `eval/holdout/`. The categories are chat, code, math, summarization,
  creative, and long-document. The script prints only counts and SHA-256 hashes, never
  content.
- **Holdout sealing:**
  - Holdout files are set read-only, their hashes are committed, and I do not open them
    before Phase 3.
  - The harness loads them only with an explicit `--phase3-holdout` flag, and every such
    access is appended to `results/holdout_access.log`.
  - Before Phase 3 that log must be empty, which you can check yourself.
- Prompts are formatted with each model's own chat template. For Qwen3.5 the template's
  default thinking mode is kept, as a real user would have it.

## 8. Measurement tooling protection

- At the end of Phase 1 all files in `bench/` get a SHA-256 manifest (`bench/MANIFEST.sha256`)
  and a git tag `bench-frozen`, and are set read-only.
- Every measurement run first verifies the manifest and writes the manifest hash into its
  result file. A run with a mismatch aborts.
- If I find a bug in the tooling during Phase 2, I stop and ask you. Any approved fix is
  committed as a separate "tooling amendment", and **the reference is re-measured** with the
  fixed tooling before any comparison.

## 9. Technical plan

### 9.1 Realism check (a prior to be tested, not a result)

Batch-1 generation is limited by memory bandwidth, because every token streams all active
weights from VRAM once. The 7800 XT's spec-sheet bandwidth is 624 GB/s (256-bit
GDDR6 at 19.5 Gbps).

In Phase 1 I will measure two things:

- the **bytes read per token** from the GGUF tensor inventory (excluding lookup-only tables
  such as token embeddings and Gemma's per-layer embeddings)
- the **achievable bandwidth**, as the best observed streaming and mat-vec GB/s in
  `test-backend-ops`

Together these give a hard upper bound, tg_max ≈ achievable bandwidth ÷ bytes per token.
If llama.cpp already reaches X % of tg_max, then kernel-level work alone can yield at
most 1/X. For example, at 60 % the ceiling is 1.67×, below the 2× target.

My prior is that llama.cpp's mature Vulkan path gets a large fraction of that bound for
standard layers. There may be more headroom in newer operators, such as Qwen3.5's
Gated-DeltaNet recurrence and Gemma's per-layer embeddings, and in host-side overhead.
**A ≥ 2× gain therefore almost certainly requires producing more than one token per pass
over the weights, i.e. speculative decoding**, because lossless weight-byte reduction is
not available at these thresholds. The gain from speculation depends on the content:
high for code and structured text, lower for open-ended sampled chat. I expect ≥ 2× to be
plausible on some workloads and ≥ 3× to be unlikely overall. Phase 1 will confirm or refute
this with data.

### 9.2 Hypotheses, in planned order

Each hypothesis is one or more iterations, with one change per iteration.

1. **H-spec-Qwen: speculative decoding for Qwen3.5-9B.** Three candidate drafters:
   - the model's native MTP head (a separate unsloth GGUF with MTP weights exists locally;
     the main-weight identity must be verified tensor by tensor)
   - a small same-tokenizer draft model (Qwen3.5-0.8B)
   - n-gram / prompt-lookup drafting

   Key risk: the hybrid Gated-DeltaNet layers keep recurrent state, which must be
   checkpointed and rolled back when draft tokens are rejected. If llama.cpp lacks this for
   this architecture, implementing it is the core engineering task.
2. **H-spec-Gemma: speculative decoding for Gemma 4 E4B.** Candidate drafters:
   - Gemma 4 E2B (available locally, but a weak ratio of about 0.4–0.5 of the target's cost)
   - an official small drafter, if one exists
   - n-gram / prompt lookup
   - self-speculation using the nested MatFormer sub-model, or layer skipping
3. **H-host: host-side overhead per token.** Examples are CPU sampling over a vocabulary of
   about 250k, logits read-back, and graph building or submission. Fixes include GPU
   argmax/sampling, graph reuse, and fewer synchronizations.
4. **H-kern: decode-path kernel work**, guided by the per-op profiler:
   - mat-vec tuning for Q4_K/Q8_0 on RDNA3 (workgroup shape, subgroup size 32 vs. 64,
     integer dot products)
   - operator fusion (norm+matmul, gate/up, DeltaNet recurrence)
   - lossless weight re-layout for coalesced loads
5. **H-long: long-context attention and KV path.** Lossless changes only, e.g.
   flash-attention variants and split-K for decode at depth.
6. **H-backend: alternatives** (HIP/ROCm build, other engines), judged only on the same
   gates. Engines that require their own quantization of the weights (e.g., MLC) will
   almost certainly fail Q1 against the reference Q4_K_M/Q8_0 weights, so they have low
   priority.

## 10. Budget

- **Proposed: 8 hours of active working time**, excluding time spent waiting for your
  answers. Split: Phase 1 ≈ 2.5 h, Phase 2 ≈ 4 h, Phase 3 ≈ 1.5 h.
- Midpoint status at about 4 h.
- Hard stop at 8 h. Any extension only with your approval.

## 11. Working directory layout and traceability

```
Fast llama/
├── PROTOCOL.md          this file (frozen after approval; amendments in §12)
├── JOURNAL.md           chronological log: hypothesis → change → measurement → conclusion
├── REPORT.md            Phase 3 final report
├── env/                 raw hardware / driver / toolchain inventory
├── scripts/             setup, split, and build scripts
├── bench/               measurement + quality tooling (frozen after Phase 1, checksummed)
├── eval/dev/            data used during optimization
├── eval/holdout/        sealed until Phase 3
├── models/              GGUF files (not in git) + MODELS.md (hashes, sources, licenses)
├── results/raw/<run>/   untouched raw outputs (JSON/CSV) + run metadata; never edited
├── patches/             diffs of every modified project against its upstream base commit
├── src/                 upstream clones (reference clone never modified) and own code (not in git; recorded via commit + patches)
├── build/               build trees (not in git)
└── toolchain/           portable build tools (not in git; versions + hashes recorded)
```

- The outer directory is a git repository with **one commit per iteration**. Each commit
  contains the journal entry, the raw results, and the exported patch.
- Code changes to llama.cpp live on a branch in `src/llama.cpp-dev`, and every iteration
  commit there is exported to `patches/`.
- Every result file records:
  - the command line
  - the engine commit and patch hash
  - the build flags
  - the model SHA-256
  - the tooling manifest hash
  - the driver version
  - a timestamp
- Large intermediate files, such as full-vocabulary logit dumps, are not committed. Only
  their hashes and the per-position metrics derived from them are.

## 12. Amendments

### Amendment 1: 2026-09-30, approved by the user ("Go with option A")

**Trigger:** §4.6. The Q1 noise floor measured in Phase 1 is llama.cpp's own difference between
its stock configuration choices. It exceeds the §4.3 absolute thresholds by 3–8×
(JOURNAL entry 004, `results/raw/q1/noisefloor_*`). No optimization results existed when this
amendment was made.

**A1.1: Q1 is redefined as a noise-envelope gate.** It replaces the absolute thresholds of §4.3.

For each model and each evaluation corpus (dev in Phase 2, holdout in Phase 3), the frozen
tooling measures three stock llama.cpp b11284 variants against the reference decode path
R(ub=1). All three use the pinned server arguments:

- V1 = R at ub=512 (the prompt path)
- V2 = R at ub=4 (the batched verify path)
- V3 = R at ub=1 with `-fa off`

The envelope for that model and corpus is:

- E_meanKLD = max over V of mean KLD
- E_p99 = max over V of p99 KLD
- E_top1 = min over V of top-1 agreement
- E_ppl = max over V of \|ln(PPL_V / PPL_R)\|

A candidate execution path X passes Q1 if C_X compared against R(ub=1) meets all four
conditions:

- mean KLD ≤ E_meanKLD
- p99 KLD ≤ E_p99
- top-1 agreement ≥ E_top1
- \|ln PPL ratio\| ≤ E_ppl

X covers every path the candidate uses to produce emitted tokens' distributions, plus its prompt
path. In Phase 3 the envelope is **re-measured on the holdout corpus** before the candidate is
evaluated. The envelope variants are fixed as listed above and cannot be chosen after the fact.

**A1.2: design rule (hard constraint, in addition to A1.1).** Calibration showed that a mildly
lossy change can fall inside the envelope: an 8-bit KV cache did. Therefore a candidate may use
only numeric techniques that stock llama.cpp b11284 **already applies by default on this GPU for
the same model in some execution path**. Examples: int8 (q8_1) activation quantization for
matmuls, the stock flash-attention precision, and any accumulation order. **Not allowed:**

- lower-bit or re-quantized weights. Weights must be byte-identical to the target file or a
  lossless re-layout of it.
- KV-cache quantization or any KV type other than the default
- approximate or sparse attention
- layer skipping or early exit for emitted tokens
- any other approximation stock llama.cpp does not apply by default

Draft models and draft heads are exempt, because they only propose tokens and the unchanged
target verifies every emitted token.

**A1.3: unchanged.** Gate Q2 (§4.4: zero hard divergences, Δ > 0.25 nats), the sampling rule
(§4.5), and all speed, success, and abort criteria.

**A1.4: tooling amendment.**
- `bench/q1_gate.py` evaluates A1.1 from the existing `q1.py` summary files.
- The measurement code (`q1.py`, `qdump`, `session.py`) is unchanged, so the Phase 1 reference
  measurements remain valid.
- The manifest is regenerated and tagged `bench-frozen-a1`.

**A1.5: reference backend.** HIP could not be run without the system-wide HIP SDK (S2, not
approved). The official ROCm build needs `hipblas`/rocBLAS from a system install. The reference
is therefore Vulkan only, as §5.5 allows ("HIP if it can be built").
