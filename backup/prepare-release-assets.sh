#!/usr/bin/env bash
# Archive immutable inputs and binaries inside the isolated validation VM only.
set -euo pipefail
[[ "$(hostname)" == macvm-validation && "$(uname -m)" == x86_64 ]] || exit 78
repo=/home/macvm/src/macvm
out=/home/macvm/analysis/repository-backup-20260902/artifacts
mkdir -p "$out"
[[ ! -e "$out/qemu-boot116-linux-x86_64.tar.zst" ]] || exit 78
tar -I 'zstd -T1 -3' -cf "$out/qemu-boot116-linux-x86_64.tar.zst" -C "$repo" \
  build/qemu-boot116-attachments/qemu-system-aarch64 \
  build/qemu-boot116-attachments/config.status \
  build/qemu-boot116-attachments/binary.sha256 \
  build/qemu-boot116-attachments/previous-binary.sha256 \
  build/qemu-boot116-attachments/qemu-source.diff \
  build/qemu-boot116-attachments/reims-source.diff
# Existing dependency versions are recorded; no package install or replacement.
ldd "$repo/build/qemu-boot116-attachments/qemu-system-aarch64" |
  awk '$2 == "=>" && $3 ~ /^\// {print substr($3,2)} $1 ~ /^\// {print substr($1,2)}' > "$out/runtime-files.txt"
find /usr/share/vulkan/icd.d /usr/share/vulkan/explicit_layer.d -maxdepth 1 -type f \
  -printf '%p\n' | sed 's,^/,,' >> "$out/runtime-files.txt"
find /usr/lib/x86_64-linux-gnu -maxdepth 1 -type f \
  \( -name 'libvulkan_lvp.so*' -o -name 'libVkLayer_khronos_validation.so*' \) \
  -printf '%p\n' | sed 's,^/,,' >> "$out/runtime-files.txt"
tar -h -I 'zstd -T1 -3' -cf "$out/linux-runtime-libraries.tar.zst" -C / -T "$out/runtime-files.txt"
tar -I 'zstd -T1 -3' --exclude=.git --exclude=__pycache__ \
  -cf "$out/research-and-helper-tools.tar.zst" -C /home/macvm research tools src/reference src/research src/xnu-12377.121.6
tar -I 'zstd -T1 -3' --exclude='*.ipsw' --exclude='*.pem' --exclude='*.key' --exclude='*.p12' \
  -cf "$out/macos-26.6-restore-materials.tar.zst" -C /home/macvm/macos-restore 26.6
tar -I 'zstd -T1 -3' -cf "$out/boot115-test-and-build-evidence.tar.zst" \
  -C /home/macvm analysis/boot115-crash evidence
cd "$out"
sha256sum ./*.tar.zst > SHA256SUMS
date -u +%FT%TZ > PREPARED
printf 'Archives ready at %s\n' "$out"
