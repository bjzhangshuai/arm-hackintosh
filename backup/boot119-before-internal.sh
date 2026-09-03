#!/usr/bin/env bash
# Private disk/evidence backup in isolated Linux. Never stops a VM itself.
set -euo pipefail
cd /home/macvm/src/macvm
source scripts/lib/require-debug-env.sh
macvm_require_debug_env
[[ $(hostname) == macvm-validation ]] || exit 78
run=/home/macvm/runs/aux-26.6/xnu-imgsrc-reims-boot119-graphics-storage
data=/home/macvm/installation-data
out=$data/boot119-before-internal-20260903
[[ $(findmnt -n -o UUID --mountpoint "$data") == 432e46d4-88c5-4885-bf16-1ecdb0f90ba5 ]] || exit 78
[[ -d "$run" && ! -L "$run" ]] || exit 78
case "${1:-}" in
  live-evidence)
    [[ ! -e "$out" ]] || { echo 'backup directory already exists; inspect, never overwrite' >&2; exit 73; }
    [[ $(readlink /proc/925112/exe) == /home/macvm/src/macvm/build/qemu-boot119-graphics-storage/qemu-system-aarch64 ]] || exit 78
    umask 077
    mkdir "$out"
    mkdir "$out/online-evidence"
    # Open images and sockets are deliberately excluded; these copies are only
    # time-bounded logs, not a claim of consistent disks or a running-RAM snapshot.
    while IFS= read -r -d '' file; do
      relative=${file#"$run/"}
      mkdir -p "$out/online-evidence/$(dirname "$relative")"
      if [[ -r "$file" ]]; then
        cp --preserve=mode,timestamps -- "$file" "$out/online-evidence/$relative"
      else
        # Read an existing root-owned perf capture inside isolation; do not
        # chmod/chown the source. Only the private backup copy gets new ownership.
        sudo -n install -m 600 -o macvm -g macvm -- "$file" "$out/online-evidence/$relative"
      fi
    done < <(find "$run" -type f ! -name '*.img' ! -name '*.qcow2' -print0)
    cp --preserve=mode,timestamps -- \
      "$data/install-analysis/boot119-before-internal-logs.tar.gz" "$out/"
    tar -czf "$out/source-config.tar.gz" scripts tools tests configs docs patches \
      README.md AGENTS.md BLOCKERS.md backup
    sha256sum build/qemu-boot119-graphics-storage/qemu-system-aarch64 > "$out/qemu.sha256"
    runtime=/home/macvm/analysis/repository-backup-20260903-boot119
    (cd "$runtime" && sha256sum -c SHA256SUMS)
    cp -a -- "$runtime" "$out/validated-qemu-runtime"
    date -u +%FT%TZ > "$out/ONLINE_EVIDENCE_COMPLETE"
    ;;
  offline-disks)
    [[ -f "$out/ONLINE_EVIDENCE_COMPLETE" && ! -e "$out/offline" ]] || exit 73
    command -v fuser >/dev/null || exit 69
    # Refuse while any nested ARM QEMU is still open. No kill/stop/quit command.
    if pgrep -f '^/home/macvm/src/macvm/build/qemu-[^ ]*/qemu-system-aarch64( |$)' >/dev/null; then
      echo 'offline disk backup requires the approved completed guest shutdown and QEMU exit' >&2
      exit 78
    fi
    python3 tools/validate_install_target.py --image "$data/macos-26-system.raw"
    for file in "$run/aux.img" "$run/root.img" "$run/usb.img" \
                "$run/recovery-overlay.qcow2" "$data/macos-26-system.raw" \
                "$data/metadata-contract-20260903.raw"; do
      [[ -f "$file" && ! -L "$file" ]] || exit 78
      if fuser "$file" >/dev/null 2>&1; then
        echo "image is still open: $file" >&2; exit 78
      fi
    done
    umask 077
    mkdir "$out/offline"
    # A root-owned perf capture is included with its ownership preserved.
    sudo -n cp -a --sparse=always --reflink=auto -- "$run" "$out/offline/run"
    for name in macos-26-system.raw metadata-contract-20260903.raw; do
      cp --preserve=mode,timestamps --sparse=always --reflink=auto -- "$data/$name" "$out/offline/$name"
      qemu-img compare -f raw -F raw "$data/$name" "$out/offline/$name"
    done
    # Flatten only a NEW backup image. The original overlay and backing remain intact.
    qemu-img convert -f qcow2 -O raw "$run/recovery-overlay.qcow2" "$out/offline/recovery-preserved.raw"
    qemu-img compare -f qcow2 -F raw "$run/recovery-overlay.qcow2" "$out/offline/recovery-preserved.raw"
    for name in aux.img root.img usb.img; do
      cmp -- "$run/$name" "$out/offline/run/$name"
    done
    (cd "$out/offline" && sha256sum run/aux.img run/root.img run/usb.img \
       run/recovery-overlay.qcow2 recovery-preserved.raw > SHA256SUMS && sha256sum -c SHA256SUMS)
    date -u +%FT%TZ > "$out/OFFLINE_DISKS_COMPLETE"
    ;;
  *) echo 'usage: boot119-before-internal.sh live-evidence|offline-disks' >&2; exit 64 ;;
esac
echo "MACVM_BOOT119_BACKUP_STAGE_COMPLETE $1 $out"
