# Blockers

## Current validation status — 2026-09-03, Boot120 local prepare repair

Boot120's internal target passes the actual prerequisite check and reaches the
installation progress UI. At 10:23 UTC the installer shows a software-update
personalization failure (B012), traced to UpdateBrain's CFRelease(NULL) cleanup.
The already downloaded 25G83 payload is preserved, locally repackaged as validated
ZIP64 and backed up outside the inner APFS target.
The first local UI launch exposed the previously established B010 tmpfs staging
problem again; the bounded combined session now passes actual B010 service
startup and retains the B012 one-shot guard after normal metadata retirement.
The local 26.6.2/25G83 archive completed extraction and integrity verification
at guest 13:30:13 UTC, with zero additional OS packages downloaded. Preparation
then failed at PREFLIGHT_PERSONALIZE (fraction 0.15) at 13:30:34. The new service
PID 10125 has the same B012 NULL cleanup stack. B013 below explains why the
old adapter could never match its kernel process name. The adapter is now fixed
and validated; actual one-shot correction/resumed installation is not yet proven.
Installation, account creation and installed-system boot remain incomplete. The
existing 25G72 IPSW was reused for recovery boot, not a complete offline workflow.
See `docs/boot120-install-progress.md` for current evidence; Boot119 below is history.

### B013 — NULL-cleanup adapter compared a truncated kernel name with 49 bytes

- **State:** Code defect fixed; live correction and continuation pending.
- **Evidence:** Private second failure archive
  `boot120-local-prepare-crash-20260903-1330.tar.gz`, 212,910 bytes, SHA256
  `6c6fac838c94ab9e212aed1c08b2f51d8e5c9af4ed1ecdf0ffb3e593869aa592`.
  PID 10125 crashed in `CFRelease.cold.2` via the exact same UpdateBrain
  `checkAndReissueUCRTAndOICIfNeeded:` cleanup. CF/UpdateBrain UUIDs and the
  CF load address are unchanged. Do not confuse old PID 9169's normal teardown
  with new PID 10125's SIGTRAP. The debugger's natural timeout occurred later,
  so timeout is not the cause of this failure.
- **Root cause/source:** `bridge_boot120_null_cleanup.py::NullCleanup.stop`
  read `proc+0x5dd` and compared it with the 49-character executable name.
  XNU `resource_monitors.h` defines `proc_name_t[2*MAXCOMLEN+1]`, and
  `kern_exec.c::set_proc_name` copies at most 32 characters. Therefore the
  intended service was silently rejected before the existing cleanup planner.
  Existing planner/session tests mocked a full name and missed the adapter bug.
- **Correction:** Read precisely 17-byte p_comm and 33-byte p_name fields, and
  require the exact executable LC_UUID at proc+0x608. Truncated names alone are
  not an identity. The exact RestoreKernelCache's proc_selfname and originator
  UUID getter establish offsets/bounds; live instruction checks enforce them.
  All existing caller UUID, full function bytes, NULL local, frame, signed LR,
  one-repair budget and PC-only authenticated-epilogue restrictions remain.
- **Validation:** 89 focused tests pass inside isolated Linux, including seven
  process-identity and eight real-adapter callback regression tests. The fixed
  adapter passes read-only live verification and detaches normally. No build,
  test, package or QEMU replacement ran on either production machine.
- **Next bounded experiment:** One user-authorized retry in the existing inner
  VM using the verified local archive, with the corrected one-shot adapter.
  No signatures/tickets/policy decisions are replaced and no retry loop is used.
  A COMPLETED/1.0 callback followed by an error is failure, not installation
  completion; require actual NULL repair evidence and later prepare success.

### Installer GUI acceptance

- The genuine QMP capture `screen-installer-first.ppm`, timestamp
  **2026-09-03 03:09:33 +0800**, shows the foreground **Install macOS Tahoe**
  menu and a complete welcome window: Tahoe artwork, title, setup instructions,
  and the blue **Continue** button. The old Recovery window contents are absent.
  The PNG is a format conversion of that QMP image, not a reconstruction.
- Serial records real `InstallAssistant` PID **312**, build 532, at 19:06:00 UTC,
  and `osinstallersetupd` PID **318** at 19:06:24 UTC. The exact BaseSystem
  executable is a **Mach-O 64-bit arm64 executable**; the boot log identifies
  **Darwin 25.6.0 / RELEASE_ARM64_VMAPPLE**, and the same BaseSystem's
  SystemVersion identifies **macOS 26.6 / 25G72**. This is not x86 macOS.
- At acceptance, QMP reported **running**, **8 vCPU**, **17179869184 bytes RAM**.
  Boot119 was left alive without another boot or installer Continue click at that
  checkpoint. See the subsequent installation attempt below. No disk selection, installation completion,
  installed-system boot, hardware GPU acceleration, or macOS 27 success is claimed.
- The five earlier transient fence-timeout/writeback losses and unsupported
  texture formats remain open. Both QEMU stdout/stderr are empty at this
  checkpoint; that is not a claim that every graphics path is implemented.
- Evidence, hashes, reproducibility limits, and test gates:
  [Boot119 installer acceptance](docs/boot119-installer-acceptance.md).

### B010 — Installation follow-through: UpdateBrain launch constraint failure

- On the user's subsequent request to finish installation, the welcome Continue
  button was clicked once. After loading installation information, the real GUI
  reported that required installation content could not be downloaded. Evidence:
  `artifacts/boot119/install-20260903032545/03-info-later.png`.
- The guest installation log localizes the failure **after successful download
  and extraction** of the predicate product metadata and `UpdateBrain.zip`.
  `OSISPredicateUpdateInstallerProduct` reports fetch success at 03:29:35 UTC;
  extraction succeeds at 03:29:45. At 03:30:31 the update-brain wakeup fails with
  `SUMacControllerErrorPreflightWakeupFailed=7721`, underlying
  `MobileSoftwareUpdateErrorDomain/MSU_ERR_FAILED_BRAIN_LOAD=27`, "Could not create
  connection to update brain service". This is not a demonstrated download or
  DNS failure. ReportCrash PID 5587 appears while wakeup is pending.
- The matching ARM64 UpdateBrain crash report establishes `CODESIGNING`, code 4,
  `Launch Constraint Violation`, before application frames. AMFI logs
  `c[4]p[1]m[1]e[0]`: the executable's own launch constraint does not match.
  Reading its unmodified Apple signature with guest `codesign -d -vvvv` reveals
  exactly `is-sip-protected=true` and `validation-category=1`. AMFI already
  reports validation category 1; the staged executable has no `restricted` file
  flag and lives on the Recovery Data **tmpfs**. Thus the missing SIP-protected
  launch location is the immediate mismatch, not an ARM CPU exception or DNS.
  Why roleaccountd staging lacks the expected protection, and the appropriate
  filesystem-level correction, remain under investigation. No signature was
  replaced, no launch constraint was stripped, and no retry loop was started.
- Source-level follow-through: the matching tmpfs `tmpfs_alloc_file` passes type,
  UID/GID/mode to `tmpfs_alloc_node` but does not store `vnode_attr.va_flags`.
  The vnode creation fallback in XNU `kpi_vfs.c:vnode_setattr_fallback` only
  supplies extended security/ACL metadata, not file flags. The protected staging
  root and unprotected `exec`/payload match this omission. A normal `chflags`
  attempt on a newly created empty probe file is denied by SIP; no protection
  setting was disabled to work around that denial.
- A temporary, opt-in **metadata compatibility bridge** is under validation.
  It verifies exact 25G72 instruction/layout contracts and only adds the lost
  `SF_RESTRICTED` bit beneath the already-protected RoleAccountStaging anchor.
  Existing-object repair is limited to the known Apple cache and its `exec`/`tmp`
  directories; unknown bundles/probe files are excluded. New creations must
  already request the bit and have a protected parent. No guest text or signature
  bytes are rewritten. The 11 pure contract tests pass inside the isolated Linux
  VM; this does not establish successful UpdateBrain launch or installation.
  Use **gdb-multiarch**, not native x86 GDB, for this guest debugger interface.
- One post-correction Continue attempt failed at 04:41:45 UTC. The lower-level
  error changed to `xpcproxy: setup_role_account failed, error 0x4f` (EFTYPE 79),
  before the service executable starts. No new launch-constraint crash report was
  generated. Source signature verification passes. The bridge was cleanly detached with 134 existing
  metadata repairs and **zero new-create repairs**; new-file inheritance remains
  unvalidated.
- A read-only instrumented attempt at 05:00 UTC localized the failure: the new
  staging copy returns zero (later shown not to prove success), but the static-code object is null before
  the role-account signature requirement is evaluated. Error reply is 79; the
  signature-requirement and signing-information calls are not reached. Reference
  daemon SHA-256 is `b25d5bd50c97efb7cf43643b91802fae701846bcd8e53eeae63666633eb87155`.
  Its live UUID and exact probe instructions were verified. Log:
  `roleaccount-stage-trace-v2.log`. A prior v1 observer detached with zero
  observations because of signed-address conversion; no VM restart occurred.
  Next bounded evidence: the precise CFURL/static-code path and original
  `SecStaticCodeCreateWithPath` status, before changing any behavior.
- Follow-up v5 evidence at 05:18 UTC disproves success of the staged copy:
  `COPYFILE_ERR` callbacks start at the temporary root directory and continue
  through its contents. The callback ignores these errors and recursive copy
  returns 0. The non-null CFURL then yields **-67068 / static code not found**.
  This is a missing staging destination, not a rejected Apple signature. The
  first directory-create errno remains to be collected. No policy/signature
  bypass is applied, and the next experiment is at the filesystem level rather
  than another full installer retry. The v5 observer detached at errno 79.
