#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
QEMU_ROOT="$REPO_ROOT/third_party/qemu"
BUILD_DIR="${MACVM_QEMU_BUILD_DIR:-$REPO_ROOT/build/qemu}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
NINJA_BIN="${NINJA_BIN:-ninja}"
NINJA_JOBS="${MACVM_BUILD_JOBS:-2}"

source "$SCRIPT_DIR/lib/require-debug-env.sh"
macvm_require_debug_env

"$SCRIPT_DIR/check-upstreams.sh"
"$SCRIPT_DIR/apply-qemu-patches.sh"

for tool in "$PYTHON_BIN" "$NINJA_BIN" pkg-config cc cargo; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "macvm: required build tool not found: $tool" >&2
    exit 69
  fi
done

if [[ ! "$NINJA_JOBS" =~ ^[1-4]$ ]]; then
  echo "macvm: MACVM_BUILD_JOBS must be an integer from 1 through 4" >&2
  exit 64
fi

mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

if [[ ! -f build.ninja ]]; then
  MESON_WRAP_MODE=nodownload "$QEMU_ROOT/configure" \
    --target-list=aarch64-softmmu \
    --python="$PYTHON_BIN" \
    --ninja="$NINJA_BIN" \
    --enable-tcg \
    --disable-hvf \
    --disable-pvg \
    --disable-werror \
    --disable-docs \
    --disable-gtk \
    --disable-sdl \
    --disable-opengl \
    --disable-virglrenderer \
    --enable-fdt=system
fi

"$NINJA_BIN" -j "$NINJA_JOBS" qemu-system-aarch64

QEMU_BIN="$BUILD_DIR/qemu-system-aarch64"
if [[ ! -x "$QEMU_BIN" ]]; then
  echo "macvm: build completed without producing $QEMU_BIN" >&2
  exit 70
fi

if ! "$QEMU_BIN" -machine help | grep -Eq '^vmapple[[:space:]]'; then
  echo "macvm: qemu-system-aarch64 was built, but vmapple is not registered" >&2
  exit 70
fi

echo "macvm: built $QEMU_BIN"
