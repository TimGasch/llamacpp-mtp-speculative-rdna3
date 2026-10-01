"""Inventory of a GGUF file: metadata (without huge arrays) + per-tensor byte sizes.

Also classifies tensors into 'streamed per generated token' vs 'lookup only' to estimate the
bytes that batch-1 decode must read from VRAM per token (the roofline input, PROTOCOL §9.1).

Usage: python scripts/gguf_inventory.py <model.gguf> <out.json>
Requires PYTHONPATH to include src/llama.cpp-ref/gguf-py.
"""
import json, sys
from collections import defaultdict
from gguf import GGUFReader

path, out = sys.argv[1], sys.argv[2]
r = GGUFReader(path)

meta = {}
for k, f in r.fields.items():
    if k.startswith("GGUF.") or k.startswith("tokenizer.ggml.") and k not in ("tokenizer.ggml.model", "tokenizer.ggml.pre"):
        continue
    try:
        v = f.contents()
    except Exception as e:                      # pragma: no cover - defensive
        v = f"<unreadable: {e}>"
    if isinstance(v, list) and len(v) > 64:
        v = f"<array len={len(v)}>"
    if isinstance(v, str) and len(v) > 400:
        v = v[:400] + f"... <truncated, len={len(v)}>"
    meta[k] = v

names = {t.name for t in r.tensors}
tied_output = "output.weight" not in names
tensors = []
by_class = defaultdict(int)
by_type = defaultdict(int)
for t in r.tensors:
    n = t.name
    # lookup-only tensors: only one row per token is read (embedding tables)
    if n == "token_embd.weight" and not tied_output:
        cls = "lookup"
    elif n == "token_embd.weight" and tied_output:
        cls = "streamed(output head, tied)"
    elif "per_layer_token_embd" in n:
        cls = "lookup"
    elif ".nextn." in n or n.startswith("mtp."):
        cls = "mtp(unused by plain decode)"
    else:
        cls = "streamed"
    nb = int(t.n_bytes)
    tensors.append({"name": n, "type": t.tensor_type.name, "shape": [int(x) for x in t.shape], "bytes": nb, "class": cls})
    by_class[cls] += nb
    by_type[t.tensor_type.name] += nb

streamed = sum(v for k, v in by_class.items() if k.startswith("streamed"))
res = {
    "file": path,
    "n_tensors": len(tensors),
    "total_tensor_bytes": sum(t["bytes"] for t in tensors),
    "tied_output": tied_output,
    "bytes_by_class": dict(by_class),
    "bytes_by_type": dict(by_type),
    "streamed_bytes_per_token_estimate": streamed,
    "note": "streamed = weights every decode step multiplies with; excludes KV cache and activations",
    "metadata": meta,
    "tensors": tensors,
}
with open(out, "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, default=str)
print(json.dumps({k: res[k] for k in ("file", "n_tensors", "total_tensor_bytes", "tied_output",
                                      "bytes_by_class", "streamed_bytes_per_token_estimate")}, indent=1))
for k in ("general.architecture", "general.name", "general.license", "general.license.link",
          "general.base_model.0.repo_url", "general.quantized_by", "general.file_type"):
    if k in meta:
        print(f"{k}: {meta[k]}")
arch = meta.get("general.architecture")
for k, v in meta.items():
    if arch and k.startswith(arch + ".") and not isinstance(v, str) or (arch and k.startswith(arch + ".") and len(str(v)) < 80):
        print(f"{k}: {v}")
