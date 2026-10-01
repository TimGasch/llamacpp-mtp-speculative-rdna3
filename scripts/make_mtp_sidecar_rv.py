"""Iteration 3: MTP-only sidecar with a REDUCED DRAFT VOCABULARY head (FR-Spec style).

Takes the existing sidecar (scripts/make_mtp_sidecar.py) and replaces `output.weight`
[n_embd, n_vocab] with the rows of the K most frequent tokens (byte-identical row copies of the
target's Q6_K head, which quantizes rows independently) plus a `d2t` I64 [K] tensor mapping draft
row -> target token id (same convention as llama.cpp's EAGLE3 drafter).
Only draft proposals are affected; the unchanged target verifies every token.

Token ranking: counts from an independent corpus (WikiText-2 *train*, site-packages Python code;
scripts/tokfreq) + weight * counts of the model's own dev-split generations; all control/EOG tokens
are always included.

Usage: python scripts/make_mtp_sidecar_rv.py <sidecar.gguf> <tokfreq.csv> <dev_generated_ids.txt> <K> <weight> <out.gguf>
"""
import csv, sys
import numpy as np
import gguf

src_p, freq_p, gen_p, K, W, out_p = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), float(sys.argv[5]), sys.argv[6]
rows = list(csv.DictReader(open(freq_p)))
n_vocab = len(rows)
count = np.array([float(r["count"]) for r in rows])
ctrl = np.array([r["is_control"] == "1" for r in rows])
gen = np.array([int(t) for t in open(gen_p).read().split()], dtype=np.int64)
gen_counts = np.bincount(gen, minlength=n_vocab).astype(float)
score = count + W * gen_counts
score[ctrl] = np.inf                                   # always keep control / end-of-generation tokens
order = np.argsort(-score, kind="stable")[:K]
d2t = np.sort(order).astype(np.int64)                  # ascending token ids (row order of the new head)

cov_gen = float(np.isin(gen, d2t).mean())
print(f"K={K} weight={W}: covers {cov_gen*100:.2f}% of dev-generated tokens, "
      f"{count[d2t].sum()/count.sum()*100:.2f}% of corpus tokens; control tokens kept: {int(ctrl.sum())}")

r = gguf.GGUFReader(src_p)
arch = r.fields["general.architecture"].contents()
w = gguf.GGUFWriter(out_p, arch)
for field in r.fields.values():
    if field.name == gguf.Keys.General.ARCHITECTURE or field.name.startswith("GGUF."):
        continue
    vt = field.types[0]
    st = field.types[-1] if vt == gguf.GGUFValueType.ARRAY else None
    val = field.contents()
    if field.name == "general.description":
        val = f"MTP-only sidecar with reduced draft vocabulary K={K} (d2t mapping); head rows copied byte-identically from target"
    w.add_key_value(field.name, val, vt, sub_type=st)

tensors = []
for t in r.tensors:
    if t.name == "output.weight":
        data = np.ascontiguousarray(t.data[d2t])        # [n_vocab, row_bytes] -> [K, row_bytes]
        tensors.append((t.name, data, t.tensor_type))
    else:
        tensors.append((t.name, t.data, t.tensor_type))
tensors.append(("d2t", d2t, gguf.GGMLQuantizationType.I64))
for name, data, tt in tensors:
    w.add_tensor_info(name, data.shape, data.dtype, data.nbytes, tt)
w.write_header_to_file(); w.write_kv_data_to_file(); w.write_ti_data_to_file()
for name, data, tt in tensors:
    w.write_tensor_data(data)
w.close()
for name, data, tt in tensors:
    if name in ("output.weight", "d2t"):
        print(f"{name}: {tt.name} shape(bytes)={data.shape} nbytes={data.nbytes}")
