set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SRC="$(cd "$1" && pwd)"; BLD="$(cd "$2" && pwd)"
export PATH="$ROOT/toolchain/llvm-mingw-20260922-ucrt-x86_64/bin:$PATH"
clang++ -std=c++17 -O2 -D_WIN32_WINNT=0x0A00 \
  -I"$SRC/include" -I"$SRC/common" -I"$SRC/ggml/include" -I"$SRC/vendor" \
  "$ROOT/bench/qdump/qdump.cpp" -o "$BLD/bin/qdump.exe" \
  "$BLD/common/libllama-common.dll.a" "$BLD/src/libllama.dll.a" \
  "$BLD/ggml/src/libggml.dll.a" "$BLD/ggml/src/libggml-base.dll.a"
echo "built $BLD/bin/qdump.exe"
