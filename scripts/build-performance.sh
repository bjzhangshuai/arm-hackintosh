#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
QEMU_ROOT="$REPO_ROOT/third_party/qemu"
BUILD_DIR="${MACVM_QEMU_PGO_BUILD_DIR:-$REPO_ROOT/build/qemu-pgo}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
MESON_BIN="${MESON_BIN:-meson}"
NINJA_BIN="${NINJA_BIN:-ninja}"
NINJA_JOBS="${MACVM_BUILD_JOBS:-2}"
CPU_FLAGS="${MACVM_PERF_CPU_FLAGS:--march=native -mtune=native -fno-semantic-interposition -fno-plt}"
PHASE="${1:-}"

source "$SCRIPT_DIR/lib/require-debug-env.sh"
macvm_require_debug_env

usage() {
  cat >&2 <<'EOF'
usage: scripts/build-performance.sh generate|use

  generate  Configure a fresh O3/LTO/native PGO-instrumented build.
  use       Rebuild the same directory using collected .gcda profiles.

Run a representative, correctness-checked guest workload between the two
phases and stop QEMU cleanly (for example, with QMP quit) so profiles flush.
EOF
  exit 64
}

case "$PHASE" in
  generate|use) ;;
  *) usage ;;
esac

if [[ ! "$NINJA_JOBS" =~ ^[1-4]$ ]]; then
  echo "macvm: MACVM_BUILD_JOBS must be an integer from 1 through 4" >&2
  exit 64
fi

for tool in "$PYTHON_BIN" "$MESON_BIN" "$NINJA_BIN" pkg-config cc; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "macvm: required performance-build tool not found: $tool" >&2
    exit 69
  fi
done

"$SCRIPT_DIR/check-upstreams.sh"
"$SCRIPT_DIR/apply-qemu-patches.sh"

if [[ "$PHASE" == "generate" ]]; then
  if [[ -e "$BUILD_DIR/build.ninja" ]]; then
    echo "macvm: generate requires a fresh build directory: $BUILD_DIR" >&2
    echo "macvm: choose a new MACVM_QEMU_PGO_BUILD_DIR; no directory is deleted automatically" >&2
    exit 73
  fi

  mkdir -p "$BUILD_DIR"
  cd "$BUILD_DIR"
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
    --disable-tools \
    --disable-guest-agent \
    --disable-plugins \
    --enable-fdt=system \
    -Doptimization=3 \
    -Db_lto=true \
    -Db_pgo=generate \
    --extra-cflags="$CPU_FLAGS"
else
  if [[ ! -f "$BUILD_DIR/build.ninja" ]]; then
    echo "macvm: PGO build directory is not configured: $BUILD_DIR" >&2
    exit 66
  fi

  profile_count="$(find "$BUILD_DIR" -type f -name '*.gcda' -print | wc -l)"
  if [[ "$profile_count" -eq 0 ]]; then
    echo "macvm: no PGO profiles found in $BUILD_DIR; run the generated binary and stop it cleanly" >&2
    exit 65
  fi

  cd "$BUILD_DIR"
  "$MESON_BIN" configure -Db_pgo=use .
fi

"$NINJA_BIN" -j "$NINJA_JOBS" qemu-system-aarch64

QEMU_BIN="$BUILD_DIR/qemu-system-aarch64"
if [[ ! -x "$QEMU_BIN" ]]; then
  echo "macvm: performance build completed without producing $QEMU_BIN" >&2
  exit 70
fi

if ! "$QEMU_BIN" -machine help | grep -Eq '^vmapple[[:space:]]'; then
  echo "macvm: performance binary was built, but vmapple is not registered" >&2
  exit 70
fi

if [[ "$PHASE" == "generate" ]]; then
  echo "macvm: instrumented binary ready at $QEMU_BIN"
  echo "macvm: run a representative guest workload, verify correctness, stop QEMU cleanly, then run:"
  echo "macvm: MACVM_QEMU_PGO_BUILD_DIR='$BUILD_DIR' $0 use"
else
  echo "macvm: optimized PGO binary ready at $QEMU_BIN"
fi
