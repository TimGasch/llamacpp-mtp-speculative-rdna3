"""Compare two GGUF files tensor-by-tensor (name, type, shape, SHA-256 of the raw data).

Used to decide whether a variant file (e.g. one that adds MTP heads) carries byte-identical main
weights, i.e. can be derived losslessly from the target file (PROTOCOL §2).
Usage: python scripts/gguf_tensor_diff.py A.gguf B.gguf out.json
"""
import hashlib, json, sys
from gguf import GGUFReader


def inv(path):
    r = GGUFReader(path)
    return {t.name: (t.tensor_type.name, [int(x) for x in t.shape], hashlib.sha256(t.data.tobytes()).hexdigest())
            for t in r.tensors}


a, b = inv(sys.argv[1]), inv(sys.argv[2])
common = sorted(set(a) & set(b))
same = [n for n in common if a[n] == b[n]]
diff = [{"name": n, "a": a[n], "b": b[n]} for n in common if a[n] != b[n]]
res = {"a": sys.argv[1], "b": sys.argv[2], "n_a": len(a), "n_b": len(b), "n_common": len(common),
       "n_identical": len(same), "different": diff, "only_a": sorted(set(a) - set(b)), "only_b": sorted(set(b) - set(a))}
json.dump(res, open(sys.argv[3], "w"), indent=1)
print(f"common={len(common)} identical={len(same)} different={len(diff)} only_a={len(res['only_a'])} only_b={len(res['only_b'])}")
print("only_b sample:", res["only_b"][:12])
print("different sample:", [(d['name'], d['a'][0], d['b'][0]) for d in diff[:8]])
