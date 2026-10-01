"""Create the dev / holdout evaluation splits (PROTOCOL §7).

Reads the raw sources in eval/raw/ (see eval/raw/SOURCES.tsv) plus CPython stdlib source files,
samples disjoint dev and holdout sets with a fixed seed, and writes per split:

  prompts.jsonl  chat prompts for speed (S-greedy, S-sampled) and gate Q2
  corpus.jsonl   text segments for gate Q1 (teacher-forced), tokenized/truncated later per model
  long.jsonl     long documents for L-4k/16k/32k and the Q1 long-context segment

This script NEVER prints content: only counts and SHA-256 hashes, so the holdout stays unseen.
Holdout files are set read-only afterwards.
"""
import gzip, hashlib, io, json, os, random, stat, sys, zipfile
from pathlib import Path

SEED = 20260930
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "eval" / "raw"
STDLIB = Path(sys.base_prefix) / "Lib"   # CPython 3.13 stdlib sources (PSF license)
PER_CATEGORY = 3                          # prompts per category per split
rng = random.Random(SEED)


def take_disjoint(pool, n):
    """Shuffle pool deterministically and return (dev, holdout), each with n items."""
    pool = list(pool)
    rng.shuffle(pool)
    assert len(pool) >= 2 * n, f"pool too small: {len(pool)} < {2*n}"
    return pool[:n], pool[n:2 * n]


def gutenberg_body(text):
    s = text.find("*** START OF")
    s = text.find("\n", s) + 1 if s >= 0 else 0
    e = text.find("*** END OF")
    return text[s:e if e > 0 else len(text)].strip()


# ---------------------------------------------------------------- prompts
dolly = [json.loads(l) for l in (RAW / "databricks-dolly-15k.jsonl").read_text(encoding="utf-8").splitlines()]
for i, d in enumerate(dolly):
    d["_idx"] = i


def dolly_pool(cats, need_context=False, min_len=40):
    out = []
    for d in dolly:
        if d["category"] not in cats:
            continue
        if need_context and len(d["context"]) < 400:
            continue
        if len(d["instruction"]) < min_len:
            continue
        out.append(d)
    return out


def dolly_prompt(d, cat):
    text = d["instruction"]
    if d["context"]:
        text += "\n\n" + d["context"]
    return {"category": cat, "source": "databricks-dolly-15k", "source_index": d["_idx"],
            "messages": [{"role": "user", "content": text}]}


splits = {"dev": {"prompts": [], "corpus": [], "long": []},
          "holdout": {"prompts": [], "corpus": [], "long": []}}

cat_sources = [
    ("chat", dolly_pool({"open_qa", "general_qa", "brainstorming"})),
    ("creative", dolly_pool({"creative_writing"})),
    ("summarization", dolly_pool({"summarization", "information_extraction"}, need_context=True, min_len=10)),
]
used_dolly = set()
for cat, pool in cat_sources:
    dev, hold = take_disjoint(pool, PER_CATEGORY)
    splits["dev"]["prompts"] += [dolly_prompt(d, cat) for d in dev]
    splits["holdout"]["prompts"] += [dolly_prompt(d, cat) for d in hold]
    used_dolly |= {d["_idx"] for d in dev + hold}

gsm = [json.loads(l) for l in (RAW / "gsm8k-test.jsonl").read_text(encoding="utf-8").splitlines()]
dev, hold = take_disjoint(list(enumerate(gsm)), PER_CATEGORY)
for name, items in (("dev", dev), ("holdout", hold)):
    splits[name]["prompts"] += [{
        "category": "math", "source": "gsm8k-test", "source_index": i,
        "messages": [{"role": "user", "content": g["question"] + "\n\nSolve this step by step."}]}
        for i, g in items]

he = [json.loads(l) for l in gzip.decompress((RAW / "HumanEval.jsonl.gz").read_bytes()).decode("utf-8").splitlines()]
dev, hold = take_disjoint(list(enumerate(he)), PER_CATEGORY)
for name, items in (("dev", dev), ("holdout", hold)):
    splits[name]["prompts"] += [{
        "category": "code", "source": "HumanEval", "source_index": i,
        "messages": [{"role": "user", "content":
                      "Complete the following Python function. Return the complete implementation "
                      "in a single code block, then briefly explain it.\n\n```python\n" + h["prompt"] + "```"}]}
        for i, h in items]

