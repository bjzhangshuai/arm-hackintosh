#!/usr/bin/env bash
set -euo pipefail
[[ "$(hostname)" == "macvm-validation" ]] || exit 78
cd /home/macvm/src/macvm
source scripts/lib/require-debug-env.sh
macvm_require_debug_env
build_dir=/home/macvm/src/macvm/build/qemu-boot115-timebase
patch_file=/home/macvm/src/macvm/patches/qemu/0033-vmapple-match-tcg-counter-to-apple-timebase.patch
[[ ! -e "$build_dir" ]] || { echo 'refusing to overwrite an existing build directory' >&2; exit 78; }
git -C third_party/qemu apply --check "$patch_file"
mkdir "$build_dir"
cp -p third_party/qemu/hw/vmapple/vmapple.c "$build_dir/vmapple.before.c"
git -C third_party/qemu diff > "$build_dir/preexisting-qemu.diff"
sha256sum build/qemu-boot105-proto/qemu-system-aarch64 > "$build_dir/previous-binary.sha256"
git -C third_party/qemu apply "$patch_file"
cd "$build_dir"
# Reuse the prior configure arguments, not its output directory or executable.
MESON_WRAP_MODE=nodownload bash ../qemu-boot105-proto/config.status
ninja -j 4 qemu-system-aarch64
sha256sum qemu-system-aarch64
