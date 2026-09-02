#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ "${MACVM_TEST_VM_CONFIRMED:-}" != "YES" ]]; then
  echo "refusing to run: set MACVM_TEST_VM_CONFIRMED=YES only inside a disposable test VM" >&2
  exit 64
fi
if [[ "$(uname -s)" != Linux || "$(uname -m)" != x86_64 ]]; then
  echo "this launcher requires a disposable Linux x86_64 test VM" >&2
  exit 69
fi

vcpus="${MACVM_VCPUS:-2}"
memory_mib="${MACVM_MEMORY_MIB:-8192}"
ssh_port="${MACVM_SSH_FORWARD_PORT:-32222}"
if [[ ! "$vcpus" =~ ^[1-4]$ ]]; then
  echo "MACVM_VCPUS must be an integer from 1 through 4" >&2
  exit 64
fi
if [[ ! "$memory_mib" =~ ^[0-9]+$ ]] || (( memory_mib < 2048 || memory_mib > 16384 )); then
  echo "MACVM_MEMORY_MIB must be between 2048 and 16384" >&2
  exit 64
fi
if [[ ! "$ssh_port" =~ ^[0-9]+$ ]] || (( ssh_port < 1024 || ssh_port > 65535 )); then
  echo "MACVM_SSH_FORWARD_PORT must be between 1024 and 65535" >&2
  exit 64
fi

qemu="${MACVM_QEMU_BIN:-$BUNDLE_ROOT/bin/qemu-system-aarch64}"
avpbooter="${MACVM_AVPBOOTER:-$BUNDLE_ROOT/assets/apple/ready/AVPBooter.vmapple2.bin}"
aux="${MACVM_AUX:-$BUNDLE_ROOT/assets/apple/ready/aux.img.trimmed}"
disk="${MACVM_DISK:-$BUNDLE_ROOT/assets/apple/ready/disk.img}"
ecid_file="${MACVM_ECID_FILE:-$BUNDLE_ROOT/assets/apple/ready/ecid.txt}"

python3 "$SCRIPT_DIR/preflight-assets.py"
if [[ ! -x "$qemu" ]]; then
  echo "missing executable QEMU binary: $qemu" >&2
  exit 69
fi
ecid="$(tr -d '[:space:]' < "$ecid_file")"

exec "$qemu" \
  -machine "vmapple,uuid=$ecid" \
  -accel tcg,thread=multi \
  -cpu max \
  -smp "$vcpus" \
  -m "${memory_mib}M" \
  -bios "$avpbooter" \
  -drive "file=$aux,if=pflash,format=raw" \
  -drive "file=$disk,if=pflash,format=raw" \
  -drive "file=$aux,if=none,id=aux,format=raw" \
  -drive "file=$disk,if=none,id=root,format=raw" \
  -device vmapple-virtio-blk-pci,variant=aux,drive=aux \
  -device vmapple-virtio-blk-pci,variant=root,drive=root \
  -netdev "user,id=net0,ipv6=off,hostfwd=tcp:127.0.0.1:${ssh_port}-:22" \
  -device virtio-net-pci,netdev=net0 \
  -display none \
  -serial mon:stdio