- Read-only storage-class evidence at 05:34 UTC establishes a second tmpfs
  metadata omission: Sandbox asks the protected parent for `va_flags` and
  `va_extflags` (mask 0x200000000400), but tmpfs reports supported mask 0x1600450,
  missing bit 45. It therefore returns default `system` class 03 instead of
  following the parent's RoleAccountStaging xattr. The original daemon is
  entitled for RoleAccountStaging, not arbitrary system-protected storage.
  Source: matching Sandbox `_rootless_get_storage_class`, tmpfs getattr, and
  XNU `vnode_getattr`; log `tmpfs-storage-class-trace-v1.log`. This explains why
  restricted flags alone are insufficient. Both guest observers are detached.
- A native APFS differential uses a NEW 1 GiB scratch image inside the approved
  data filesystem, not the installation target. QEMU's automatic USB hub was
  not enumerated by this guest; `hw/usb/bus.c:usb_claim_port` explains the automatic
  hub when one root port remains. Only the newly added empty hub was removed,
  and the same scratch disk was attached explicitly to free root port 4.
  Verified blank guest disk8, serial MACVMMETA20260903, size 1073741824 bytes,
  was formatted once as APFS macvm-staging, disk9s1 on disk8s1, volume UUID
  2DEFBA24-3C0E-4BC2-BA2D-A66AF5879A3A. Formatting and ownership enable succeeded.
  No production resource or original guest device was replaced. Native metadata
  inheritance and signed-copy validation are next; this is not an installed OS.
- APFS copy evidence at 05:45–05:50: signed contents verify, but `ditto` does not
  establish the restricted flag on either the existing volume root or a new
  directory. The latter does preserve the storage-class xattr and mode. The
  earlier helper PASS marker was false and is retired; explicit metadata guards
  now fail closed. Next: the original vendor `rootless-init -b` startup repair,
  with unchanged rootless.conf, on a fresh APFS staging volume (disk9s2, UUID
  489C9422-DAD7-4130-8DBC-9C934B031438). Old tmpfs staging is to be preserved below
  an ordinary mount; no signature/policy edit or VM restart is required.
- The ordinary APFS mount was denied with EPERM and safely returned to its
  `/Volumes` mount; no rootless-init repair was executed. The next source-driven
  tmpfs bridge fixes the uncached-new-vnode path predicate and reports the absent
  requested `va_extflags=0` only beneath the verified protected anchor. All 16
  contract tests pass in isolated Linux. In the single subsequent preflight,
  the actual role daemon resolves **RoleAccountStaging / class 0f**, errno 0,
  instead of default system/class03; new staging objects really are created with
  inherited restricted flags. This is not yet proof of UpdateBrain execution or
  completed installation. This was the initial live checkpoint in
  `tmpfs-metadata-compat-v4-role.log`; the final result follows.
- Verified at guest 06:20:03–06:20:18 UTC: the new staging cache
  `exec/872415233.7287.xpc` launches UpdateBrainService PID 10501, wakeup reaches
  100%, and the installer identifies **Tahoe 26.6.2 / 25G83**, **Device is supported**.
  The genuine license page and agreement-confirmation sheet are displayed.
  No new launch-constraint crash is recorded. The bridge then detached normally
  at its observation budget: 132 newly created objects inherited restricted
  flags, 0 existing-object repairs, 8974 missing extended-attribute responses.
  The VM and UpdateBrain remain running. This crosses preflight only: installation,
  account creation and installed-system boot are not yet complete. The temporary
  getter bridge is not a persistent filesystem implementation.
- Initial target inventory also lacked a full-system disk. With explicit user
  approval, a new 200 GiB host-side test data image was created. Both live VMs'
  PCI disks report `hotpluggable=false`; the approved new disk therefore uses the
  **outer test QEMU only** as a loopback NBD exporter. It was formatted with ext4
  and mounted **inside the isolated Linux VM**. No existing disk was resized.
- A new 128 GiB raw target inside that filesystem was attached successfully to
  Boot119's existing hotpluggable virtual USB bus. macOS `diskutil list` identifies
  it as **disk6**, external physical, **137.4 GB**, without a partition table.
  Exact byte size, serial and empty whole-device identity were rechecked, then
  only the blank new disk was successfully prepared as GPT/APFS `macos26`.
  `disk7s1` is the new APFS volume, with physical store `disk6s2`; do not erase
  again on resume.
- After dismissing the failed installer, a QMP screendump request timed out while
  waiting for a console update. QMP still reports running and all disk I/O states
  are `ok`. A separate VNC capture succeeded and showed Recovery Springboard;
  this is not evidence of a VM crash. VNC is now being used to inspect the UI.
- Neither VM was restarted. The approved new storage is not yet automatically
  reconnected after an outer VM restart. Exact resource identities, mount UUID,
  evidence and resume constraints are in
  [the installation progress record](docs/boot119-install-progress.md).

### B011 — Target volume preflight: MSU_ERR_MISSING_TARGET (42)

- After successful B010 wakeup, the original installer validates available
  volumes. Guest system.log at 06:21:57 reports MobileSoftwareUpdateErrorDomain
  code 42, `MSU_ERR_MISSING_TARGET`: "Unable to set target system volume for
  preflight". The same error is then reported for the two diagnostic volumes
  during enumeration; these are not manual installation retries.
- License acceptance reaches the genuine disk-selection UI. Selecting the new
  `macos26` shows that exact tooltip and a disabled Continue button. Evidence:
  `artifacts/boot119/install-20260903032545/68-target-check.png`.
- The exact target UUID remains 31209BA2-BC1F-4D51-99C1-4AFF986CB8AA, APFS
  disk7s1 on disk6s2, read-write, owners enabled, ~137.1 GB free, 24 KiB used;
  `diskutil info` reports OS Can Be Installed: Yes. This rules out an absent
  physical disk or exhausted target capacity, not all installer requirements.
- Matching OSInstallerSetupInternal code shows
  `OSISCustomizationController validateTarget:withSystemTarget:error:` obtains
  `liveFilesystemForTarget:`, passes its `diskUUID` to `setTargetVolumeUUID:`,
  then requests `prerequisiteCheckForDescriptor:overrides:progressBlock:completion:`.
  The lower-level MSU target resolution failure was subsequently localized below.
  No disk role/partition/security-policy change is justified by the generic tooltip alone.
- **Root cause:** the actual UpdateBrain log at
  `/System/Volumes/Data/MobileSoftwareUpdate/restore.log` receives the correct
  target UUID and reports `Failed to locate update container for target`.
  Matching ARM64e UpdateBrainLibrary 2422.160.6, UUID
  8BB113CF-7583-3554-82B4-B4C009A16A16, implements the selection in
  `-[MSUTargetController setSystemTargetUUID:timeout:]` at file address 0xe7e4.
  An external target with an embedded root device requires a normal internal
  APFS physical store (role 0). The missing-container branch is 0xed98, before
  Update-volume creation. At 06:55:56 UTC, guest IOKit/diskutil confirm both
  internal Apple virtio disks have EmbeddedDeviceTypeRoot=Yes, but contain only
  Recovery and iSC partitions. The normal APFS installation store is on external
  USB disk6. This exactly matches the failed selection branch.
- **Next bounded correction:** preserve the existing target image and attach it
  as an internal Apple virtio root device on a planned inner-VM restart. Keep the
  current AUX/iSC and Recovery disk state in a consistent offline backup and a
  new run directory. Do not reformat, add guessed volume roles, or change installer
  checks. The user approved one planned inner shutdown/restart. Boot119 then
  shut down normally; its offline images, configuration and restore inputs were
  backed up and verified. Boot120 is now running with the same target attached
  internally and has reached Recovery's volume examination screen. No outer VM
  restart or production-resource change occurred. Disk backup is not a RAM
  snapshot; the temporary tmpfs bridge must be revalidated in Boot120.
- **Boot120 acceptance:** the unchanged target is internal disk5s1 on disk0s2.
  UpdateBrain resolves container 6C0D6E74-EBBB-4A40-A7F1-AFDE0A1B34FD and Update
  volume 189F33BD-FE3A-4D0C-8BDD-9F7E55A61725 (disk5s2). Its restore log then
  migrates to `/System/Volumes/Data/private/tmp/tmp-mount-S6DjuV/restore.log`.
  That log records `SUMacControllerCommandPrerequisiteCheck`, `result = success`,
  and `targetDriveIsInternal = YES` for the exact target UUID and 25G83.
  B011's missing-container preflight failure is resolved. Screen 38 reaches
  genuine disk selection; actual installation and account creation remain pending.
  Live checkpoint: `docs/boot120-install-progress.md`.

### B012 — UpdateBrain NULL cleanup crashes before personalization

- **State:** Open; root cause established, correction prepared but not yet
  applied to a matching live call. First observed in the read-only status check
  at 2026-09-03 10:23 UTC. The later actions below were separately authorized by
  the user's request to fix and continue using local assets. No automation or
  VM restart was introduced.
- **Evidence:** Genuine VNC capture
  `artifacts/boot120/install-20260903/46-progress-20260903-1024.png` shows
  "An error occurred preparing the update. Failed to personalize the software
  update. Please try again." The background estimate changed to about one minute;
  neither this estimate nor the progress bar means installation succeeded.
  QMP still reports PID 974460 running, target I/O `ok`, zero failed reads/writes,
  and no native crash marker. Cumulative target writes are 37,619,216,384 bytes;
  this is not a download-completion or installed-size metric.
- **More specific stage evidence:** New serial output near guest 10:14:25–28 UTC
  includes `SUMacControllerCommandPreparePackage` and `result = success`, with
  UpdateBrain PID 7514 and the existing target Update-volume mount. Thus the old
  download-start log is no longer a sufficient description of current progress.
  These successful preparation events do not identify the subsequent error's
  underlying code or establish successful personalization.