# ---------------------------------------------------------------- Q1 corpus
with zipfile.ZipFile(RAW / "wikitext-2-raw-v1.zip") as z:
    name = [n for n in z.namelist() if n.endswith("wiki.test.raw")][0]
    wiki = z.read(name).decode("utf-8")
# split into top-level articles (lines of the form " = Title = ")
articles, cur = [], []
for line in wiki.splitlines(keepends=True):
    if line.startswith(" = ") and not line.startswith(" = = ") and cur:
        articles.append("".join(cur)); cur = []
    cur.append(line)
articles.append("".join(cur))
articles = [a.strip() for a in articles if len(a) > 4000]
dev, hold = take_disjoint(articles, 3)
for name, items in (("dev", dev), ("holdout", hold)):
    splits[name]["corpus"] += [{"kind": "prose", "source": "wikitext-2-raw test", "text": a[:6000]} for a in items]

py_files = sorted(p for p in STDLIB.glob("*.py") if 6000 < p.stat().st_size < 200000)
dev, hold = take_disjoint(py_files, 2)
for name, items in (("dev", dev), ("holdout", hold)):
    for p in items:
        txt = p.read_text(encoding="utf-8", errors="replace")
        off = len(txt) // 3                                    # skip license headers / imports
        splits[name]["corpus"].append({"kind": "code", "source": f"CPython stdlib {p.name}",
                                       "source_sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                                       "text": txt[off:off + 6000]})

chat_pool = [d for d in dolly if d["_idx"] not in used_dolly and len(d["response"]) > 300 and not d["context"]]
rng.shuffle(chat_pool)
k = 0
for name in ("dev", "holdout"):
    for _ in range(3):
        msgs, n = [], 0
        while n < 3000:
            d = chat_pool[k]; k += 1
            msgs += [{"role": "user", "content": d["instruction"]},
                     {"role": "assistant", "content": d["response"]}]
            n += len(d["instruction"]) + len(d["response"])
        splits[name]["corpus"].append({"kind": "chat", "source": "databricks-dolly-15k", "messages": msgs})

# ---------------------------------------------------------------- long documents
books = sorted(RAW.glob("pg*.txt"))
dev_books, hold_books = take_disjoint(books, 3)
TASK = ("\n\n---\nSummarize the text above in detail: describe the main characters, "
        "the key events in order, and the overall tone.")
for name, bks in (("dev", dev_books), ("holdout", hold_books)):
    for purpose, target, bk in (("L", 4096, bks[0]), ("L", 16384, bks[1]), ("L", 32768, bks[2]),
                                ("Q1-long", 16384, bks[0])):
        body = gutenberg_body(bk.read_text(encoding="utf-8"))
        need = int(target * 5.5)                              # generous; trimmed by tokens later
        need = min(need, len(body))
        start = rng.randrange(0, max(1, len(body) - need))
        splits[name]["long"].append({"purpose": purpose, "target_tokens": target,
                                     "source": f"Project Gutenberg {bk.name}",
                                     "text": body[start:start + need], "task": TASK if purpose == "L" else ""})

# ---------------------------------------------------------------- write + report (no content!)
for name, parts in splits.items():
    d = ROOT / "eval" / name
    d.mkdir(parents=True, exist_ok=True)
    for part, rows in parts.items():
        for i, r in enumerate(rows):
            r["id"] = f"{name}-{part}-{i:02d}"
        p = d / f"{part}.jsonl"
        if p.exists():
            os.chmod(p, stat.S_IWRITE | stat.S_IREAD)
        data = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows).encode("utf-8")
        p.write_bytes(data)
        cats = {}
        for r in rows:
            key = r.get("category") or r.get("kind") or f'{r.get("purpose")}-{r.get("target_tokens")}'
            cats[key] = cats.get(key, 0) + 1
        print(f"{name:8s} {part:8s} n={len(rows):3d} sha256={hashlib.sha256(data).hexdigest()} {cats}")
        if name == "holdout":
            os.chmod(p, stat.S_IREAD)
