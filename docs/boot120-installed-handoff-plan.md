# Boot120 installed-system handoff — preparation, not an executed launcher

## Current state

Boot120's earlier local 25G83 attempt completed extraction/integrity checks,
then UpdateBrain crashed in a NULL cleanup call (B012/B013). The identity fix is
tested and its bounded one-shot guard is armed. The current B015 attempt passed
staging coverage, native service startup, license confirmation and target
selection, and is extracting the preserved local archive. It has **not**
completed installation or produced a verified bootable system. This document does not
authorize interrupting it. The approved Boot119 shutdown/restart is already done.
Keep outer Linux and its NBD attachment running. Only inner test resources below
are in scope; production guests, QEMU packages and passthrough remain untouched.

## Source-established storage contract

The actual build's `build.ninja` identifies `third_party/qemu` as its source.
Do not substitute the older, unmodified vendored QEMU source when checking this.

- `hw/vmapple/vmapple.c:create_bdif` binds pflash index 0 to AUX, index 1 to
  firmware root, and index 2 to USB. It falls back to IF_VIRTIO only when index 1
  is absent. Boot120's root.img is a 64 MiB scratch file, not the installation disk.
- XNU currently sees the correct 128 GiB installation image through a separate
  `vmapple-virtio-blk-pci,variant=root`. Changing only this frontend does not
  change firmware's root backend.
- `hw/vmapple/bdif.c` implements actual block writes when its explicit
  `block-writes` opt-in is enabled. Its backend permissions allow shared writers.
  Boot120 already uses this contract for AUX/iSC coherence. Raw backends sharing
  a file require deliberate locking/share settings; do not copy an untested
  double-open command line or silently disable locking for unrelated files.
- The exact local/isolated-Linux source files now match by SHA-256. In
  `hw/core/qdev-properties-system.c:set_drive_helper`, passing a block **node**
  name creates a separate frontend BlockBackend over the existing node; passing
  an already-attached backend ID fails. `hw/block/block.c:blkconf_apply_backend_options`
  permits a second writer only when `share-rw=on`. This suggests a single raw
  node shared by firmware and OS frontends can avoid double-opening the file.
  It is a source-established candidate, **not a validated continuation command**;
  the final graph must be tested with disposable fixtures before using installed
  data. No additional QEMU process or disk-graph mutation was performed here.
- Do not try to instantiate BDIF with `-device` under an unrelated machine for
  that fixture: `hw/core/sysbus.c` defaults SysBus devices to
  `user_creatable=false`, and BDIF does not override it. The future test must
  model the real board initialization or explicitly limit its claim to block
  sharing semantics; a generic-device test is not a vmapple boot test.
- `docs/system/arm/vmapple.rst` also presents the system disk through both
  firmware pflash and OS virtio. That document's old macOS-12/HVF example is
  storage-contract evidence, **not** proof that 26.6.2/TCG cold boot works.

## Boundary gates before any next boot

1. Wait for the installer itself to request reboot/shutdown. Record QMP state,
   native watcher state, serial shutdown/unmount evidence and latest installer
   logs. Do not send `cont` to a halted guest. A pause or I/O error without clean
   shutdown is not permission to terminate, copy live files as consistent, or boot.
2. Export available volatile install/restore logs before that boundary. Record
   the final APFS topology, system/data volume-group UUIDs, Preboot/Recovery
   volumes and installer/bless output. Inspect actual results, not guessed paths
   or old disk numbers. Do not manufacture boot files, signature tickets or roles.
3. On confirmed clean shutdown, close only this inner QEMU cleanly, then preserve
   its complete current AUX/iSC, Recovery overlay plus backing chain, target disk,
   scratch files, launch configuration and runtime evidence. Backups are private
   and new-path/non-overwriting. Verify consistency and capacity before copying.
4. Generate a separate continuation directory and explicit launch configuration.
   Preserve VM UUID/ECID, firmware, current AUX state and target image identity.
   Firmware root and OS root must address the same installed system disk. Never
   rerun `validation-boot120.sh` against an existing run: it provisions scratch
   and copies earlier state. Never substitute the old pre-installation AUX.
5. Verify that the installer actually produced the necessary signed boot assets,
   policy/NVRAM state and system volume. If not, diagnose the corresponding stage
   before attempting a new boot. Recovery's runtime debugger inputs are not an
   installed-system resume procedure and must not be copied blindly.
6. Test command construction/identity/overwrite refusal in isolated Linux first.
   A passing test is not a live boot result. Permit one evidence-backed next boot
   only after all prerequisites are established; retain reboot-boundary protection.

## Completion criteria

Installation progress or package download alone is not success. Require a real
installed-system boot, Setup Assistant, the requested local account (credentials
entered interactively, never committed), a working login/desktop and independent
ARM64 / macOS build / system-disk identity evidence. No near-native-performance
or NVIDIA-hardware claim follows from this installation test.