- **2026-09-03 follow-up authorized by the user:** The failure dialog was
  acknowledged once to access Recovery Terminal; no retry or reboot followed.
  Exported logs establish UpdateBrain PID 7514 crashed at 10:14:29 UTC with
  EXC_BREAKPOINT/SIGTRAP and `*** CFRelease() called with NULL ***`.
  The stack is `CFRelease.cold.2` → `CFRelease` →
  `-[MSUPrebrain checkAndReissueUCRTAndOICIfNeeded:] +496` →
  `handle_MSUPreflightUpdate +940`. Error propagation is MSU code 7 / XPC
  connection interrupted → SUMacController 7723 → OSInstallerSetup 1007.
- **Exact implementation:** ARM64e UpdateBrainLibrary 2422.160.6 / 25G83,
  UUID `8bb113cf-7583-3554-82b4-b4c009a16a16`, SHA256
  `0d680541b7c6f2e6911cdf2a83e4144892cf3c0ad10325b041c3b6b7a254475b`.
  Function file addresses 0x5130c–0x51510 initialize the ticket local to NULL,
  attempt to read `/System/Volumes/iSCPreboot/SFR/current/apticket.der`, log
  the intended skip on read failure, then unconditionally call CFRelease
  at 0x514f8 on that still-NULL local. The live SFR directory is absent.
  This establishes the cleanup defect, not a signing-server rejection or a
  QEMU native crash. Later package signature/content/personalization checks are
  separate calls and remain unchanged; no ticket is fabricated.
- **Bounded correction prepared, not yet applied:**
  `tools/updatebrain_null_cleanup.py` and its Boot120 adapter permit one PC-only
  jump from the exact CFRelease NULL failure block to its own real epilogue.
  Exact process, image UUIDs, full caller bytes, NULL local, saved stack/LR and
  instruction contracts must match. The original RETAB still authenticates the
  unchanged return address. No disk/text/signature-policy write is permitted.
  Nineteen planner tests pass in isolated Linux. The live read-only `verify`
  mode passed at 10:45 UTC and detached. Repair-only mode was subsequently armed
  during one local UI launch, but no matching call occurred. It was explicitly
  detached by SIGINT with `repaired=False` after the earlier B010 startup failure;
  the original VM remained running with I/O `ok`.
- **Offline prerequisite:** The completed 25G83 UpdateBundle was preserved
  before any retry: 2,233 regular files / 19,202,615,016 bytes, matching file
  paths/sizes and key-metadata checks, with `CLONE_COMPLETE`. This is an APFS
  clone on the same target volume, not an independent-disk backup. A separate
  local working product was assembled. Full control-flow review disproved the
  initial static-directory assumption for Recovery: getenv at 0x7560 branches
  before the static preference at 0x7660, using Recovery's own mutable-product
  paths instead. A normal local UpdateBundle ZIP route is now prepared.
  The original downloaded PKG was removed by Apple's
  successful payload-disposal operation, not by this repair.
- **First local UI launch:** Unchanged secondary InstallAssistant PID 8206 and
  helper 8213 launched, found the local asset metadata/UpdateBrain ZIP, and
  extracted the latter successfully. Two automatic UpdateBrain service starts
  failed with `setup_role_account` EFTYPE 79, matching B010's missing tmpfs
  attribute/staging failure, before B012. The helper then exited normally; no
  target selection or fresh OS payload download occurred. Do not label the
  failed startup a completed local installation path.
- **Offline archive state:** The first ditto archive wrapped 32-bit ZIP directory
  offsets and was rejected without giving it to the installer. The replacement
  uses the existing libarchive ZIP64 writer; the same-library tiny read/write
  probe passed. The full 19,203,380,932-byte archive subsequently passed guest
  CRC, was promoted to `UpdateBundle.zip`, and has `LOCAL_ARCHIVE_READY` after
  restoring the unused static preference. Its separate isolated-Linux copy and
  native ZIP64/CRC/inventory check have now completed successfully. No large remote OS payload
  was downloaded by this local preparation.
- **Next bounded experiment:** Use one
  debugger session for the existing B010 metadata contract plus one B012 cleanup
  correction. `tools/bridge_boot120_local_install.py` preserves both scopes and
  budgets; no old/unknown bundle relabelling is enabled. The focused suite has
  **92 passing isolated-Linux tests**, including detach-on-SIGINT/error and
  read-only HMP memory-boundary tests.
  Prior `tmpfs-metadata-compat.log` proves the metadata observation budget was
  actually exhausted (100001 observations). The combined session now retires
  only metadata breakpoints on that explicit normal limit, keeping the separate
  one-shot NULL guard active. It never continues a contract error, unknown stop,
  SIGINT or completed NULL correction. This prevents the metadata lifetime from
  silently disarming the later preflight correction.
  Actual local preflight/installation still requires live acceptance. No
  automatic follow-up, reboot loop or security-decision alteration is authorized.
- **Private evidence:** `boot120-personalization-20260903-logs.tar.gz`,
  332,738 bytes, SHA256
  `e819412dbac150b98a28744f89c934384096a7527347b8a205df06cd315c5cd6`,
  under the isolated VM's installation-data/install-analysis directory.
  Apple assets, crash dumps and detailed private logs are not committed.

### Graphics storage follow-up

- The earlier Boot118 QMP screenshot, `screen-installer-before-new-build.ppm`,
  still shows the foreground Install macOS Tahoe menu and an installer-sized
  window with stale Recovery contents. The bounded read-only
  `installer-window-stack.log` has InstallAssistant PID 476 in the normal
  NSApplication event loop. Repeated clicks or longer waiting do not establish
  missing image semantics. Boot118 did not pass installer-welcome acceptance.
- The new native graphics storage path is implemented in
  `runtime/metal_draw/graphics_storage.rs` and `engine/graphics_storage.rs`:
  actual raw guest format, explicit descriptor class, seed/upload, graphics
  barriers, fence completion, native readback, cache invalidation and bounded
  guest writeback. Linear and IOSurface backings must still resolve to the
  same physical spans and mapping generation before writeback; overlapping
  sampled/storage/attachment views or unproven backings decline explicitly.
- Independent pixel tests cover nonzero seeds, RGBA16F/RG16F/RGBA32F/integer
  values, partial coverage, BGRA order, skipped primary readback, frame-buffer
  inputs, MRT, vertex and fragment storage, and ring/pool reuse. FakeHost
  regressions cover 4K/16K pages, padding/neighbor preservation, map/PFN reuse,
  unmapping, invalid byte extents and overflow.
- A strict validation-layer sweep caught two pre-existing readback lifetime
  defects: a second `acquire_readback` overwrote the prior live allocation;
  teardown reclaimed returned leases only after draining the free list.
  Prior live slots now stay owned by the entry, and teardown reclaims before
  draining. Both transitions have direct regression assertions. The first
  clean sweep passed 1317 unit + 71 graphics/compute tests, one intentionally
  ignored performance test, zero VUIDs. Later expanded tests remain a separate
  gate and must not inherit that result without rerunning.
- Expanded shader tests exposed raw-word ID scanning: a loaded image with
  SSA ID 32 collided with literal float widths. A grammar-decoded operand-use
  API in metal2vulkan now distinguishes IDs from literals, enums and strings;
  the storage escape analysis still rejects actual opaque-handle escapes and
  unknown opcodes. Its initial 2 parser and 20 access-analysis tests pass.
  `StorageImageWriteWithoutFormat` was incorrectly numbered 34 (ImageCubeArray)
  in the existing runtime helper; corrected to Khronos value 56, with an
  independent ordinal assertion and a GPU test of actual specialization.
- Final post-fix native Vulkan gate: **1318 unit + 58 graphics + 14 compute
  tests passed**, one intentionally ignored performance test, zero validation
  errors. It includes half/int16 conversions, framebuffer fetch to BGRA and
  real format/capability specialization. The full host-window unit gate has
  **1356 passed**, zero ignored/validation errors. Translator: **1093 unit +
  3 registry + 6 fallback passed**, workspace/all-target strict Clippy passed.
  Python: **495 passed**, zero skipped with temporary-image formatter tests.
  Native feature-matrix check passes; Apple cross-check unavailable.
  Reims Clippy still reports the same 13 existing diagnostics, not a clean tree.
  Final logs: `boot119-graphics-final-gate.log`, `boot119-host-window-final.log`,
  `boot119-translator-full.log`, `boot119-translator-clippy.log`,
  `boot119-python-full-gate.log` under the isolated VM's
  `/home/macvm/analysis/boot116-rootcause/`.
- Boot119 built successfully at `build/qemu-boot119-graphics-storage`; binary
  SHA-256 `bfedb312ba18bcaeed2ca67f449575295eb42c2a986308676e7ab17e809ce411`.
  Version and shared-library resolution checks pass in the isolated VM. The
  build retains source snapshots including new files, and the Boot118 binary
  hash remains unchanged. After retaining `screen-installer-final-pre119.ppm`
  and the complete Boot118 run, a scoped QMP quit ended PID 842499 normally.
  Boot119 started at 18:44 UTC on September 2 (02:44 September 3 CST), PID
  925112, with native crash capture attached. Only one inner VM runs, still
  8 vCPU / 16 GiB; recovery inputs and authentication policy are unchanged.
  Its fail and draw logs are explicitly run-specific. The later Boot119 UI
  acceptance checkpoint is recorded above.
