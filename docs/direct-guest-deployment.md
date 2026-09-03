# Direct ARM guest / RTX 4060 Ti — approved direction, activation held

## User decision, 2026-09-04 (Asia/Shanghai)

The user selected these future deployment components:

- Physical x86_64 Ubuntu runs the experimental `qemu-system-aarch64` directly.
- ARM64 macOS 26 still executes through TCG; this does not enable ARM KVM on x86.
- RTX 4060 Ti remains owned by Linux and serves the PVG/Metal-to-Vulkan backend.
- The production x86 macOS QEMU, dependencies and configuration must be backed up
  before any deployment change. The experimental executable will use a separate
  prefix, never replace the production executable or global library configuration.

The user then clarified that the RTX 4060 Ti **has not been installed** and asked
to **back up the previous QEMU first**. This is the active scope. Do not install
drivers, release the installer hold, migrate disks, change the debug-environment
guard, stop/restart any VM or reboot the physical host. Wait for the user's
hardware-ready notification and coordinate any shutdown separately.

The read-only physical-host inventory found Ubuntu 26.04, Linux 7.0.0-27-generic,
ASPEED graphics and RX580 bound to `vfio-pci`; no NVIDIA display device was found.
This is an inventory, not a GPU/performance test. Do not appropriate the RX580.

## Backup design

`tools/backup_production_qemu.sh` is an explicitly gated, backup-only exception to
the normal isolated-execution policy. It verifies the exact physical hostname,
requires a separate backup-only environment marker, and writes only to a new
private directory under `apple-m-macos-vm/production-qemu-backups`.

It records installed QEMU executables, optional QEMU modules, their ELF runtime
dependencies, complete files from the discovered packages, production startup
scripts and manager source/runtime, configuration, EFI/ROM files, closed
OpenCore/OVMF state, current boot/kernel files and package metadata. QEMU process
maps and configuration stay private and are not uploaded to GitHub.

Verification consists of source hashes before and after archiving, byte-level
archive comparison against the source files, and an archive SHA-256. This is not
a VM restore test. The main production macOS disk, installers and large logs are
deliberately excluded; no live OS disk is copied and no production process is
stopped. Archive creation uses low CPU/I/O priority and one compression thread.

## Restore boundary

Never blindly extract the archive over `/`. Stage it in a new directory, verify
the manifests, and restore only approved target files in a coordinated window.
In particular, the copied dpkg database is reference evidence, not an instruction
to overwrite the host's current package database. Exact installed bytes preserve
local QEMU modifications even when the same version's repository package does not.

This backup is on the same physical host, not an off-machine disaster-recovery
copy. It does not establish that the ARM installation succeeds or that NVIDIA
hardware rendering works. B016 storage topology activation remains pending.

## Verified backup, 2026-09-04

Authoritative private backup directory on the physical Ubuntu host:

```text
/home/jansurezhang/apple-m-macos-vm/production-qemu-backups/production-qemu-20260903T165748Z-FQ6Wo3
```

- Archive: `production-qemu.tar.zst`, 274,230,949 bytes (about 262 MiB).
- Archive SHA-256:
  `aa2b4ada11d23c5a08d5819ab7557753b89cfdc2c2ae7b38209ea2debc659cc8`.
- 176 discovered QEMU/dependency/firmware package names; 6,430 regular files.
- Source hashes match before/after archiving; `tar --compare` reports no
  differences; a separate final `sha256sum -c archive.sha256` returns `OK`.
- The fixed `fuser` ownership checks for OpenCore and OVMF boot state report no
  users and no diagnostic errors. No production VM was stopped for this backup.
- Verified presence of the actual QEMU binary, original startup and HugePages
  scripts, production VM JSON, VFIO configuration, GRUB and HugePages service.
- Existing `/usr/bin/qemu-system-x86_64` remains SHA-256
  `e8143c590e74194763cd03ae334d194e1a9148bdd07cabb44913fd85b99a7704`.
- The backup parent/directory are private (0700) and owned by `jansurezhang`;
  the archive is 0600. Root collected the files; final verification was also
  performed through the ordinary user account.

The directory contains `VERIFIED.txt`, package lists, exact source manifests,
archive checksum, loaded-library evidence and selected host-state records.
Sensitive originals are only in this private host backup, not in Git. No NVIDIA
driver installation, package upgrade, QEMU replacement, system tuning, device
reassignment, VM restart or ARM installation activation was performed.

The earlier smaller archive was retained; the directory above is the final
backup including complete discovered package contents. Shell syntax was checked
inside the isolated Linux VM. No tests/builds ran on the production Mac, and the
physical-host work was inventory, backup and integrity verification only.
