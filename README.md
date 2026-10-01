# Faster-than-llama.cpp local inference on an RX 7800 XT: a measured attempt

A time-boxed R&D project. The goal: make batch-1 local LLM generation on an AMD Radeon RX 7800 XT
(16 GB, Windows 11, Vulkan) **2–3× faster than stock llama.cpp**, with output quality unchanged.
Two models were used: **Gemma 4 E4B Q8_0** and **Qwen3.5-9B Q4_K_M**.

Everything was pre-registered in [PROTOCOL.md](PROTOCOL.md): quality thresholds, speed method,
success and abort criteria. Every step is logged in [JOURNAL.md](JOURNAL.md), and the results are
in [REPORT.md](REPORT.md). Every number in the report comes from a file in `results/`.

## Result in one table

Holdout evaluation #3 (final configuration "v3", clean build). Speedup of generation
throughput vs stock llama.cpp b11284 without speculation, with 95 % bootstrap CIs over prompts:

| Model | Greedy | Sampled | Long context (4k–32k) | TTFT ratio vs stock (median: greedy / sampled / long) |
|---|---|---|---|---|
| Gemma 4 E4B Q8_0 | **2.060×** [1.926, 2.211] | 1.951× | 1.806× | 1.007 / 0.996 / 1.004 |
| Qwen3.5-9B Q4_K_M | **1.895×** [1.806, 1.992] | 1.709× | 1.682× | 1.000 / 1.037 / 1.025 |

Source: REPORT.md §1 and §4.

**The honest summary:**
- **3× was not reached, and 2× only for Gemma.** On speed, the protocol level is "partial
  success".
- **Most of the gain is stock llama.cpp's own MTP speculative decoding, configured well.** My
  patches add +15.9 % on top of that for Qwen and nothing for Gemma.
- **Quality:**
  - Every target-model execution path is **bit-identical** to stock llama.cpp (equal logit
    hashes).
  - Free-running greedy generation shows zero hard divergences.
- **Open point:** stock llama.cpp's own 16-token prompt path falls outside the pre-registered Q1
  noise envelope, so a literal reading of the quality gate fails every engine, stock included.
  This is documented, not "fixed" by moving thresholds (REPORT §1, §8).
- **Why not 3×:** batch-1 decoding already runs at about 70 % of memory bandwidth. A speculative
  step is about 72 % GPU verify time, and the verify kernels are near the bandwidth roofline
  (REPORT §7, §6).

## What I changed (patches against llama.cpp b11284)

| Patch | What | Effect |
|---|---|---|
| `0001` | Vulkan MMVQ decode-once for Q4_K/Q5_K/Q6_K | Removes the collapse of speculative verification at 4–7 tokens; bit-identical |
| `0002` | RDNA3 rows-per-workgroup for more than 4 columns | Faster multi-token verify; bit-identical |
| `0003` | Reduced-vocabulary (FR-Spec-style) MTP draft head for Qwen3.5 | Draft head over 64k or 32k instead of 248k vocabulary rows; draft-only |
| `0006` | Medium MMQ tile for 9–32-token batches on non-coopmat2 GPUs | Faster short-prompt prefill; bit-identical |
| `0007` | MTP prompt window (`FASTLLAMA_MTP_PROMPT_WINDOW`, default 2048) | Removes most of MTP's time-to-first-token penalty; draft-only |

`0004`/`0005` are an experiment and its revert. `exp-*.diff` are experiments that were not
kept. `diag-host-timers.diff` is diagnostic instrumentation only.

## Repository layout

| Path | Content |
|---|---|
| `PROTOCOL.md` | Pre-registered plan, including Amendment 1 (noise-envelope quality gate) |
| `JOURNAL.md` | Chronological lab journal, including failures and dead ends |
| `REPORT.md` | Final report: results, attribution, limitations, reproduction |
| `patches/llama.cpp/` | All code changes as `git format-patch` files plus experiment diffs |
| `bench/` | Frozen measurement harness (manifest `bench/MANIFEST.sha256`): streaming timing, sessions, Q1 logit dumps and KLD (`qdump`), Q2 divergence check |
| `scripts/` | Build, data splits, GGUF sidecar creation, report tables, post-hoc analysis |
| `configs/engines/` | Exact engine definitions (binary and arguments) for every measured configuration |
| `eval/` | Dev and sealed holdout splits, with sources and hashes (raw downloads not included) |
| `env/` | Hardware, driver and toolchain inventory |
| `models/MODELS.md` | Model files with SHA-256, sources and licenses (weights not included) |
| `results/` | All raw measurement outputs: per-request JSONL, server logs, canaries, Q1/Q2 results. Excludes the multi-GB logit dumps, whose hashes are in `results/q1dumps/*.json` |

## Reproducing

Full instructions are in REPORT.md §9. In short:

1. Portable toolchain inside the working directory (no system installs): LLVM-MinGW, CMake,
   Ninja, Vulkan SDK. See JOURNAL entry 002 for versions and hashes.
2. Check out llama.cpp `b11284`, apply `patches/llama.cpp/000[123]-*.patch` and `000[67]-*.patch`,
   and build with `scripts/build_llama.sh`.
3. Get the model files listed in `models/MODELS.md` and verify their hashes. Then build the Qwen
   MTP draft sidecar with `scripts/make_mtp_sidecar.py` and `scripts/make_mtp_sidecar_rv.py`.
4. Run, for example:

   ```bash
   llama-server -m Qwen3.5-9B-Q4_K_M.gguf -ngl 99 -c 40960 -np 1 \
     -md Qwen3.5-9B-MTP-sidecar-rv32k-q4k.gguf --spec-type draft-mtp --spec-draft-n-max 3
   ```

**Note:** the engine configs and some scripts contain absolute paths from the original machine
(`H:/python-projects/Fast llama/…`). Adjust them to your checkout.

## Licenses

- **Patches:** derived from llama.cpp (MIT). See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
- **Evaluation excerpts:** keep their source licenses (CC BY-SA 3.0, MIT, PSF, public domain).
  See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
- **Everything else** (documents, scripts, benchmark tooling, configs, results): MIT, see
  [LICENSE](LICENSE).
