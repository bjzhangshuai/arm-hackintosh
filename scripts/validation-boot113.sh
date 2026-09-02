#!/usr/bin/env bash
set -euo pipefail
[[ "$(hostname)" == "macvm-validation" ]] || exit 78
cd /home/macvm/src/macvm
exec env \
  MACVM_DEBUG_ENV_CONFIRMED=YES \
  MACVM_QEMU_BIN=/home/macvm/src/macvm/build/qemu-boot105-proto/qemu-system-aarch64 \
  MACVM_RUN_NAME=xnu-imgsrc-reims-boot113-aux-ean \
  MACVM_QEMU_DISPLAY=vnc=127.0.0.1:113 \
  MACVM_QEMU_TIMEOUT=5400s \
  MACVM_SMOKE_VCPUS=8 MACVM_SMOKE_MEMORY_GIB=16 MACVM_GDB_PORT=12351 \
  MACVM_VMAPPLE_CFG_MODEL=VirtualMac2,1 \
  MACVM_GDB_POST_TRACE_SCRIPT=/home/macvm/src/macvm/tools/inject_basesystem_auth_and_boot_args_trace_mount.gdb \
  MACVM_SESSION_STEPS_FILE=/home/macvm/src/macvm/configs/macos-26.6-restore.steps \
  MACVM_STAGE2_PROMPT_TIMEOUT_SECONDS=120 MACVM_SESSION_CONNECT_TIMEOUT=120 MACVM_SESSION_RECV_TIMEOUT=180 \
  MACVM_GDB_TIMEOUT=300s MACVM_POST_GDB_TIMEOUT=900s MACVM_POST_GDB_MILESTONE_TIMEOUT_SECONDS=900 \
  MACVM_KEEP_QEMU_RUNNING_AFTER_HELPER=YES MACVM_SMOKE_TRACE_VERBOSE=NO \
  MACVM_BASESYSTEM_AUTH_BLOB=/home/macvm/macos-restore/26.6/customer-base/022-22048-085.dmg.aea.root_hash \
  MACVM_RAMDISK_OVERRIDE_IMAGE=/home/macvm/macos-restore/26.6/customer-base/RestoreRamDisk-with-BaseSystem.raw \
  MACVM_RAMDISK_OVERRIDE_ADDRESS=0x3c0000000 \
  MACVM_RESTORE_TRUSTCACHE_IMAGE=/home/macvm/macos-restore/26.6/restore-bundle-erase/094-96989-085.dmg.trustcache \
  MACVM_TRUSTCACHE_OVERRIDE_ADDRESS=0x7433c000 \
  MACVM_BASESYSTEM_TRUSTCACHE_IMAGE=/home/macvm/macos-restore/26.6/customer-base/022-22048-085.dmg.aea.trustcache \
  MACVM_EXPOSE_RECOVERY_VIRTIO=YES \
  MACVM_RECOVERY_IMAGE=/home/macvm/macos-restore/26.6/validation-recovery-v1.img \
  MACVM_RECOVERY_VOLUME_UUID=0C6B79EF-6E03-58C2-BEF6-6ADAAA25668E \
  MACVM_EXPOSE_ISC_VIRTIO=YES MACVM_EXPOSE_UTIL_VIRTIO=YES \
  MACVM_ISC_IMAGE=/home/macvm/macos-restore/26.6/validation-isc-xart-v2.img \
  MACVM_ALLOW_BASESYSTEM_RW_ROOT=YES \
  MACVM_ALLOW_PACKAGESLINK_SYMLINK=YES \
  MACVM_ALLOW_PACKAGESLINK_ROFS_BYPASS=YES \
  MACVM_ALLOW_PACKAGESLINK_APFS_ROFS_BYPASS=YES \
  MACVM_DETACH_AFTER_PACKAGESLINK=YES MACVM_DETACH_AFTER_PACKAGESLINK_RESULT=YES \
  REIMS_VGPU_FORCE_APPLE_DEVICE_INFO=1 REIMS_VGPU_DRAW_LOG=1 \
  bash scripts/run-ibec-usb-restore-smoke.sh