- Boot119 reaches Boot Picker, then Language Chooser PID 237 after one Options
  selection and one Continue. A single click on the observed language arrow
  launches Recovery Springboard PID 261, which reports `Activated` at 19:00:30
  UTC. No repeated clicks, authentication changes, or additional boot occurred.
  The current run has five `resident_read` fence-timeout losses during language
  composition (elapsed-log times 647936, 666380, 691573, 846363, 886777 ms).
  Later draw completions show the queue recovers without restarting; a bounded
  two-second native CPU profile taken afterwards contains 150 samples, zero
  lost samples, mostly TCG rather than active llvmpipe. It does not identify
  the shader active at each timeout. QEMU stdout/stderr still have no VUIDs.
  Source inspection: the engine fence limit is five seconds; the render-flush
  error arms unpin the resident and consume the deferred obligation, including
  on transient TIMEOUT. Pending GPU cleanup itself stays fence-owned. Treat
  loss of the guest writeback obligation separately from unsafe GPU lifetime;
  simply increasing the wait is not a demonstrated root-cause fix.
- Type-12 investigation now confirms the exact 25G72 driver's format-info
  branch for 0x226/0x227 selects two planes, each with four-byte element/block
  geometry, gated by the driver's capability query. This does not establish
  packing/channel semantics. No guessed RGBA interpretation or feature-bit
  suppression is included in the new code.
- Exact-driver allocator inspection now resolves `allocDimensionNormal` at
  unslid 0xd8e0 and its dispatch at 0xdb30. Each plane uses a 24-byte header plus
  36 bytes per mip, including its own base offset, slice extent, block geometry,
  mip offset/extent, row stride and dimensions. A one-mip dual-plane record
  therefore has two 60-byte layouts; the captured type-12 envelope has a 12-byte
  prefix and 44-byte serialized descriptor. The allocator proves layout, not
  RGB/alpha encoding. Private disassembly stays only in the isolated analysis
  directory and is not repository source or a test fixture.

### Earlier Boot117/118 evidence and gates

- Boot117 ran one uninterrupted macOS 26.6/25G72 ARM64 recovery boot in the
  isolated `macvm-validation` VM, using the new iSC layout and shader-contract
  binary. Native APFS mounts xART, iSCPreboot and Hardware; the prior missing
  Hardware directory crash is absent. `mobileactivationd` PID 124 remains alive.
- Recovery Springboard PID 409 launches after Language Chooser Continue (`en`).
  Serial records the actual activation result `Activated` at 16:10:33 UTC,
  `showWindow` at 16:11:08, and KeyRecoveryAssistant success (200) at 16:11:38.
  No activation state or authentication result was fabricated or patched.
- QEMU then exits **SIGSEGV/139**, around 27 minutes, not by manual stop or
  timeout. `native-crash-watch.log` captures llvmpipe worker 9 at RIP 0, with
  several sibling workers at the same null call. Main thread is in the Vulkan
  sampled-image pool. This identifies the failing rendering subsystem, but
  does not yet establish which shader instruction caused the null call.
- `qemu.stdout` retains VUID 07988/08114 (missing binding 161), then 07990
  (binding 163 declared STORAGE_IMAGE by SPIR-V but supplied SAMPLED_IMAGE)
  and an Rgba16f versus BGRA8 view mismatch. Empty stderr is not a clean gate.
  The engine built layouts only from supplied resources, without checking the
  complete shader interface; the runtime merely logged absent texture binds.
- Last real screenshot: `artifacts/boot117/screen-language-ready.png` is the
  gray language/progress background, not readable recovery utilities or the
  macOS installer. There is no accepted installer screenshot yet.
- Exact run evidence remains at
  `/home/macvm/runs/aux-26.6/xnu-imgsrc-reims-boot117-isc-complete`.
  Binary SHA-256:
  `29b608a38ff2f2a2dc5ef48dd2ce7b403f0004eed9a1ff2f4ab129a211cb60b0`.
  The old run, binaries, disks, logs and production machines are unchanged.
- New descriptor preflight checks missing bindings, descriptor classes,
  sets, image dimensions/array/multisample state and unsupported descriptor
  arrays before context creation or submission. Seven focused synthetic tests
  plus two GPU integration tests pass in the isolated VM. It rejects unsafe draws; it does **not** implement
  storage textures or make those previously missing pixels correct.
- MRT ColorInput 1..7 now uses same-format pass-before snapshots, retaining
  sparse input indices and matching input-attachment device limits. CLEAR and
  LOAD semantics, primary fetch combinations, pooled/resident primary paths,
  depth, and RGBA8/RG16F/RGBA16F secondaries pass 84 pixel-checked combinations.
  The matrix exposed VUID 09600: the old layout was read before an image was
  recreated on format change. Querying the layout after registry ensure fixes
  that stale-image state. Primary `target_clear` is also consumed now.
- SDK MTLPixelFormat.h identifies 0x3f as RG16Uint (not float/unorm). Native
  upload preserves its four-byte texels without RGBA conversion. Padded-row,
  short-input and actual integer texel-fetch tests verify values through 65535.
  Integer test samplers must use nearest filtering: the initial fixture used
  linear and triggered VUID 04553 despite nominal test success; the corrected
  fixture passes the strict validation gate. No product sampler default changed.
- Latest isolated checks: **1347 library tests passed** with host-window,
  **1309 library tests passed** with the actual QEMU-linked `backend-vulkan`
  feature arm, including five bounded diagnostic tests. The final product-arm
  GPU gate with diagnostic capture enabled has **67 graphics/compute tests
  passed**, one intentionally ignored performance test, zero validation errors.
  **494 Python tests passed**, zero skipped, including Boot118 configuration and
  the native-crash capture helpers. Feature-matrix native Vulkan check passes;
  Apple cross-check is unavailable (no Apple target/rustup in this guest), not
  verified. No build or test was run on the production Mac to fill that gap.
  Clippy has 13 pre-existing diagnostics outside the feature edits, so the tree
  is not claimed warning-free. No installer completion is implied by these tests.
- Remaining connected gaps: primary `target_format` is still not consumed
  through allocation/seed/readback; graphics STORAGE_IMAGE access/synchronization
  and writeback are not implemented; type-12 176-byte texture descriptors are
  unsupported. Do not guess aliases, fabricate transparent textures or change
  descriptor class without proving the shader operations and texture contract.
- Read-only PVG page-table helper passes four tests (4K/16K geometry, flagged
  PFNs, unmapped/malformed tables, short reads and cross-page spans). Idle
  task-4 root entries were zero; transient unmapping is only a hypothesis.
  The live type-12 watch hit but failed its pointer/length guard and detached.
  No descriptor bytes were obtained; diagnostics now normalize unsigned
  registers and retain rejected length/pointer values. A new capture is needed.
- Opt-in `REIMS_VGPU_CAPTURE_REJECTED_CONTRACTS=YES` captures unknown descriptor
  prefixes directly at the live resolution point and retains rejected vertex/
  fragment SPIR-V with binding metadata before pipeline creation. Capture-only
  limits: 64 KiB descriptor prefix, 4 MiB/artifact, 32 MiB total, 128 captures.
  Exact duplicates are suppressed. Files/directories are owner-only and
  create-new; RAM-only probe reads reject MMIO holes/overflow and cannot write.
  This is private evidence under guest `/tmp`, never a committed Apple fixture.
- Native crash watch validates the exact QEMU executable/PID and the isolated
  hostname, then continues execution. On a real SIGSEGV/SIGABRT it records all
  thread stacks, registers, mappings, and at most sixteen 64 KiB readable
  executable windows around crash frames. Files are exclusive/owner-only;
  no full guest-memory core is generated and no VM is manually killed.
- Boot118 built successfully in `build/qemu-boot118-render-contract` from the
  tested patch set; QEMU reports 11.0.93, SHA-256
  `b260ad46476fbc8496692b0932f1aff7d059b087084f6c333964b0838f802d42`.
  Boot117 binary hash verification passes. The new run is active at
  `/home/macvm/runs/aux-26.6/xnu-imgsrc-reims-boot118-render-contract`, QEMU
  PID 842499, 8 vCPUs/16 GiB, GDB 12354, VNC loopback display 118, no timeout.
  Initial restore helper and GDB phases both return zero. The native watcher
  attaches using sudo inside this VM because its ptrace policy rejects a
  sibling process attach; no ptrace/sysctl policy was modified.
  The runner changes only binary/run/socket identity and
  opt-in contract capture; the Boot117 recovery-chain and storage inputs remain
  unchanged. Primary native-format seed/readback and graphics storage-image
  semantics are still open work, not included in the completion claims above.
- Native primary-format audit: `engine/exec.rs` still derives allocation and
  primary alias snapshot format from the BGRA boolean and allocates four bytes
  per readback pixel. `engine/mod.rs::ResidentReadSnapshot` drops `slot.format`;
  both `read_target_inner` and `read_target_leased` likewise assume four bytes.
  Runtime `metal_draw/vulkan.rs` CPU seed, `M2vDrawSpan::Pixels`, surface-cache
  and writeback routes carry only RGBA8/BGRA8. Enabling `target_format` at the
  render-pass alone would therefore create a new buffer/format mismatch.
  A complete follow-up needs format-bearing readback/seed data through these
  consumers, exact-size guards and native-value Store/Load/sampling tests,
  including format changes under one identity and half-float values outside
  [0,1]. Current MRT tests prove GPU snapshot/sampling, not native CPU readback.
- Boot118 live evidence: Boot Picker reaches a real Recovery/Options screen;
  selecting Options and Continue launches Language Chooser PID 234. Actual
  `screen-language-window.ppm` shows the complete readable language list and
  forward button. English Continue is confirmed in serial at 17:22:27 UTC.
  This is progress beyond Boot117's gray background, not an installer verdict.
