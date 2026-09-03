# Boot120 — internal installation target continuation

## Scope and current status

The user approved one planned inner ARM VM shutdown/restart after backup. The
outer Linux isolation VM, its NBD mount and all production host resources stay
running and unchanged. No OS installation or account creation is complete yet.

Boot119 shut down normally through `/sbin/shutdown -h now`. Its serial log shows
APFS unmount completion, CPU halt, NVRAM sync and ApplePSCI system off. QMP reported
`shutdown`, `running=false`; only then was QMP `quit` sent. QEMU exited with code
0 and its native crash watcher exited naturally. No forced process termination.

## Private backups

Inside isolated Linux only:
`/home/macvm/installation-data/boot119-before-internal-20260903`

- Volatile guest install/system/restore logs and crash reports were exported
  before shutdown. Archive SHA256:
  `4440ec31995e92ae7f5329bd97caa45674d6ad26580d5c7c53045918c15af5a2`.
- Live evidence/config/source and previously validated QEMU/runtime archives.
- Offline run directory, including AUX/iSC, root/USB scratch and Recovery overlay.
- Offline copies of the 128 GiB installation image and 1 GiB diagnostic image.
- Flattened Recovery backup (`offline/recovery-preserved.raw`), avoiding reliance
  on a writable old overlay in the next run.
- Exact firmware, signed recovery components, BaseSystem ramdisk/auth/trustcache
  inputs in `restore-inputs`; never publish these private Apple inputs or tickets.
- `qemu-img compare` reports identical installation/diagnostic/Recovery contents;
  AUX/root/USB copies pass `cmp`; disk and restore-input SHA256 manifests pass.
- Completion markers: `ONLINE_EVIDENCE_COMPLETE`, `OFFLINE_DISKS_COMPLETE`,
  `RESTORE_INPUTS_COMPLETE`. This is **not a running-RAM snapshot**. The old
  temporary metadata bridge and all RAM-only state must be re-established safely.

An earlier partial evidence directory ending `-incomplete-permission` is retained
separately, not presented as a completed backup. A root-owned perf capture caused
the initial read failure; only its backup copy was given readable ownership.
The source file and its permissions were not altered.

## One planned configuration change

Launcher: `scripts/validation-boot120.sh`. New run directory:
`/home/macvm/runs/aux-26.6/xnu-imgsrc-reims-boot120-internal-install`.

- Same QEMU executable/build as Boot119; SHA256
  `bfedb312ba18bcaeed2ca67f449575295eb42c2a986308676e7ab17e809ce411`.
- 8 vCPU, 16 GiB, x86_64 TCG; VNC loopback 6019, guest GDB loopback 12355.
- Existing `/home/macvm/installation-data/macos-26-system.raw` now uses internal
  `vmapple-virtio-blk-pci,variant=root` as drive ID `macvm-install-internal`.
  The QMP block node name is auto-generated, not this drive ID.
  No reformat, resize, clone replacement or guest UUID change.
- A separate explicit opt-in leaves the old read-only BaseSystem root mode intact.
  The identity gate checks the approved mount UUID, exact image path/capacity,
  primary/backup GPT checksums/geometry and normal APFS container UUID/checksum.
- AUX/iSC is copied into the new run from the completed offline backup; Recovery
  uses a new overlay backed by the preserved raw backup. Old Boot119 files stay
  intact. GDB runtime dump/read paths are also scoped into the new run.
- `reboot=shutdown,shutdown=pause` retains any future installer reboot boundary.
  Firmware pflash root remains Recovery scratch: an installed-system boot launcher
  is still unverified and must be prepared before resuming an installer reboot.
- The old USB diagnostic image is preserved but not attached in this boot.

Tests ran only in isolated Linux: 20 target/continuation contract tests and 35
existing restore-runner tests pass; the 16 existing tmpfs contract tests also
pass. This is 71 tests, not proof of installed-system boot or GUI correctness.

## Live checkpoint

QEMU PID at startup: 974460. Original non-root native watcher could not attach
under the existing isolated VM ptrace policy; it exited without changing policy
or VM state. A root native watcher was then attached inside isolation with output
`native-watch-root.log`. No host ptrace settings changed.

The boot passes signed iBSS/LocalPolicy/iBEC and reaches ARM64 XNU/Recovery. Both
`HELPER_RC` and `POST_GDB_RC` are 0. The bootstrap guest debugger detaches at the
known PackagesLink result boundary. The genuine GUI initially presents Boot
Picker (Recovery and Options), rather than the previous template's direct
language picker. Options was selected and Continue clicked once. At guest
07:22:54 the agent launches Language Chooser; Boot Picker exits normally with
status 0. This is an in-guest application transition, not another VM restart.
Screens 02–04 preserve that transition.

Next: establish the fixed-enum controller, independently
observe this boot's protected tmpfs staging anchor, then reuse the exact-image
metadata compatibility contract before the first UpdateBrain preflight. Never
reuse Boot119's old vnode address or claim that disk backup preserved it.

The new Boot120 observer and identity gate are prepared but not yet run live.
The bridge refuses an old PID, wrong slide, unprotected anchor, unexpected path,
missing read-only provenance, or non-kernel/unaligned pointers. The five added
identity tests pass alongside all sixteen existing tmpfs tests, in isolated Linux.

### Recovery GUI and diagnostic-pause correction

