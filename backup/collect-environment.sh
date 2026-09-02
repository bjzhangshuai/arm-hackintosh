#!/usr/bin/env bash
# Metadata capture only; never executes a QEMU binary or changes the running VM.
set -euo pipefail
[[ "$(hostname)" == macvm-validation && "$(uname -m)" == x86_64 ]] || exit 78
repo=/home/macvm/src/macvm
out=/home/macvm/analysis/repository-backup-20260902
mkdir -p "$out/environment" "$out/upstream-diffs"
cp /etc/os-release "$out/environment/os-release"
uname -a > "$out/environment/uname.txt"
dpkg-query -W -f='${binary:Package}\t${Version}\t${Architecture}\n' > "$out/environment/packages.tsv"
ldd "$repo/build/qemu-boot116-attachments/qemu-system-aarch64" > "$out/environment/qemu-ldd.txt"
cp "$repo/build/qemu-boot115-timebase/config.status" "$out/environment/boot115-config.status"
sha256sum "$repo/build/qemu-boot116-attachments/qemu-system-aarch64" > "$out/environment/boot116-binary.sha256"
for component in qemu reims-vgpu metal2vulkan libapplegfx-vulkan; do
  git -C "$repo/third_party/$component" rev-parse HEAD > "$out/environment/$component.commit"
  git -C "$repo/third_party/$component" status --short > "$out/environment/$component.status"
  git -C "$repo/third_party/$component" diff --binary HEAD > "$out/upstream-diffs/$component.patch"
done
cp /home/macvm/runs/aux-26.6/xnu-imgsrc-reims-boot116-attachments/qemu.command "$out/environment/boot116-qemu.command"
find /home/macvm/macos-restore/26.6 -xdev -type f -printf '%s\t%p\n' > "$out/environment/apple-assets-sizes.tsv"
find "$repo/build" -xdev -type f -name qemu-system-aarch64 -printf '%s\t%p\n' > "$out/environment/qemu-builds.tsv"
date -u +%FT%TZ > "$out/environment/captured-at.txt"
printf 'Metadata captured under %s\n' "$out"
