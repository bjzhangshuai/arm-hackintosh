#!/usr/bin/env bash
# Backup packaging only; execute in the dedicated validation VM, never on a host.
set -euo pipefail
repo=/home/macvm/src/macvm
cd "$repo"
[[ "$(hostname)" == macvm-validation && "$(uname -m)" == x86_64 ]] || exit 78
export MACVM_DEBUG_ENV_CONFIRMED=YES
source scripts/lib/require-debug-env.sh
macvm_require_debug_env
out=/home/macvm/analysis/repository-backup-20260903-boot119
build=build/qemu-boot119-graphics-storage
mkdir -p "$out/environment"
if [[ -f "$out/PREPARED" ]]; then
  (cd "$out" && sha256sum -c SHA256SUMS)
  exit 0
fi
# Immutable executable from the accepted run; never stop or snapshot the live VM.
expected=bfedb312ba18bcaeed2ca67f449575295eb42c2a986308676e7ab17e809ce411
[[ "$(sha256sum "$build/qemu-system-aarch64" | cut -d ' ' -f 1)" == "$expected" ]] || exit 65
tar -czf "$out/qemu-boot119-linux-x86_64.tar.gz.partial" \
  "$build/qemu-system-aarch64" "$build/config.status" \
  "$build/binary.sha256" "$build/previous-binary.sha256" \
  "$build/qemu-source.diff" "$build/reims-source.diff" \
  "$build/metal2vulkan-source.diff" \
  "$build/reims-source-snapshot.tar.gz" "$build/metal2vulkan-source-snapshot.tar.gz"
mv "$out/qemu-boot119-linux-x86_64.tar.gz.partial" "$out/qemu-boot119-linux-x86_64.tar.gz"

cp /etc/os-release "$out/environment/os-release"
uname -a > "$out/environment/uname.txt"
dpkg-query -W -f='${binary:Package}\t${Version}\t${Architecture}\n' > "$out/environment/packages.tsv"
ldd "$build/qemu-system-aarch64" > "$out/environment/qemu-ldd.txt"
# Include the selected software Vulkan implementation, layer, and their library
# dependencies. This is an archive, not permission to replace system libraries.
find /usr/lib/x86_64-linux-gnu -maxdepth 1 -type f \
  \( -name 'libvulkan_lvp.so*' -o -name 'libVkLayer_khronos_validation.so*' \) \
  -print > "$out/environment/vulkan-libraries.txt"
ldd "$build/qemu-system-aarch64" > "$out/environment/runtime-ldd.txt"
while IFS= read -r library; do
  ldd "$library" >> "$out/environment/runtime-ldd.txt"
done < "$out/environment/vulkan-libraries.txt"
awk '$2 == "=>" && $3 ~ /^\// {print substr($3,2)} $1 ~ /^\// {print substr($1,2)}' \
  "$out/environment/runtime-ldd.txt" > "$out/environment/runtime-files.unsorted"
sed 's,^/,,' "$out/environment/vulkan-libraries.txt" >> "$out/environment/runtime-files.unsorted"
find /usr/share/vulkan/icd.d /usr/share/vulkan/explicit_layer.d -maxdepth 1 -type f \
  -printf '%P\n' > "$out/environment/vulkan-manifest-names.txt"
find /usr/share/vulkan/icd.d /usr/share/vulkan/explicit_layer.d -maxdepth 1 -type f \
  -printf '%p\n' | sed 's,^/,,' >> "$out/environment/runtime-files.unsorted"
sort -u "$out/environment/runtime-files.unsorted" > "$out/environment/runtime-files.txt"
tar -h -czf "$out/linux-runtime-boot119.tar.gz.partial" -C / -T "$out/environment/runtime-files.txt"
mv "$out/linux-runtime-boot119.tar.gz.partial" "$out/linux-runtime-boot119.tar.gz"

# Allowlist finite test/build logs. No raw guest memory, authentication transcript,
# OS payload, ticket, mutable disk, or private reverse-engineering capture.
tar -czf "$out/boot119-test-build-evidence.tar.gz.partial" -C /home/macvm \
  analysis/boot116-rootcause/boot119-graphics-final-gate.log \
  analysis/boot116-rootcause/boot119-host-window-final.log \
  analysis/boot116-rootcause/boot119-translator-full.log \
  analysis/boot116-rootcause/boot119-translator-clippy.log \
  analysis/boot116-rootcause/boot119-python-full-gate.log \
  analysis/boot116-rootcause/boot119-feature-matrix-final.log \
  analysis/boot116-rootcause/boot119-build.log
mv "$out/boot119-test-build-evidence.tar.gz.partial" "$out/boot119-test-build-evidence.tar.gz"
tar -czf "$out/boot119-environment.tar.gz.partial" -C "$out" environment
mv "$out/boot119-environment.tar.gz.partial" "$out/boot119-environment.tar.gz"
cd "$out"
sha256sum qemu-boot119-linux-x86_64.tar.gz linux-runtime-boot119.tar.gz \
  boot119-test-build-evidence.tar.gz boot119-environment.tar.gz > SHA256SUMS
sha256sum -c SHA256SUMS
date -u +%FT%TZ > PREPARED
