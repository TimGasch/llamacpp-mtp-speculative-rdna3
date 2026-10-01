"""Build an MTP-only "sidecar" GGUF for Qwen3.5-9B from local files (no download).

The TARGET file is not modified and remains the model used for every token that is emitted.
The sidecar holds only what llama.cpp's MTP drafter needs (`-md <sidecar> --spec-type draft-mtp`):
  - token_embd / output_norm / output  copied byte-identically from the TARGET file
  - blk.<n>.* MTP block (attention + FFN + nextn.*) copied from the unsloth MTP GGUF
  - metadata from the MTP GGUF (block_count = 33, nextn_predict_layers = 1, tokenizer, ...)
llama.cpp detects "MTP-only" files via the absence of blk.0.attn_norm.weight (src/models/qwen35.cpp).
The drafter only proposes tokens; the target verifies every one, so the sidecar affects speed only.

Usage: python scripts/make_mtp_sidecar.py <target.gguf> <mtp_full.gguf> <out_sidecar.gguf>
"""
import sys
import gguf

target_p, mtp_p, out_p = sys.argv[1:4]
tgt = gguf.GGUFReader(target_p)
mtp = gguf.GGUFReader(mtp_p)
arch = mtp.fields["general.architecture"].contents()
n_nextn = mtp.fields[f"{arch}.nextn_predict_layers"].contents()
n_all = mtp.fields[f"{arch}.block_count"].contents()
mtp_blocks = {f"blk.{i}." for i in range(n_all - n_nextn, n_all)}

tgt_t = {t.name: t for t in tgt.tensors}
picked = []
for name in ("token_embd.weight", "output_norm.weight", "output.weight"):
    picked.append(("target", tgt_t[name]))
for t in mtp.tensors:
    if any(t.name.startswith(p) for p in mtp_blocks):
        picked.append(("mtp", t))

w = gguf.GGUFWriter(out_p, arch)
for field in mtp.fields.values():
    if field.name == gguf.Keys.General.ARCHITECTURE or field.name.startswith("GGUF."):
        continue
    vt = field.types[0]
    st = field.types[-1] if vt == gguf.GGUFValueType.ARRAY else None
    w.add_key_value(field.name, field.contents(), vt, sub_type=st)
w.add_key_value("general.description", "MTP-only sidecar: target token_embd/output(+norm) + unsloth MTP block",
                gguf.GGUFValueType.STRING)
for _, t in picked:
    w.add_tensor_info(t.name, t.data.shape, t.data.dtype, t.data.nbytes, t.tensor_type)
w.write_header_to_file()
w.write_kv_data_to_file()
w.write_ti_data_to_file()
for _, t in picked:
    w.write_tensor_data(t.data, tensor_endianess=mtp.endianess)
w.close()
for src, t in picked:
    print(f"{src:6s} {t.name:40s} {t.tensor_type.name:6s} {int(t.n_bytes):>12d}")
print("total bytes:", sum(int(t.n_bytes) for _, t in picked))
