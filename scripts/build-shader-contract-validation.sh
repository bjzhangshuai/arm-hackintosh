#!/usr/bin/env bash
set -euo pipefail
[[ "$(hostname)" == "macvm-validation" ]] || exit 78
cd /home/macvm/src/macvm
source scripts/lib/require-debug-env.sh
macvm_require_debug_env
build_dir=/home/macvm/src/macvm/build/qemu-boot117-shader-contract
[[ ! -e "$build_dir" ]] || { echo 'refusing to overwrite existing build' >&2; exit 78; }
mkdir "$build_dir"
sha256sum build/qemu-boot116-attachments/qemu-system-aarch64 > "$build_dir/previous-binary.sha256"
git -C third_party/qemu diff > "$build_dir/qemu-source.diff"
git -C third_party/reims-vgpu diff > "$build_dir/reims-source.diff"
git -C third_party/metal2vulkan diff > "$build_dir/metal2vulkan-source.diff"
cp third_party/reims-vgpu/crates/reims-vgpu/src/backend/vulkan/engine/shader_contract.rs "$build_dir/shader_contract.rs"
cd "$build_dir"
MESON_WRAP_MODE=nodownload bash ../qemu-boot116-attachments/config.status
CARGO_BUILD_JOBS=2 ninja -j 2 qemu-system-aarch64
sha256sum qemu-system-aarch64 > binary.sha256
cd /home/macvm/src/macvm
sha256sum -c "$build_dir/previous-binary.sha256"
