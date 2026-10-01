# Third-party notices

## llama.cpp (MIT)

The files in `patches/llama.cpp/` are changes to llama.cpp release b11284 (`25747b08`),
<https://github.com/ggml-org/llama.cpp>. They contain llama.cpp code as diff context and are
distributed under llama.cpp's license:

```
MIT License

Copyright (c) 2023-2026 The ggml authors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

`scripts/make_mtp_sidecar*.py` and `scripts/gguf_*.py` use the `gguf-py` package from the same
repository (MIT) at run time. It is not included here.

## Evaluation data (in `eval/`, and quoted in `results/`)

The prompt and corpus files in `eval/dev/`, `eval/holdout/` and `eval/holdout_tokens/` are
excerpts of the sources below and remain under **their** licenses. The raw downloads are not
included. `scripts/fetch_eval_data.sh` re-fetches them, and `eval/raw/SOURCES.tsv` lists the
URLs and SHA-256 hashes.

| Source | License |
|---|---|
| WikiText-2 raw | CC BY-SA 3.0 |
| databricks-dolly-15k | CC BY-SA 3.0 |
| GSM8K (openai/grade-school-math) | MIT |
| HumanEval (openai/human-eval) | MIT |
| CPython 3.13 standard library sources | PSF License |
| Project Gutenberg #1342, #2701, #1661, #98, #84, #1400 | Public domain in the USA |

Model outputs in `results/` were generated from these prompts.

## Models (not included)

No model weights are included. `models/MODELS.md` lists the files used, with SHA-256 hashes,
sources and licenses (Gemma 4 E4B and Qwen3.5 GGUFs by Unsloth, plus the official Gemma 4
E4B MTP drafter). The Qwen MTP sidecar files are derived locally by `scripts/make_mtp_sidecar*.py`.
