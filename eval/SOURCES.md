# Evaluation data sources (PROTOCOL §7)

Raw files, URLs, licenses, sizes and SHA-256 are listed in `eval/raw/SOURCES.tsv`. They were
fetched by `scripts/fetch_eval_data.sh` on 2026-09-30.

| Source | License | Used for |
|---|---|---|
| WikiText-2 raw, test split (mirror: huggingface.co/datasets/ggml-org/ci) | CC BY-SA 3.0 | Q1 prose segments |
| databricks-dolly-15k | CC BY-SA 3.0 | Chat, creative, and summarization prompts; Q1 chat segments |
| GSM8K test (openai/grade-school-math) | MIT | Math prompts |
| HumanEval (openai/human-eval) | MIT | Code prompts |
| CPython 3.13.6 stdlib sources (local install, `Lib/*.py`) | PSF License | Q1 code segments (file names + SHA-256 in corpus.jsonl) |
| Project Gutenberg #1342, #2701, #1661, #98, #84, #1400 | Public domain in the USA | Long-context documents (L-4k/16k/32k, Q1-long) |

**Split:** `scripts/make_splits.py` uses seed 20260930 and 3 prompts per category per split.
It writes `eval/dev/` and `eval/holdout/`. The hashes are in `eval/SPLITS.txt`. The holdout files
are read-only and sealed until Phase 3. Every access through the harness is logged to
`results/holdout_access.log`.