- Springboard PID 299 records real `Activated` at 17:23:09 UTC and successful
  KeyRecoveryAssistant authentication (200) at 17:24:24. After cold compilation,
  the actual `screen-utilities-menu-2.ppm` shows readable Restore from Time
  Machine / Reinstall macOS Tahoe / Web Browser / Disk Utility and Continue.
  Central icons/backgrounds remain incomplete. The same Boot118 is retained;
  Continue launches **InstallAssistant PID 476**, build 532, at 17:41:08 UTC.
  Its actual welcome window is still awaited; process launch alone is not the
  accepted installer screenshot. The read-only recovery image's actual
  `/Install macOS Tahoe.app/Contents/MacOS/InstallAssistant` is Mach-O ARM64
  (not a universal/x86 executable), and SystemVersion.plist is 26.6/25G72.
- Selection appeared visually unchanged even after input. A bounded read-only
  GDB snapshot (`springboard-input-stack.log`) verifies the 25G72 instruction
  contract and detaches normally. Springboard's main thread is in NSApplication
  event wait, not blocked on activation; coherent symbolization uses this boot's
  dyld slide 0x0b6c4000, derived from mach_msg2_trap +8 and corroborated by the
  frame chain. The subsequent screenshot shows Reinstall selected and Continue
  disabled during InstallAssistant launch: the earlier highlight was stale,
  not evidence that the inputs were rejected. No input/QEMU patch was made.
- The direct probe now captures four complete 176-byte type-12 descriptors in
  `/tmp/reims-vgpu-contract-842499` (0001, 0002, 0006, 0007), with task/ref/GVA
  and explicit page_shift=14. They have one allocation header, two layout
  records, and a trailing serialized texture block naming format 0x226; do not
  reinterpret either plane as a normal RGBA texture until its contract is known.
- Captured rejected fragments 0004/0005 identify a more precise binding-161
  cause: the variable is loaded, but that load's result has no instruction
  consumer. The compiler retains an unused descriptor load, which makes the
  resource statically used for Vulkan despite no image read consuming it.
  `passes/finalize.rs` calls `function_referenced_ids` before dropping globals,
  so that unused load keeps the descriptor/interface alive. A narrow structural
  elimination of non-volatile unused descriptor loads is now implemented before
  liveness in `passes/finalize.rs`, preserving image operations, escaped handles,
  indirect/non-opaque loads, memory-access operands and volatile decorations.
  The synthetic AIR test keeps the real texture read and drops unused texture/
  sampler bindings without an `air.arg_unused` hint. Reflection still describes
  declared AIR resources; documentation and legacy fixtures distinguish that
  metadata from live SPIR-V. Isolated tests: **1091 unit + 3 registry + 6 fallback
  passed**, workspace/all-target Clippy `-D warnings` passes. This subsequent
  translator edit is NOT loaded into the already-running Boot118 binary.
- Boot118 captures the actual graphics storage-image failure as private fragment
  0025: a framebuffer-input read feeds a real image write at binding 163 with
  Rgba16f. Supplied runtime resource is sampled BGRA8 (64x64). This is not an
  unused descriptor and must not be eliminated or replaced with dummy content.
  Required implementation spans native texture staging, format specialization,
  STORAGE_IMAGE descriptors, graphics-stage synchronization, post-draw writeback
  and resident/cache invalidation. Merely reclassifying the descriptor is unsafe.
- Protocol audit: this guest requests 245 and is clamped to 62; device-info key
  12 advertises two-plane textures and the run uses the existing forced-Apple
  limits setting. Those are current evidence, not proof of implemented support.
  No capability or protocol changes were made during this run. Private format
  0x226 has an external research lead naming RGB10A8_2P_XR10, but plane packing
  and transfer semantics still need authoritative driver/format proof.
- Actual Language Chooser draws also request format 0x3f as a primary render
  target; only sampled RG16Uint is supported by the current patch. The typed
  target/clear/readback path above must cover integer targets too. Their render
  declines are recorded, not hidden by the successful language screenshot.
- Upload work remains paused at the user's request. No Apple artifacts are
  committed. Builds/tests/debugging stay entirely inside the isolated VM.

## Historical checkpoint — 2026-09-02, Boot116 reaches Recovery Springboard

- ARM64 XNU 25.6.0 (`RELEASE_ARM64_VMAPPLE`) and macOS BaseSystem 26.6 build 25G72
  boot and pivot to the recovery root. The old B003 pre-kernel notes below are historical.
- Boot115 reaches `Aqua session established.` and launches RecoveryOS Agent and Boot Picker.
  A genuine QMP capture now shows the Recovery volume icon, keyboard menu, Shut Down and
  Restart controls. This is the startup selector, **not yet the installer**.
- Selecting Options and Continue succeeds: Boot Picker exits with status 0 and
  RecoveryOS Agent launches Language Chooser and launchprogresswindow. QEMU then
  exits with SIGSEGV (139) at approximately 26m53s, before a language-screen capture.
  It was not manually stopped. See B009; no installer completion is claimed.
- Boot116 stays in the same run and passes that startup-selector handoff: after keyboard
  activation, Boot Picker exits with status 0 and Language Chooser PID 439 starts.
  Serial records `show choice window`, `LCA: Refreshing language list`, and later hiding
  Installer Progress. The executable in the exact recovery image is Mach-O ARM64e.
  Actual screenshots show the Apple progress UI and an emerging language-window background;
  no readable language list, recovery utilities or installer screenshot is claimed yet.
  `qemu.stderr` remains empty at this checkpoint, with a native SIGSEGV backtrace watcher
  attached only to the isolated QEMU process. The live dyld slide is 0x4d88000, not Boot115's.
- Language Chooser accepts Continue (`en`) and starts Recovery Springboard PID 494.
  Its main-thread stack is blocked in `MobileActivationMacOS.getActivationState` during
  `_windowDidLoad`, not in the normal event loop. `mobileactivationd` has crashed 19 times
  with SIGTRAP (last PID 644, guest 15:02:14); launchd now defers each spawn by 1199 seconds.
  The actual screenshot still lacks the controls. A process-scoped, observe-only user-crash
  watch is armed for the next automatic service spawn; it neither fabricates an activation
  result nor changes service policy. Boot116 remains the same live run.
- Correction to validation interpretation: `qemu.stderr` being empty does **not** mean
  Vulkan validation is clean. `qemu.stdout` contains six VUID classes: 06340/06341
  (stage storage writes not enabled), 08740 (VariablePointersStorageBuffer / Demote
  capability features not enabled), 08737 (scalar condition with vector OpSelect under
  a downgraded SPIR-V version), 07988/08114 (missing descriptor binding 161).
  Attachment-composition targeted tests were clean; the entire GUI is not.
- The Linux PVG/Vulkan bridge produces actual visible UI on a software renderer. This
  supersedes the initial black screen and B002's missing-backend status, but is **not**
  hardware acceleration or a performance result. The same boot was retained throughout.
- Build, tests, GDB, package installation and execution remain inside `macvm-validation`.
  The production Mac and production hypervisor are not test environments.
- Source-level fixes prepared during the same Boot116 run (not hot-installed):
  SPIR-V retains its actual 1.4+ semantics and required entry interfaces; Vulkan
  supported storage-write/variable-pointer/demote features are queried and enabled;
  unsupported shader feature contracts decline before driver module creation.
  Teardown now retires pooled command buffers before destroying cached pipelines.
  The new deferred-submit/reset test reproduces three VUID-00765 errors on the old
  ordering. With the fix, graphics parity is 48 passed / 1 ignored and compute is
  14 passed with no VUID or SKIP output after installing glslc only inside the VM.
  Metal2Vulkan: 1086 unit + 3 registry + 6 fallback tests passed, Clippy clean.
  Reims: 1334 library tests passed before the teardown edit; full Clippy still
  reports pre-existing lints outside this feature change. Do not claim all checks clean.
- PID 861 reaches `_os_crash` (observed LR 0x104506924); the page-aligned return
  address match identifies `main.cold.4`, the required-directory creation failure.
  The direct user-memory stack read failed, so no full NSError/errno is claimed yet.
  The watch now uses the process's own pmap and isolates field failures; 12 focused
  capture/page-table tests pass. Next automatic service retry is still being observed.
- Follow-up PID 1068 capture **succeeds** with its own pmap (root 0x1c5944000):
  `_os_crash` receives a complete nested NSError naming
  `/System/Volumes/Hardware/MobileActivation/internal`, NSCocoaErrorDomain 513,
  underlying NSPOSIXErrorDomain **1 (EPERM)**. Its main.cold.4 caller and main stack
  are captured in `mobileactivation-crash-watch-v4.log`; watch detaches normally.
  This closes the missing failure-path/errno evidence, without changing activation.
- Static 25G72 mobileactivationd requests
  `/System/Volumes/Hardware/MobileActivation/{internal,logs}`. Boot116 serial explicitly
  reports no iSC Hardware role 320 (0x140), and the old builder intentionally creates
  only xART. This is a concrete storage-layout gap, not a GPU or activation-result fix.
  A separate apfsprogs source copy now builds 1–4 volumes with independent maps/trees,
  UUIDs, fs_index, role and space accounting. Its five real formatter/checker tests
  cover 1–4 layouts, legacy format, and malformed/duplicate/conflicting/oversized
  arguments; independent `apfsck -cuw` and explicit map/checksum checks pass. Another
  32 iSC/EAN/layout unit tests pass. The new three-volume image is offline only until
  the live failure evidence and next-run preflight are complete.
