#!/usr/bin/env bash
# Download raw evaluation sources (PROTOCOL §7, approved download D5) into eval/raw/.
# Records URL, size and SHA-256 of every file in eval/raw/SOURCES.tsv.
# This script never prints file contents.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RAW="$ROOT/eval/raw"; mkdir -p "$RAW"
LOG="$RAW/SOURCES.tsv"
printf 'file\turl\tlicense\tbytes\tsha256\tfetched\n' > "$LOG"

fetch() { # name url license
  local name="$1" url="$2" lic="$3"
  curl -sSfL --retry 3 -o "$RAW/$name" "$url"
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$url" "$lic" \
    "$(stat -c %s "$RAW/$name")" "$(sha256sum "$RAW/$name" | cut -d' ' -f1)" "$(date -Iseconds)" >> "$LOG"
}

# Prose: WikiText-2 raw (same mirror llama.cpp's scripts/get-wikitext-2.sh uses)
fetch wikitext-2-raw-v1.zip "https://huggingface.co/datasets/ggml-org/ci/resolve/main/wikitext-2-raw-v1.zip" "CC BY-SA 3.0"
# Instructions / QA / summarization / creative
fetch databricks-dolly-15k.jsonl "https://huggingface.co/datasets/databricks/databricks-dolly-15k/resolve/main/databricks-dolly-15k.jsonl" "CC BY-SA 3.0"
# Math word problems
fetch gsm8k-test.jsonl "https://raw.githubusercontent.com/openai/grade-school-math/master/grade_school_math/data/test.jsonl" "MIT"
# Code prompts
fetch HumanEval.jsonl.gz "https://github.com/openai/human-eval/raw/master/data/HumanEval.jsonl.gz" "MIT"
# Long documents: public-domain books from Project Gutenberg
for id in 1342 2701 1661 98 84 1400; do
  fetch "pg$id.txt" "https://www.gutenberg.org/cache/epub/$id/pg$id.txt" "Public domain (Project Gutenberg)"
  sleep 2   # be polite to gutenberg.org
done

cat "$LOG" | cut -f1,3,4,5
