#!/usr/bin/env bash
# Build a llama.cpp source tree with the portable LLVM-MinGW toolchain + Vulkan SDK.
# Usage: scripts/build_llama.sh <src-dir> <build-dir> [extra cmake args...]
# Every invocation logs the exact configuration to <build-dir>/BUILDINFO.txt.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$(cd "$1" && pwd)"; BUILD="$2"; shift 2

LLVM_MINGW="$ROOT/toolchain/llvm-mingw-20260922-ucrt-x86_64"
export PATH="$LLVM_MINGW/bin:$ROOT/.venv/Scripts:/c/VulkanSDK/1.4.350.0/Bin:$PATH"
export VULKAN_SDK="C:/VulkanSDK/1.4.350.0"

CMAKE_ARGS=(
  -G Ninja
  -DCMAKE_BUILD_TYPE=Release
  -DCMAKE_C_COMPILER=clang
  -DCMAKE_CXX_COMPILER=clang++
  -DBUILD_SHARED_LIBS=ON
  -DGGML_VULKAN=ON
  -DGGML_NATIVE=ON
  -DLLAMA_OPENSSL=OFF
  -DLLAMA_USE_PREBUILT_UI=OFF
  -DLLAMA_BUILD_TESTS=ON
  # MinGW headers default to an older Windows target; vendored cpp-httplib requires Windows 10 APIs.
  # This only sets the target Windows version (same as the official builds, which target Win10).
  "-DCMAKE_C_FLAGS=-D_WIN32_WINNT=0x0A00"
  "-DCMAKE_CXX_FLAGS=-D_WIN32_WINNT=0x0A00"
  "$@"
)

mkdir -p "$BUILD"
{
  echo "date: $(date -Iseconds)"
  echo "src: $SRC"
  echo "commit: $(git -C "$SRC" rev-parse HEAD)"
  echo "describe: $(git -C "$SRC" describe --tags --always --dirty)"
  echo "dirty-diff-sha256: $(git -C "$SRC" diff HEAD | sha256sum | cut -d' ' -f1)"
  echo "compiler: $(clang --version | head -1)"
  echo "cmake: $(cmake --version | head -1)"
  echo "ninja: $(ninja --version)"
  echo "glslc: $(glslc --version 2>&1 | head -1)"
  echo "cmake-args: ${CMAKE_ARGS[*]}"
} > "$BUILD/BUILDINFO.txt"

cmake -S "$SRC" -B "$BUILD" "${CMAKE_ARGS[@]}"
cmake --build "$BUILD" -j "$(nproc)"

# LLVM-MinGW runtime DLLs (libc++, libunwind, libomp, winpthread) must sit next to the binaries.
cp "$LLVM_MINGW"/x86_64-w64-mingw32/bin/{libc++.dll,libunwind.dll,libomp.dll,libwinpthread-1.dll} "$BUILD/bin/"
echo "runtime-dlls: copied from $LLVM_MINGW/x86_64-w64-mingw32/bin" >> "$BUILD/BUILDINFO.txt"