- New offline image `validation-isc-complete-v4-ean.img`, 2 GiB,
  SHA-256 `8617dcc1835e84da0e08d0ee4cee9c035691976da77528c92acc17aa4a80c520`.
  Old v3 template remains `761c7b5d611a6e811cb8cd3b7641f9dc619739b924f5aec8b357da5e411338bf`.
  New QEMU builds and prints version 11.0.93 at `build/qemu-boot117-shader-contract`,
  SHA-256 `29b608a38ff2f2a2dc5ef48dd2ce7b403f0004eed9a1ff2f4ab129a211cb60b0`.
  Build verifies the Boot116 executable hash is unchanged.
  Python all-enabled run: **485 tests, zero skipped**; subsequent Boot117 configuration
  contract is an additional preflight test. Combined Vulkan gate: **62 passed,
  1 intentionally ignored performance case, zero VUID/validation errors or silent skips**.
  Boot117 script refuses overlapping ARM guests and uses `timeout 0s` (disabled),
  avoiding an arbitrary runtime cutoff during diagnosis. It has not yet been launched.
- Latest Python regression run: `python3 -m unittest discover -s tests -q` passed
  **469 tests** in the isolated VM, including EAN header, timer, exit-status and Boot116 configuration contracts.
  The focused preflight subset passed 99 tests and Boot114 passed `bash -n`.
  These results do not imply installer success or a fresh Rust/QEMU full-suite run.

## B004 — Recovery GUI waits for an unexposed AUX/EAN storage service

- **State:** AUX/EAN initialization and guest writes verified; Boot115 also completes the
  keychain/Aqua setup. The startup selector is visible; installer validation remains open.
- **Evidence:** Boot112 `recovery-user-stacks.log`, `key-service-kernel-stacks.log`,
  `keystore-gate-owner.log` under `/home/macvm/runs/aux-26.6/xnu-imgsrc-reims-boot112-rofs-context`.
  User page tables and PAC-aware frame chains show `recoveryosd` PID 77 blocked in
  `SecKeychainLogin` / `StorageManager::login` / `SSDLSession::DbCreate`.
  `securityd` waits in `applekeystored_client_kb_load`; `applekeystored` PID 133 waits in
  `IOServiceOpen`. Its kernel stack waits on the AppleKeyStore workloop gate.
- **Root cause:** The gate owner is kernel thread 179 (`0xfffffe1e4a02dec0`). It is in
  `avp_late_init -> xart_locker_get_size -> AppleVirtualPlatformXART::load -> ean`, waiting
  indefinitely for the **AppleNVMeEAN** IOService. The actual matching string was read at
  `0xfffffe00206f05be`, and the wait's timeout argument is `UINT64_MAX`.
  The runner exposes an iSC APFS disk using `variant=root`, but no `variant=aux` utility
  device. The mounted xART-role APFS volume does not supply the EAN service.
- **Source locations:** QEMU `hw/vmapple/virtio-blk.c` distinguishes root and AUX roles.
  The extracted 25G72 AppleVirtIOStorage binary maps AUX to AppleVirtIOUtilStorageDevice;
  its `createUtilDevice` constructs AppleNVMeEAN, and `StartDevice` requires that utility
  provider. AppleVirtualPlatform `ean` is at unslid `0xfffffe00088a6164`; its wait returns at
  `0xfffffe00088a61c8`. All offsets above were checked against the actual running build.
- **Next bounded experiment:** Retain the root-role iSC disk and add a distinct AUX-role
  utility frontend to run-scoped storage only, after checking `/product/util/regions`,
  EAN header initialization, capacity and overlap with the iSC partition. Exercise runner
  contracts in the isolated VM before the next boot. Do not disable keychain or fabricate
  successful driver returns. Preserve Boot112 until evidence collection completes.
- **Other open observations:** opendirectoryd repeatedly crashes; causality is not yet
  established. PackagesLink creation still returns EROFS and remains a separate issue.
- **Boot113 evidence:** `CreateUtilDevice regionID 6`, `EAN Registration done` proves
  AUX service publication; the previous infinite service-match wait progresses. However,
  `EAN is not formatted = 0` and `AppleVirtualPlatformXART failed to eanWrite proposed
  (e00002bc)` expose uninitialized EAN metadata. The exact driver `verifyHeaderCRC`
  (`0xfffffe0008885280`) accepts missing magic as unformatted; `updateHeaderFields`
  (`...8885334`) does nothing while unformatted. It does not format blank storage.
- **Fix prepared:** `tools/vmapple_ean.py` initializes only a new offline template's blank
  6 MiB EAN region (offset 0x1a00000). A 4 KiB v1 header contains magic 0xeaeaeaea,
  zero entries, 6 MiB capacity, first-free offset 4096, and CRC32 of the first 4092 bytes.
  `addImage` (`...8885b38`) confirms first-free must exclude the header. Every output byte
  is compared with the source; only the header may differ. The iSC partition starts at
  32 MiB and is untouched. Existing outputs/nonblank EAN are rejected.
- **Offline result:** isolated-VM initialization completed; new `validation-isc-xart-v3-ean.img`
  SHA-256 `761c7b5d611a6e811cb8cd3b7641f9dc619739b924f5aec8b357da5e411338bf`.
  Header tests include mutation of each of 4096 bytes and occupied/truncated storage.
- **Boot114 runtime result:** EAN registers without the unformatted warning or `eanWrite`
  error. Actual run-scoped storage now has two xART entries, next-free offset 12288 and
  matching CRC32. This proves guest driver writes, not merely successful service lookup.
  It does not yet prove SecKeychainLogin or the GUI has completed.

## B005 — Incorrect symlink diagnostic success checkpoint

- **State:** Diagnostic source corrected and tested; actual VNOP path verified on Boot113.
- **Root cause:** `0xfffffe0009e91230` returns from attribute preparation, not VNOP_SYMLINK.
  Detaching there falsely labelled a later-failing operation successful. Actual VNOP return
  is `0xfffffe0009e9126c`; completion requires the final common return at
  `0xfffffe0009e913e0`, zero errno, and the same parent-vnode/component-name transaction.
  Old process-name offsets were also wrong; the actual `_proc_name` uses `proc+0x5cc`.
- **Fix:** `tools/symlink_trace_contract.py` verifies BL targets, return instructions,
  final return and process-name instruction before diagnostic mutation. The GDB trace
  matches transactions across vCPU migration and no longer detaches on an intermediate
  successful call. Boot112 retains its original script and is not retroactively fixed.
- **Verification:** 43 symlink/trace tests passed; the instruction contract also passed
  against Boot112's live kernel. Seven page-table/frame-chain tests passed in the isolated
  VM, making 50 focused tests. `tools/arm64_user_memory.py` adds bounded, read-only 16 KiB
  user page-table translation for evidence collection. This is not a whole-project test run.
- **Next experiment:** On the next justified boot, capture the real final symlink errno.
  Do not equate mountrecursive success with GUI completion: recoveryosd logs its failure
  and continues into the independently blocked keychain/session initialization above.

## B006 — Forcing APFS read-only state off blocks a transaction instead of enabling writes

- **State:** Boot113 evidence complete enough to reject this experimental bypass; no GUI.
- **Evidence:** `post-gdb.log` records the actual PackagesLink APFS branch with
  `apfs_mount_ro=1 -> 0` and `tx_ro_byte=1 -> 0`. Unlike the old false checkpoint, no final
  VNOP/common return is seen. Serial repeatedly reports `tx_enter_internal:2370: disk5
  waiting for available tx to open: xid 106`. `mountrecursive` cannot finish.
- **Root cause:** Clearing the read-only gates does not initialize writable APFS
  transaction state for the authenticated read-only BaseSystem mount. The observed
  transaction wait follows the experimental mutation. It is not a missing GPU feature.
- **Source:** `trace_basesystem_symlink_preflight_live.gdb` APFS bypass;
  `inject_basesystem_auth_and_boot_args_trace_mount.gdb` optional RW flags;
  25G72 recoveryosd main at 0x1000015c0 logs mountrecursive failure but proceeds to
  Aqua/session setup. Returning a real write error is preferable to wedging this path.
- **Next bounded experiment:** Boot114 uses the prepared EAN template and explicitly
  disables all four BaseSystem RW / PackagesLink authorization and ROFS bypass options.
  Preserve the real final errno, then detach diagnostics so recoveryosd can continue.
  Proper writable staging/overlay remains a separate installation requirement; it is
  not implemented or claimed by this experiment. Do not edit a live run's disk image.
- **Boot114 result:** real final PackagesLink errno is EPERM (1), with all bypasses
  disabled; debugger detaches normally. No APFS transaction hang. Mountrecursive later
  exits and recoveryosd reaches Aqua session setup. Its later system-wide service delays
  must not be mislabelled as this APFS problem.

## B007 — TCG generic counter runs at 1 GHz against Apple's 24 MHz timebase

- **State:** Board-level fix built and independently tested; Boot115 full boot in progress.
- **Evidence:** Boot114 QMP `qom-get cntfrq` returns 1000000000; live CNTFRQ_EL0 is also
  1000000000. All eight signed DeviceTree CPU nodes report `timebase-frequency=24000000`.
  `timebase-live.log` is preserved with the actual data. Guest logs fast-forward hours
  within minutes and many services report CPU/timeouts. XNU platform source reads this
  DT property; the exact 25G72 `PE_call_timebase_callback` loads the field at unslid
  `0xfffffe000a993728`. A later live read of that field was not obtained because the
  guest had already panicked; do not claim it was directly measured in Boot114.
- **Code root cause:** `target/arm/tcg/cpu64.c` gives the max CPU a 1 GHz default;
  `target/arm/cpu.c` uses that when the board supplies no counter frequency. VMApple's
  CPU creation had not set its board-specific frequency. The mismatch is approximately
  41.67x, independent of ARM instruction translation throughput.
- **Fix:** ordered patch `0033-vmapple-match-tcg-counter-to-apple-timebase.patch` sets
  24 MHz for every TCG CPU before realization. Hardware virtualization is unchanged.
  No generic counter-read or timer-expiry logic is patched.
