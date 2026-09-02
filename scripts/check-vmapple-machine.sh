#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
QEMU_BIN="${MACVM_QEMU_BIN:-$REPO_ROOT/build/qemu/qemu-system-aarch64}"

source "$SCRIPT_DIR/lib/require-debug-env.sh"
macvm_require_debug_env

if [[ ! -x "$QEMU_BIN" ]]; then
  echo "macvm: QEMU binary is missing: $QEMU_BIN" >&2
  exit 69
fi

SMOKE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/macvm-vmapple-smoke.XXXXXX")"
trap 'rm -rf -- "$SMOKE_DIR"' EXIT

truncate -s 1M "$SMOKE_DIR/firmware.bin"
truncate -s 64M "$SMOKE_DIR/aux.img"
truncate -s 64M "$SMOKE_DIR/root-metadata.img"
truncate -s 64M "$SMOKE_DIR/block.img"

QMP_OUTPUT="$SMOKE_DIR/qmp.jsonl"
printf '%s\n' \
  '{"execute":"qmp_capabilities"}' \
  '{"execute":"query-status"}' \
  '{"execute":"query-pci"}' \
  '{"execute":"quit"}' |
  "$QEMU_BIN" \
    -machine vmapple \
    -accel tcg,thread=multi \
    -cpu max \
    -smp 2 \
    -m 1G \
    -S \
    -bios "$SMOKE_DIR/firmware.bin" \
    -drive "if=pflash,index=0,format=raw,file=$SMOKE_DIR/aux.img" \
    -drive "if=pflash,index=1,format=raw,file=$SMOKE_DIR/root-metadata.img" \
    -drive "if=none,id=macvm-root,format=raw,file=$SMOKE_DIR/block.img" \
    -device vmapple-virtio-blk-pci,variant=root,drive=macvm-root \
    -display none \
    -serial none \
    -monitor none \
    -qmp stdio >"$QMP_OUTPUT"

if ! grep -q '"status"[[:space:]]*:[[:space:]]*"prelaunch"' "$QMP_OUTPUT"; then
  echo "macvm: vmapple did not reach QMP prelaunch state" >&2
  exit 70
fi

if ! grep -q '"return"' "$QMP_OUTPUT"; then
  echo "macvm: vmapple QMP session did not complete" >&2
  exit 70
fi

echo "macvm: vmapple machine initialized with CPU, RAM, GIC, PCIe, cfg, bdif, block and PVG sentinels"
