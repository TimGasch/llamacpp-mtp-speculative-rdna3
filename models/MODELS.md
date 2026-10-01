# Model files

The GGUF files are copied byte-for-byte from the local Ollama blob store. They are not in git,
so this table is the authoritative record. Ollama blobs are content-addressed: each file name is
its SHA-256, and the copies were verified to match (`results/raw/phase1/` and JOURNAL entry 002).
Files are read-only.

| File | Role | SHA-256 | Bytes | Origin (Ollama tag) | Upstream | License (from GGUF metadata) |
|---|---|---|---|---|---|---|
| `gemma-4-E4B-it-Q8_0.gguf` | Target model A | `a2232a649523c36bf530f1dc3614eb8c800645c4227390381c8b05d4d6eee05a` | 8192951456 | `hf.co/unsloth/gemma-4-E4B-it-GGUF:Q8_0` | base: google/gemma-4-E4B-it, quantized by Unsloth | apache-2.0 (link: ai.google.dev/gemma/docs/gemma_4_license) |
| `Qwen3.5-9B-Q4_K_M.gguf` | Target model B | `03b74727a860a56338e042c4420bb3f04b2fec5734175f4cb9fa853daf52b7e8` | 5680522464 | `hf.co/unsloth/Qwen3.5-9B-GGUF:Q4_K_M` | base: Qwen/Qwen3.5-9B, quantized by Unsloth | apache-2.0 |

Only the text model is used. The vision/audio projector blobs of the same Ollama tags are out of
scope (PROTOCOL §2).

The full tensor and metadata inventories are in `results/raw/phase1/gguf_inventory_*.json`.

## Draft / auxiliary files (speculative decoding only)

These files never produce emitted tokens: every drafted token is verified by the unchanged target
model. They affect speed only.

| File | SHA-256 | Bytes | Source | License | Note |
|---|---|---|---|---|---|
| `Qwen3.5-9B-MTP-Q4_K_M.gguf` | `e8dd94817e95d6c0939102049d068418269978377b13616c4726235e232841fe` | 5868826976 | local Ollama store (`hf.co/unsloth/Qwen3.5-9B-MTP-GGUF:Q4_K_M`) | apache-2.0 | **Main weights differ from the target** (248/427 tensors, see `results/raw/phase1/tensor_diff_qwen35_vs_mtp.json`). Used only as the source of the MTP block. |
| `mtp-gemma-4-E4B-it.gguf` | `b6a723115efa510d3b3215db1e26790dae84cd08c2134a764f3d194f1f0c3376` | 98653248 | huggingface.co/unsloth/gemma-4-E4B-it-GGUF (download D6a, approved 2026-09-30) | apache-2.0 | Official Gemma 4 E4B MTP drafter (gemma4-assistant) |
| `Qwen3.5-0.8B-Q8_0.gguf` | `0ad885ffd4bb022fc4f0d33a3308fa108ef8613159d3b3a67e23abca056b7a6c` | 811843840 | huggingface.co/unsloth/Qwen3.5-0.8B-GGUF (download D6b, approved 2026-09-30) | apache-2.0 | Small same-tokenizer draft model |

Note: the local Gemma target (`a2232a64…`, 8192951456 B) is an **older revision** than the file
currently in unsloth/gemma-4-E4B-it-GGUF (`f8854aa4…`, 8192953472 B, repo last modified
2026-07-17). The local file remains the protocol-defined target. The Qwen target matches the
current upstream file exactly (`03b74727…`).