- **Build:** new `build/qemu-boot115-timebase/qemu-system-aarch64`, SHA-256
  `4816aa777f78794938942e411ca2f36cbd87bde94dd3f1ddc1350ace906882df`.
  Prior binary remains intact (SHA-256 verification passed); source-before and existing
  dirty diff are backed up inside the new build directory. No system QEMU was replaced.
- **Independent ARM64 test:** `timebase-115-smoke/result.json`: all 8 CPU properties and
  firmware CNTFRQ are 24 MHz. Over 2.0006867 seconds, actual counter rate is 24.391146 MHz;
  programmed virtual timer expires at the correct target count. Firmware, assembly,
  command, images and result are retained. Pure regression tests pass (466 methods before
  adding the Boot115 config-consistency method; latest focused 10 methods pass).
- **Known residual:** QEMU intentionally uses an integer nanosecond timer scale. At
  24 MHz this is 41 ns, producing approximately 1.63% drift (measured 1.6298%), not exact
  24 MHz. Changing only the counter read breaks inverse timer scheduling. Exact rational
  scaling would require coordinated counter, expiry, overflow and WFxT tests separately.
- **Boot114 terminal outcome:** recoveryosd initiated reboot; launchd panicked on
  `pre-reboot task timed out`. This is not attributed conclusively to timing alone.
  Panic log and screenshots were retained before QMP quit. Installer UI not reached.
- **Next bounded experiment:** same images, bypasses disabled and same resources, with
  only the new QEMU binary and run identity changed. Check actual XNU timebase, EAN,
  keychain/session initialization, service stability, and a genuine screen capture.
- **Boot115 runtime result:** live XNU timebase field, CNTFRQ_EL0 and all DeviceTree CPU
  frequencies agree at 24 MHz. Aqua establishes, RecoveryOS Agent runs AppKit and
  Boot Picker PID 185 appears. `screen-gpu-current.ppm` is a real 1920x1080 QMP image
  showing the Recovery startup selector. No new boot was used to obtain this image.

## B008 — Graphics backend gaps observed while recovery UI starts

- **State:** Observed, not yet fixed. Boot115 later displays a real startup selector;
  therefore its earlier GPU waits must not be described as a permanent deadlock.
- **Evidence:** `graphics-stacks.log`, `icon-stacks.log`, `qemu-host-stacks.log`, serial
  and `reims-vgpu-fail.log` under the Boot115 run directory. WindowServer was waiting in
  IOGPUWorkQueue::addCommandToTail_slow, Boot Picker waited for WindowServer and icon
  generation, and iconservicesagent submitted 3D icon work. Subsequent commands and
  visible UI prove progress resumed. GPU restart messages are not by themselves proof
  of a particular missing feature being the cause.
- **Code gaps:** Linux `runtime/heap_query.rs::query_size_and_align` unconditionally
  returns NoMetalDevice; its child-packet caller consumes/stamps the command without
  writing a size/alignment reply. `backend/vulkan/engine/exec.rs` explicitly rejects
  simultaneous depth and secondary color attachments. Actual icon draws hit this path.
  The former needs a verified allocation/placement contract, not invented sizes.
- **Next bounded work:** continue the visible UI workflow on Boot115 first. Retain the
  complete evidence and implement focused synthetic regressions for proven rendering
  defects before any new full boot. Do not blindly clear GPU errors or force completion.

## B009 — MRT + framebuffer fetch creates an attachment-count mismatch and crashes Vulkan

- **State:** Reproduced in a focused test at the same crash instruction; attachment
  and lifetime fixes pass targeted Vulkan-validation regressions. New build in progress.
- **Live evidence:** Boot115 serial confirms Language Chooser launch after Options/Continue.
  `qemu.status` contains `QEMU_RC=139`; the isolated VM kernel reports a fault in
  `libvulkan_lvp.so` at ELF offset `0x7c4c8`. Mesa is 26.0.8-1ubuntu0.3, build ID
  `1dab537bd9d19186a0a1e8aef43781f0fa90dbb6`. Apport discarded the non-package binary's
  dump, so no complete Boot115 core is available. Do not claim to have its full backtrace.
- **Independent reproduction:** `mrt_framebuffer_fetch_resident_regression` supplies
  one primary, one secondary and a destination-read input. Vulkan validation reports
  `VUID-VkFramebufferCreateInfo-attachmentCount-00876` (pass 3, framebuffer 2), then
  the small test segfaults at the **same library offset 0x7c4c8**. Evidence is under
  `/home/macvm/analysis/boot115-crash/mrt-fetch-before.log` and the isolated kernel log.
- **Code root cause:** `engine/caches.rs` correctly describes primary, optional input,
  secondaries and optional depth. `engine/exec.rs` chose exclusive MRT/depth/input
  framebuffer branches: resident MRT omitted the input, pooled MRT omitted secondaries,
  and depth+MRT was rejected. Fix unifies the view order for both primary allocations
  and retires the ad-hoc framebuffer exactly once after submission.
- **Additional validation finding:** independent per-attachment masks/blend states were
  used without enabling `independentBlend` (`VUID-pAttachments-00605`). Feature query,
  enablement and an explicit unsupported-device refusal were added together.
- **Lifetime finding:** registry_ensure_color uses dedicated memory, while pool teardown
  assumed every target was slab-backed. Registry, target and recycled-target teardown
  now check slab ownership and free dedicated memory after destroying its image/view.
- **Results:** 6 MRT-focused tests pass with **zero Vulkan validation errors**, including
  a 24-combination pixel/readback matrix. The earlier 52 teardown validation errors are
  gone. Twelve device-feature unit tests pass. A broader run before the lifetime fix
  passed 48 tests with 1 intentionally ignored; it also exposed 32 pre-existing vertex
  SPIR-V NonWritable/vertexPipelineStoresAndAtomics validation messages. That separate
  shader contract is not claimed fixed or validation-clean by this patch.
- **Coverage prepared:** resident/pooled primary, fetch on/off, depth absent/Never/Always,
  one/three secondaries, repeated submissions and independent secondary readback. No
  hardware GPU or performance claims follow from these software-Vulkan regressions.
- **Harness correction:** restore-helper success previously printed smoke passed after
  QEMU crashed. The runner now rejects crash, timeout, malformed or missing exit status;
  only short-smoke mode's intentional TERM is accepted. Its 35 focused Python tests pass.
- **Next bounded experiment:** complete Vulkan validation/pixel regressions and build a
  separate QEMU binary before a new full boot (completed). Continue Boot116's Language
  Chooser/Recovery UI flow without restarting it. Keep Boot115 artifacts and old binary intact.
- **Boot116 build:** `build/qemu-boot116-attachments/qemu-system-aarch64`, SHA-256
  `80d19c41e8e8e9be5a4f662e7f303b770956e14367516634467d5c3388f1ee34`.
  All 2239 build targets completed; Boot115's binary hash remains unchanged. The exact
  linked feature set (`backend-vulkan` without host-window) also passes the 6 targeted
  MRT tests with Vulkan validation and distinct seed/shader pixels for depth rejection.
  The same recovery media, 8 vCPUs and 16 GiB RAM are used; validation layers are enabled.
- **Static check limitation:** Clippy was run with `-D warnings` but is not clean: it
  reports existing decode/doc-comment/unused-import/argument-count lints and a prior
  bool assertion in the primary-format test. No Clippy pass is claimed.

## B001 — Dedicated target environment

- **State:** Closed for Phase 1 build and machine initialization
- **Resolution:** Revalidated on 2026-08-31 inside a separate Ubuntu 26.04 x86_64 VM. The build
  began at 2 vCPUs/8 GiB and the VM was then restarted at the user-approved 16 vCPUs/36 GiB. No
  build, package installation, ARM64 execution, or test ran directly on the production hypervisor.
- **Evidence:** 136 unit tests pass, QEMU 11.0.93 builds, `vmapple` registers, and the paused QMP
  machine-initialization smoke test passes. See `docs/test-environment.md`.
- **Source location:** `scripts/lib/require-debug-env.sh`, `scripts/build.sh`,
  `scripts/check-vmapple-machine.sh`.
- **Remaining boundary:** The VM does not contain a physical GPU and was intentionally not granted
  VFIO, bridge, TAP, or other production-host resources.

## B002 — Linux ARM64 PVG MMIO backend is missing

- **State:** Open
- **Blocker:** Upstream QEMU's `apple-gfx-mmio` is Objective-C and requires Apple's
  ParavirtualizedGraphics/Metal frameworks; reims-vgpu does not publish the requested Linux-host +
  ARM64-guest combination.
- **Evidence:** `third_party/qemu/hw/display/apple-gfx-mmio.m`,
  `third_party/qemu/meson.build`, `third_party/reims-vgpu/README.md`.
- **Source location:** `hw/vmapple/vmapple.c:create_gfx`, reims-vgpu's QEMU MMIO shim and Rust
  runtime.
- **Root cause:** Existing projects independently cover Linux/Vulkan with an x86 PCI guest and
  ARM64/MMIO with a macOS host, but not their intersection.
- **Attempted solutions:** Phase 1 patch substitutes observable unimplemented MMIO sentinels so the
  rest of the machine can initialize on Linux without falsely claiming GPU support.
- **Test constraint:** GPU, Vulkan, compute, and WindowServer validation is explicitly deferred
  until the user installs the NVIDIA RTX 4060 Ti.
- **Next experiment:** Import the thin `reims-vgpu-mmio` QEMU shim into the locked QEMU tree, remove
  its Darwin-only build assumptions, and connect its host memory callbacks to the Linux Vulkan
  runtime behind an explicit Kconfig option.

## B003 — macOS 26 restore pipeline is incomplete

