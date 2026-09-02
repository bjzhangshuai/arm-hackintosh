# Blockers

## Current validation status — 2026-09-02, Boot116 started after crash reproduction/fix

- ARM64 XNU 25.6.0 (`RELEASE_ARM64_VMAPPLE`) and macOS BaseSystem 26.6 build 25G72
  boot and pivot to the recovery root. The old B003 pre-kernel notes below are historical.
- Boot115 reaches `Aqua session established.` and launches RecoveryOS Agent and Boot Picker.
  A genuine QMP capture now shows the Recovery volume icon, keyboard menu, Shut Down and
  Restart controls. This is the startup selector, **not yet the installer**.
- Selecting Options and Continue succeeds: Boot Picker exits with status 0 and
  RecoveryOS Agent launches Language Chooser and launchprogresswindow. QEMU then
  exits with SIGSEGV (139) at approximately 26m53s, before a language-screen capture.
  It was not manually stopped. See B009; no installer completion is claimed.
- The Linux PVG/Vulkan bridge produces actual visible UI on a software renderer. This
  supersedes the initial black screen and B002's missing-backend status, but is **not**
  hardware acceleration or a performance result. The same boot was retained throughout.
- Build, tests, GDB, package installation and execution remain inside `macvm-validation`.
  The production Mac and production hypervisor are not test environments.
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
  separate QEMU binary before a new full boot. Keep Boot115 artifacts and old binary intact.
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
