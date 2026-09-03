# B016 — primary-disk discovery repair, activation held

The user requested completion of the current diagnosis/repair work but **no next
installer launch or VM restart**, pending RTX 4060 Ti installation. Current inner
VM remains running; neither physical-host shutdown nor production VM changes are
authorized here. No automation has been created.

## Established evidence

B015 completed local 25G83 archive extraction and integrity checking, retrieved
zero packages, then failed during SFR preflight personalization. The B012 cleanup
adapter did run once and detached normally. New PID 11622 subsequently aborted
with `NSInvalidArgumentException: nil file argument`, not another CFRelease trap.

Private evidence stays outside Git:

- `boot120-b015-crash-20260903-1540.tar.gz`, 392425 bytes, SHA256
  `aa00eeb687558455f46b4f4ecd98eb71dcd8b36c6f05cd6043c5d483979213a7`.
- Exact 25G83 UpdateBrain ARM64e SHA256
  `0d680541b7c6f2e6911cdf2a83e4144892cf3c0ad10325b041c3b6b7a254475b`.
- Boot120 serial markers `MACVM_B016_SFR_STATE_BEGIN/END` at guest 16:02 UTC,
  plus the later explicit IORegistry query of `EmbeddedDeviceTypeRoot`.

The actual chain in the matching binaries is:

1. `-[LPMedia isPrimaryMedia]` (unslid 0x19f0dedfc) delegates to
   `isEmbeddedDeviceTypeRoot`.
2. `+[LPPartitionMedia primaryMedia]` (0x19f0e0178) returns the first matching
   media. It does not merge physical disks.
3. `+[LPAPFSContainer _containerWithPhysticalStoreRole:]` (0x19f0d514c), and
   its LPStatic equivalent (0x1a22ce574), search **children of that one media**.
   `diagsContainer` requests role 1. Recovery uses role 2.
4. UpdateBrain `+[MSUSFRTargetController iSCPrebootVolume]` (file 0x37d48)
   asks diagsContainer for its Preboot volume.
5. `currentSFRManifestHash` (0x383b4) appends the ticket filename to currentPath
   without a nil guard. `_NSIHDataForTicketPath:error:` (0x39064) then calls NSData
   with nil and throws. The downstream native version-comparison logic already
   treats a missing hash as unequal, so no fabricated hash/check override is needed.

Live topology confirms disk0/system, disk1/Recovery and disk2/iSC ALL have
`EmbeddedDeviceTypeRoot=Yes`. Disk3s2/iSCPreboot is genuinely mounted read/write
at `/System/Volumes/iSCPreboot`, UUID 9EF8EE17-1937-5C3F-A31E-42B2EAB53D21.
SFR/current is absent, but creating an empty directory would not fix the volume
discovery failure: the helper already composes a path without checking directory
existence when create=NO. Selecting/reordering a different primary merely makes
another required sibling disappear. The bootstrap device layout is wrong for
the native installer contract.

## Prepared code, not a completed installation fix

`tools/vmapple_primary_disk.py` implements a closed-backup migration primitive:

- Validate both GPT copies, CRCs, types, bounds, alignment and APFS NXSB identity.
- Require one iSC, one ordinary APFS, one Recovery, and preserve optional EFI.
- Emit one new GPT disk retaining partition UUIDs, container UUIDs and every
  source partition byte; preserve the installation disk's GPT UUID.
- Use exclusive output creation, sparse zero copying and full per-partition
  SHA256 readback. Reject source identity/mtime changes, links, overlap, duplicate
  identities, malformed geometry and ambiguous primary classification.
- No formatting, resizing APFS, Apple binary change, signing-policy change,
  ticket creation, installer launch or production activation CLI.

The common restore runner now refuses the known-bad split installation layout
before any run-directory or disk writes. Historical recovery-only diagnostics
are not enabled or launched by this change. The changed runner is **local/staged
source only**: never overwrite a script file being read by an active shell.

**129 targeted/regression tests pass**, including 29 new topology/migration
tests and the existing target, iSC, Recovery, evidence-transfer and runner suites.
Shell syntax checks also pass. Tests ran in a separate directory inside isolated Linux, not the production Mac
or physical host. Synthetic fixtures exercise actual migration and byte/UUID
preservation; the runner-refusal tests invoke only its early exit, not QEMU.
They are not a successful guest install, cold boot, or GPU test.

At final read-only inspection (2026-09-03 16:23 UTC), original QEMU PID 974460
is running, target I/O is ok, failed reads/writes are zero, and no native crash
marker exists. The active runner source still has its pre-change SHA256
`7f6214104355f12ff404c8f8ef982e94dee977bb2ea3160e691e05a105028edf`.

## Gates still required after the user releases the hold

1. Export volatile logs; obtain explicit coordinated test-VM shutdown before
   physical-host power-off. The user manages their production guests/host.
2. On a confirmed clean inner shutdown, preserve current AUX, target, Recovery
   overlay AND backing chain, firmware inputs and configuration in new paths.
   Do not regard a live raw copy or old Boot119 backup as current/consistent.
3. Verify available space and flatten only the closed Recovery backup. Build the
   new primary from these closed backups, then verify bytes and all identities.
4. Review the whole block graph: exactly one OS root-role disk, no duplicate
   exposed iSC/Recovery UUIDs, separate preserved AUX utility/NVRAM state, and
   deliberate firmware-root versus restore-scratch handling. The old AUX image
   also contains iSC: prove firmware/kernel ownership and coherence before
   removing its old root-role exposure. This graph is NOT yet activated/validated.
5. Integrate only the newly installed GPU into the agreed isolation boundary;
   confirm hardware Vulkan device selection, not software fallback. Keep
   existing RX580/USB/Wi-Fi passthrough and production QEMU unchanged.
6. Only then authorize one next startup. Reconfirm native primary/iSC/Recovery
   discovery before using the same local OS archive. Preserve remaining B010
   staging coverage and independent B012 cleanup checks if still required.

No promise that a GPU fixes this storage error, CPU emulation, or later installer
requirements follows from this diagnosis. Activation is held, not automatically
scheduled; installation/account creation remain incomplete.