- **State:** Open; signed ARM64 iBootStage1 executes under x86_64 QEMU TCG, LocalPolicy accepts,
  signed iBEC validates, the final iBSS `SVC #7` stage switch is reached, and iBEC enters
  iBootStage2 recovery mode. QEMU now has opt-in fixes for the Apple iBoot `SVC #0xa0` PSCI conduit,
  low scratch RAM, USB restore BDIF cfg, pending USB restore receives, USB restore outbound packets,
  and a bidirectional USB restore chardev. The macOS kernel, recovery environment, GUI, and installer
  still do not start yet.
- **Blocker:** The current first blocker has moved past the old null `root` descriptor panic and the
  USB BDIF transport dead ends. iBEC can now reach tethered restore, accept a real host-to-iBEC USB
  restore endpoint event over QEMU chardev, and send guest-to-host response packets back over the
  same channel. The confirmed host-to-iBEC frame shape is
  `uint32_le(payload_len) + endpoint byte + kind byte + payload`; valid iBEC event kinds observed
  before the line-514 guard are 1, 2, and 3. EP0 libirecovery-style control OUT/IN is now also
  proven: a semantic `command:getenv build-version` followed by `control-in:0xff` returns
  `0100 + "mBoot-18000.161.9\0"` from iBEC. What is still missing is the persistent host-side
  restore client/protocol stream that speaks the rest of Apple's tethered restore conversation and
  serves the selected
  BuildManifest assets in the order iBEC expects. Without that client, iBEC stops at the recovery
  command-prompt boundary instead of progressing to restore ramdisk/kernel/installer handoff.
- **Evidence:** The official macOS 26.6 IPSW passes size, SHA-256, ZIP CRC, manifest, build, and
  `VirtualMac2,1` checks. A generated HUFA AuxiliaryStorage header passes AVPBooter's SHA-384 check,
  and the signed iBSS path reaches remote boot. The original failing LocalPolicy ticket contained a
  48-byte BNCH while iBoot's traced comparison required 32 bytes; the first 32 bytes matched. The
  replacement Apple TSS response has an exact 32-byte BNCH and is now executed successfully:
  LocalPolicy outer validation returns accepted, the LocalPolicy handler returns zero, and iBSS
  advances to signed iBEC. iBEC IMG4 validates, BVX2 decompression succeeds after the restore
  workspace maximum is patched from 512 KiB to 2 MiB, and iBEC manifest validation returns zero.
  The normal synthetic restore path originally appeared to fail dispatch because the trace reused
  `0x700c56c8`, a real iBoot instruction address, as a synthetic return sentinel. After moving that
  sentinel to guest RAM at `0x73fff000`, the isolated trace reaches `IBEC_STAGE_SVC7`, finds final
  descriptors, and calls `IBEC_FINAL_HANDOFF_CALLBACK callback=0xaca00000`. The callback dump proves
  `0xaca00000` is the handoff trampoline that disables interrupts, clears memory windows, and
  prepares to enter the stage image. A diagnostic-only GDB shim that injects a minimal descriptor
  confirmed the earlier null-root-descriptor wall, then code inspection showed that the following
  `svc #0xa0` path uses PSCI-style function IDs. Patch
  `0006-vmapple-route-iboot-svc-a0-psci.patch` adds an opt-in filtered SVC conduit for this Apple
  restore path; its VM smoke test executes `svc #0xa0` with `x0=0x84000000` and returns
  `x0=0x10001`. Patch `0007-vmapple-map-iboot-low-scratch.patch` fixes the next low-memory scratch
  crash. Patch `0009-vmapple-report-usb-restore-bdif-cfg.patch` makes the USB BDIF function report
  the `0x1a01` restore cfg iBEC expects. Patches `0011` through `0014` keep restore receives pending
  instead of completing bogus zero packets, add a one-shot first-packet probe, track the USB queue
  selector, and consume iBEC guest-out packets. Patches `0015` and `0016` add the bidirectional
  chardev and prime/read tracing. In the disposable VM, run
  `/home/macvm/runs/aux-26.6/ibec-usb-chardev-in-0202-20260901-061634` connected a Unix chardev,
  sent `000000000202`, logged `chardev-buffered`, `chardev-in`, `guest-out`, and `chardev-out`, and
  the host helper received `0402`. Serial output from the same run shows
  `Microkernel iBootStage2 for vma2`, `aborting autoboot due to tethered restore`, and
  `Entering iBootStage2 recovery mode, starting command prompt`. Later isolated runs refined the
  packet evidence: `ibec-usb-callback-map-20260901-073422` shows the `0202` bootstrap event reaches
  iBEC's endpoint-event callback path at `0x7008d4cc`; `ibec-usb-ep04-kind1-callback-20260901-074013`
  proves endpoint `0x04`, kind `1`, payload `0000000000000800` is delivered intact to the same
  callback and returns `0104`; `ibec-usb-ep04-kind1-kind3-probe-20260901-074205` shows adding a
  kind `3` completion returns `0504` but still does not enter the inner packet dispatcher at
  `0x7009190c` or the type-0/control handler at `0x7008ec60`. `ibec-usb-event-syntax-smoke-20260901-074605`
  validates the helper's new semantic `event:02,2` syntax against the same Stage2 recovery prompt
  and bidirectional BDIF trace. Later code inspection and dynamic endpoint-engine tracing showed
  that the failed `0x02`/`0x04` command attempts were sent to inactive bulk endpoint slots while
  iBEC was still using EP0 control slots `0x00` and `0x80`. Run
  `ibec-usb-control-getenv-semantic-20260901-004752` sends `event:02,2`, then
  `command:getenv build-version`, receives the short EP0 status `0100`, sends
  `control-in:0xff`, and receives `01006d426f6f742d31383030302e3136312e3900`
  (`0100 + "mBoot-18000.161.9\0"`). Unit tests pass at 220/220 and QEMU rebuilds with patches
  0001-0016 in the isolated VM.
- **Source location:** `tools/build_vmapple_aux.py`, `tools/fetch_local_policy.c`,
  `tools/verify_local_policy.py`, `tools/extract_restore_bundle.py`,
  `patches/qemu/0004-vmapple-expose-restore-random-seed.patch`,
  `patches/qemu/0006-vmapple-route-iboot-svc-a0-psci.patch`,
  `patches/qemu/0007-vmapple-map-iboot-low-scratch.patch`,
  `patches/qemu/0009-vmapple-report-usb-restore-bdif-cfg.patch`,
  `patches/qemu/0011-vmapple-keep-usb-restore-bdif-transfers-pending.patch`,
  `patches/qemu/0012-vmapple-add-debug-usb-restore-first-packet.patch`,
  `patches/qemu/0013-vmapple-track-usb-restore-queue-selector.patch`,
  `patches/qemu/0014-vmapple-handle-usb-restore-out-packets.patch`,
  `patches/qemu/0015-vmapple-add-usb-restore-chardev.patch`,
  `patches/qemu/0016-vmapple-prime-usb-restore-chardev-input.patch`, QEMU `hw/vmapple`, and the
  isolated-VM evidence directory.
- **Root cause:** The original direct-IPSW attempt omitted Apple's restore orchestration and boot
  storage contract. The 48-byte ApNonce error, iBEC restore workspace sizing, Apple `SVC #0xa0`
  PSCI conduit, low scratch mapping, USB restore cfg, pending receive behavior, queue selector, and
  guest-out path are now fixed or diagnosed. The current evidence says QEMU's BDIF chardev is
  carrying endpoint events and EP0 control transfers correctly. The latest root cause was host-side
  protocol misuse, not a QEMU CPU/device gap: pre-configuration commands must be sent through EP0
  `0x00`/`0x80`, not bulk endpoints `0x02`/`0x04`. The remaining root cause is not a single missing
  ARM64 CPU instruction seen so far; it is an incomplete host-side restore protocol implementation
  that still needs to model the rest of libirecovery-style control/bulk transfers and serve the
  restore components behind the now-working USB restore chardev.
- **Attempted solution:** Pin QEMU's guest-visible restore random value, build a valid HUFA layout,
  obtain Apple-signed restore tickets for a fixed test identity, and trace LocalPolicy validation
  without changing the validation result. `fetch_local_policy.c` now rejects every ApNonce width
  except 32 bytes to prevent recurrence, and the separate verifier rejects mismatched identity,
  security mode, payload type, nonce, or manifest digest widths. Guest-only QEMU patches add the
  missing restore-boot model pieces listed above without replacing host QEMU or touching production
  configuration. The latest validation proves real socket-backed restore endpoint-event round trips,
  and `tools/usb_restore_session.py` now has validated `event:ENDPOINT,KIND[:PAYLOAD]`,
  `command:...`, `control-in[:LEN]`, and `expect-prefix:...` step forms plus JSONL logging of
  endpoint, kind, and payload length.
- **Latest evidence (2026-09-01):** `tools/usb_restore_session.py` now implements a verified
  `recovery-open` state: configuration returns `0100`, interface 0 returns `0200`, and interface 1
  returns `0100`. A real isolated-VM session then completes buffer-start (`0100`) and the first
  endpoint-`0x04` bulk byte (`0104`) without iBEC panic or chardev write failure. The earlier
  buffer-start panic was incomplete host transport initialization, not a QEMU TCG or device-model
  failure. The suite passes 342/342 after this change.
- **Next experiment:** In the disposable Ubuntu VM only, extend this verified first bulk exchange
  into the full idevicerestore sequence: component upload and command/status exchanges, followed by
  RestoreRamDisk/DeviceTree/KernelCache handoff using the staged BuildManifest-selected
  `VirtualMac2,1` assets. If the next packet exposes another unsupported QEMU Apple VM
  device/register/transport behavior, inspect the relevant QEMU source path, patch the isolated QEMU
  tree, rebuild, and retry. Do not alter TCG validation behavior or production-host resources.
