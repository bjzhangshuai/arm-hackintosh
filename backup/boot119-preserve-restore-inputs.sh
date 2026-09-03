#!/usr/bin/env bash
# Private copies of the immutable inputs for the already-validated boot chain.
# Never publish these Apple assets/tickets to Git or public releases.
set -euo pipefail
cd /home/macvm/src/macvm
source scripts/lib/require-debug-env.sh
macvm_require_debug_env
[[ $(hostname) == macvm-validation ]] || exit 78
base=/home/macvm/macos-restore/26.6
backup=/home/macvm/installation-data/boot119-before-internal-20260903
out=$backup/restore-inputs
[[ -f "$backup/OFFLINE_DISKS_COMPLETE" && ! -e "$out" ]] || exit 78
[[ $(findmnt -n -o UUID --mountpoint /home/macvm/installation-data) == 432e46d4-88c5-4885-bf16-1ecdb0f90ba5 ]] || exit 78
files=(
  AVPBooter.vmapple2.bin
  restore-chain/iBSS.fixed-rnd-713471fb.img4
  local-policy-fixed-rnd-713471fb-bnch32/Ap.LocalPolicy.fixed-rnd-713471fb-bnch32.img4
  restore-chain/iBEC.fixed-rnd-713471fb.img4
  restore-chain/iBEC.runtime-last.bin
  restore-chain/iBEC.descriptor-table.bin
  restore-chain/RestoreTrustCache.094-96989-085.localpolicy-ticket.img4
  restore-chain/RestoreRamDisk.094-96989-085.localpolicy-ticket.img4
  restore-chain/RestoreDeviceTree.vma2macosap.localpolicy-ticket.img4
  restore-chain/RestoreKernelCache.release.vma2.localpolicy-ticket.img4
  customer-base/RestoreRamDisk-with-BaseSystem.raw
  customer-base/022-22048-085.dmg.aea.root_hash
  customer-base/022-22048-085.dmg.aea.trustcache
  restore-bundle-erase/094-96989-085.dmg.trustcache
)
for file in "${files[@]}"; do [[ -f "$base/$file" && ! -L "$base/$file" ]] || exit 78; done
umask 077
mkdir "$out"
for file in "${files[@]}"; do
  mkdir -p "$out/$(dirname "$file")"
  cp --preserve=mode,timestamps --sparse=always --reflink=auto -- "$base/$file" "$out/$file"
  cmp -- "$base/$file" "$out/$file"
done
(cd "$out" && sha256sum "${files[@]}" > SHA256SUMS && sha256sum -c SHA256SUMS)
date -u +%FT%TZ > "$backup/RESTORE_INPUTS_COMPLETE"
echo MACVM_BOOT119_RESTORE_INPUTS_BACKED_UP
