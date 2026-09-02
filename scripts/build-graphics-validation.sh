#!/usr/bin/env bash
set -euo pipefail
[[ "$(hostname)" == "macvm-validation" ]] || exit 78
cd /home/macvm/src/macvm
source scripts/lib/require-debug-env.sh
macvm_require_debug_env
build_dir=/home/macvm/src/macvm/build/qemu-boot116-attachments
[[ ! -e "$build_dir" ]] || { echo 'refusing to overwrite an existing build directory' >&2; exit 78; }
mkdir "$build_dir"
sha256sum build/qemu-boot115-timebase/qemu-system-aarch64 > "$build_dir/previous-binary.sha256"
git -C third_party/qemu diff > "$build_dir/qemu-source.diff"
git -C third_party/reims-vgpu diff > "$build_dir/reims-source.diff"
cd "$build_dir"
MESON_WRAP_MODE=nodownload bash ../qemu-boot115-timebase/config.status
CARGO_BUILD_JOBS=4 ninja -j 4 qemu-system-aarch64
sha256sum qemu-system-aarch64 > binary.sha256
cd /home/macvm/src/macvm
sha256sum -c "$build_dir/previous-binary.sha256"