Language selection eventually advances to the genuine macOS Recovery window
(`13-recovery-progress.png`), showing "Examining volumes…". Recovery Springboard
and KeyRecoveryAssistant are present in the serial log. The controller has not
yet been started in this boot; guest-visible internal-target identity and the
new installer preflight remain unverified.

One read-only guest GDB connection failed its RSP handshake at 07:31 UTC and
left QEMU paused. This was a diagnostic-tool failure, not a guest crash. Source
inspection confirms `gdb_chr_event(CHR_EVENT_OPENED)` stops the system, while
ordinary `handle_detach` resumes it. After verifying the exact QEMU PID and that
the failed client had exited, one QMP `cont` restored `running=true` at 07:34 UTC.
Evidence: `diagnostic-handshake-resume.json`. No reset, quit or new boot occurred.
The diagnostic scripts now set a 30-second RSP timeout. Every subsequent guest
debugger invocation must check QMP state on exit, including failures; a shutdown,
I/O error or unrelated pause must never be blindly resumed.

A 10-second perf capture taken during that diagnostic pause has only 24 samples
and is **not a valid performance result**. Vulkan fence-timeout messages remain
separate renderer evidence, not proof that this GUI transition was deadlocked.

Recovery's volume examination completed, and the main Recovery utilities screen
is visible in screen 15. Terminal PID 339 subsequently starts after the documented
Shift-Command-T shortcut; no repeated application launch was requested. Screen
rendering is delayed, so serial evidence and the visible prompt must both be
checked before typing commands. A later 15-second `cpu-clock` sample while
running has 717 samples, no lost samples, predominantly TCG CPU threads. This is
a startup diagnostic, not a comparative benchmark or proof about installer speed.

Current storage checkpoint: `configs/boot120-install-storage.json`. The data
mount UUID was rechecked in isolated Linux; 190 GiB is available. No target
reformat or additional guest reboot has occurred.

### Guest-visible internal target verified

The fixed-enum controller is running from the genuine Recovery Terminal. Its
read-only probe records `RELEASE_ARM64_VMAPPLE arm64`, macOS 26.6 / 25G72.
`diskutil` now confirms the unchanged target UUID
`31209BA2-BC1F-4D51-99C1-4AFF986CB8AA` as internal `disk5s1` on physical store
`disk0s2`, with owners enabled, read-write APFS and "OS Can Be Installed: Yes".
Physical disk0 is the normal 128 GiB target; disk1 is Recovery, disk2 is iSC.
IOKit reports Internal / EmbeddedDeviceTypeRoot=Yes. This verifies the intended
topology correction, **not yet UpdateBrain preflight success**.

The protected role-account staging root exists with `restricted` flags; its
`exec` and `tmp` children do not exist yet in this fresh boot. The probe's end
marker is completion of inspection, not a claim that those children exist.
The next separate read-only anchor observation must bind the bridge to this
boot's vnode/node; the Boot119 identity remains unusable.

The read-only observer then captured the exact protected anchor after 3,976
observations, wrote `tmpfs-staging-anchor.json` and detached successfully. QMP
reported `running=true` afterward. The Boot120-verified metadata bridge is now
armed with existing-directory repair and read-only storage-class tracing enabled.
It retains the previously tested instruction/layout and protected-subtree guards;
no security-decision or signature patch was added. The first Boot120 installer
launch creates InstallAssistant PID 703. Its Continue/preflight result is pending.

Screen 28 shows the genuine Tahoe installer welcome; Continue was clicked once
and screen 29 shows "Loading Installation Information…". osinstallersetupd PID
734 evaluates the 642-product catalog. The `cpuFeatures.split` package-script
messages also appear in Boot119's preserved log before its successful 25G83
selection; they are not a reason to change CPU configuration or restart here.

One 3-second, 20 ms interval in-guest `sample` was collected for PID 734 and
symbolicated. Only three samples per thread were actually obtained, so it is
not a reliable performance distribution. The active DistributionKit script
evaluation queue was enumerating IORegistry objects through JavaScriptCore;
the other product workers were waiting for that serial queue. The same existing
sample's remainder was read back, not resampled. Evidence is retained in
`catalog-sample-evidence.log` and `/private/tmp/macvm-boot120-catalog.sample`.
The process subsequently advances to UpdateBrain staging without intervention.
The actual role daemon reports `RoleAccountStaging`, class `0f`, errno 0 using
the new anchor; UpdateBrain PID 1232 enters startup. Target preflight remains
pending, and no completed installation or local account is claimed.

The current four Python regression modules were rerun together **inside isolated
Linux only**: 76 tests pass (tmpfs semantics, boot identity, target identity and
restore-runner contracts). The new guest shell probes pass `bash -n` there.
This does not constitute an installed-system boot test.

UpdateBrain PID 1232 subsequently reaches launchd `running`. The temporary
metadata bridge reaches its observation budget and detaches normally with
132 newly created objects receiving the requested protection bit, two existing
directory repairs and 8,710 absent extended-flag responses. QMP confirms
`running=true` after detach. The new staged bundle is `872415233.3794.xpc`;
the old Boot119 bundle name was not reused as the new launch target. No guest
debugger remains attached at this checkpoint. Do not reattach one implicitly.

At guest 08:03:29, wakeup reaches **100%**, and the current installer selects
**macOS 26.6.2, build 25G83**. At 08:03:31 it reports **Device is supported**,
then resolves the bundled license document. This is actual B010 launch/preflight
progress in Boot120, not merely an xpcproxy spawn. Disk selection and the B011
target-system-volume preflight still require their own acceptance evidence.
