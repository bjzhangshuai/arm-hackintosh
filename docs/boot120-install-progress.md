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

### Internal-target preflight accepted

The license confirmation alert is visible in screen 37. Its explicit Agree
button was clicked once; screen 38 reaches the real disk-selection page, listing
`macos26`, 137.23 GB total / 137.1 GB available. It is not yet an installed OS.

The target's Update volume is disk5s2, UUID
`189F33BD-FE3A-4D0C-8BDD-9F7E55A61725`, in the exact expected normal APFS
container. UpdateBrain's old restore log records the correct target UUID,
`Found update container`, `Found update volume`, then moves its output to
`/System/Volumes/Data/private/tmp/tmp-mount-S6DjuV/restore.log`. Continuing to
read only the old log would hide subsequent progress. The migrated log records
`SUMacControllerCommandPrerequisiteCheck`, `result = success`,
`targetDriveIsInternal = YES`, and target OS 25G83. This closes the original
B011 missing-container failure, not every later installation requirement.

The read-only target probe verifies both disk identities and the new log.
Long encoded build-manifest/signature lines are omitted from the display; private
raw logs remain in the isolated run and are not published to GitHub. No guest
debugger was attached, VM reset performed, or disk reformatted at this checkpoint.
The prepared license stack sampler was not executed: visible UI progress and the
migrated log made another diagnostic sample unnecessary.

### Installation started, not completed

Screen 39 shows `macos26` selected with Continue enabled. After one explicit
Continue click, screen 40 shows the genuine installation progress page. At guest
08:22:21, `OSISCreateMutableProductOperation` succeeds, then
`OSISDownloadOperation` requests the signed InstallAssistant package (18,384,624,402
bytes) from Apple's CDN. At 08:24:00 the guest's partial file is about 350 MiB;
this is real target-disk activity, not a completed download or installation.
The displayed estimate of about four hours is the installer's estimate only.
The installer holds a PreventUserIdleSystemSleep assertion. QMP remains running
and reports the installation drive's I/O status as `ok`.

The read-only progress probe is `tools/guest-boot120-install-progress.sh`.
It does not reopen the installer, control the UI, modify volumes or restart
anything. The existing reboot-to-shutdown / shutdown-to-pause protection remains
in effect so an automatic installer reboot cannot blindly reuse Recovery scratch.

### Offline-package gap clarified

The previously downloaded local asset still exists:
`/home/macvm/macos-restore/26.6/UniversalMac_26.6_25G72_Restore.ipsw`,
19,772,077,142 bytes. Its firmware and restore/BaseSystem components were reused
to reach Recovery. The IPSW member listing contains disk-image payloads and
restore manifests, not an InstallAssistant.pkg / SharedSupport installer product.
The current Recovery installer selects the different 26.6.2 / 25G83 product.
Its log explicitly says the download cache does not exist and is skipped, then
requests the 18,384,624,402-byte InstallAssistant.pkg. This is not a repeat fetch
of the same IPSW and not evidence that the old download was lost.

The user's requested fully local installation workflow remains **incomplete**.
Only local recovery boot reuse is established. `_registerDownloadCacheProducts`
in the matching OSInstallerSetupInternal checks for the cache directory and
registers recognized package products; it does not treat an arbitrary IPSW as
the requested PKG. A complete local-IPSW restore workflow or a matching local
installer-product cache would need its own implementation/verification. Do not
claim either exists, silently rename the IPSW, replace an open partial file, or
cancel the active installation merely to change routes. This gap should have
been disclosed before the second large download started.

### Follow-up during the long download

The current-task heartbeat `arm-macos` (ARM macOS 安装跟进) was scheduled every five
minutes and was **paused at the user's request on 2026-09-03**. Wait for an explicit
user notification before resuming follow-up. Only scheduled follow-up was paused;
the existing VM and installer were not stopped. The last read-only probe action
was returned to `idle`; no new probe, reboot or installer action was requested.
When authorized to resume, it follows the existing run, preserves production/isolation boundaries,
and does not cancel downloads, repeat UI input, or restart guests on a timer.
Its completion criterion is installed-system login/desktop and ARM64 identity,
not a finished package download. Local scheduled follow-up requires the desktop
application to remain running; the remote VM itself is a separate running process.

### Manual status check: installer failure, 2026-09-03 10:23 UTC

The user has explicitly prohibited automatic follow-up. This was a one-time
read-only status inspection, not a resumption of the paused heartbeat.

The genuine screen `46-progress-20260903-1024.png` now shows: "An error occurred
preparing the update. Failed to personalize the software update. Please try
again." The installer is not complete and no account exists. The error dialog
was not dismissed and no retry, reboot, debugger or runtime change was made.
QMP confirms the original inner QEMU is running, with target I/O `ok`, no failed
reads/writes and no native crash marker. The earlier 52-minute estimate was not
a reliable completion estimate.

New serial output around guest 10:14:25–28 UTC records
`SUMacControllerCommandPreparePackage`, `result = success` and UpdateBrain PID
7514. This establishes later package preparation activity, not the root cause of
the subsequent personalization error. B012 in `BLOCKERS.md` records the evidence,
uncertainty and next bounded diagnostic. Fresh installation/restore error logs
and the matching error-propagation path are still required; do not infer a
specific network, signing-service or QEMU fault from the UI wording alone.

### User-authorized diagnosis and local retry preparation, 10:26–10:55 UTC

The original error was acknowledged once for normal Terminal access. The VM
was not restarted. Exported install/restore logs and the actual crash report
identify an UpdateBrain NULL cleanup defect (B012), not an established network
or signing-service refusal. At 10:14:29 PID 7514 hit `CFRelease(NULL)` in
`-[MSUPrebrain checkAndReissueUCRTAndOICIfNeeded:]`. Reading the missing iSC
SFR ticket returned error 4; the intended skip path nevertheless released its
NULL local at UpdateBrainLibrary file address 0x514f8. Exact image identities,
error propagation and private archive hash are recorded in `BLOCKERS.md`.

The matching 25G83 package had already downloaded successfully. The installer
mounted SharedSupport at 09:33:12 and finished expanding UpdateBundle at
10:14:03, then its normal payload-disposal operation removed the original PKG
and unmounted SharedSupport. A later download operation requested zero packages.
The expanded payload still existed; it was not necessary to fetch 18.4 GB again.

Before any retry, `/Volumes/macos26/macvm-offline-25G83-boot120` was created
as an APFS clone of the expanded payload: **2,233 regular files,
19,202,615,016 bytes**. Source and clone path/size listings match, with matching
key metadata checks and a `CLONE_COMPLETE` marker. The clone retains BuildManifest,
Apple signatures/BOM, ARM64e BaseSystem/Cryptex and VMA2MACOSAP support metadata.
It shares the same target volume and is **not** an independent-disk backup.
The metadata states macOS 26.6.2 / 25G83; the old 25G72 IPSW remains a different
recovery/restore product.

The pure NULL-cleanup planner has 19 passing isolated-Linux tests. Its one-shot
adapter checks the exact live task, stack, saved signed return address, image
UUIDs and full caller instructions before permitting only PC to CFRelease's
own authenticated epilogue. No Apple text, tickets or signature decisions are
rewritten. A read-only live check passed at 10:45 UTC and detached; no actual
cleanup repair has been applied yet. Seven local-routing metadata tests and
five evidence-receiver tests bring this turn's focused gate to **31 passed**.
No tests or builds ran on the production Mac or physical Linux host.

The initial source review suggested a static-directory local product route:
`OSISMobileSoftwareUpdateProduct._setDefaultDestinationPaths` selects
`UpdateBundle-Static` / `UpdateBrain-Static` with `IASkipUnarchivingMSU`.
The unarchive operation still checks that directories exist and builds a normal
MSU product; normal package/content/signature/personalization checks remain.
The helper derives SharedSupport from its own installer app bundle, so a new
local copy is being assembled with a separate working clone, the previously
downloaded UpdateBrain archive and routing metadata copied from the real asset.
Only the isolated Linux server is used to transfer these small local inputs.
Preparation must pass normal code-signature verification before activation;
it does not itself launch another installation. **The Recovery branch invalidates
this initial route assumption; see the complete-control-flow correction below.**
No force-success defaults,
remote OS package download, account creation or installed-system success is claimed.

### Local product prepared; first local UI launch issued

Preparation initially stopped at the relocated app bundle's `codesign --verify
--deep`: `resource envelope is obsolete (custom omit rules)`. Read-only comparison
established the original bundle passes; both bundles contain identical custom
omit rules and identical executable/Info/CodeResources bytes. The relocated
secondary `InstallAssistant` executable verifies normally. No signature was
removed/replaced and no validator option/security preference was weakened.

The finalizer then verified the original bundle, compared **all 694 regular
files / 37,676,296 bytes**, modes and symlink targets, allowing only the explicit
new SharedSupport symlink. The actual InstallAssistant executable, helper and
UpdateBrain XPC passed normal signature verification. Six comparator regression
tests pass in isolated Linux (focused total **37**). The helper's exact `init`
code calls `addSuiteNamed:` for `com.apple.InstallAssistant`; that common suite's
prior IASkipUnarchivingMSU state was saved before selecting static directories.
`PREPARED_LOCAL_ONLY` was written; the source payload clone remains untouched.

One launch of the unchanged, normally verified secondary InstallAssistant was
issued, PID 8206. No target/Continue action has yet been issued in this local
attempt. The B012 adapter is armed for at most one exact cleanup correction with
a 20-minute SIGINT deadline and detach cleanup. It has not yet reported a repair.
Actual local product selection, absence of a new remote OS payload request and
preflight advancement still require live evidence. Network personalization may
still require small Apple service exchanges; local payload reuse is not a claim
of a completely air-gapped installation.

### Local UI startup result and complete Recovery path correction

The first local UI launch did not reach a target-selection/installation action.
Helper PID 8213 found our local asset XML and UpdateBrain.zip, extracted the
brain successfully, then failed to start it: `setup_role_account` EFTYPE 79,
MSU 27 / SUMacController 7721. This recurs before B012 and matches the established
B010 staging failure after the temporary metadata compatibility bridge expired.
The retained staging anchor, exec and tmp directories still have `restricted`;
the missing requested tmpfs extended-attribute response still matters. The
helper exited normally, and a later process inventory found no InstallAssistant,
UpdateBrain or helper. No agent killed/restarted the installer or VM.

The initial static-directory source reading was incomplete. Full function
0x7464–0x784c shows `getenv(__OSINSTALL_ENVIRONMENT)` at 0x7560 takes the Recovery
branch *before* the IASkipUnarchivingMSU query at 0x7660; Recovery sets its brain
path under /tmp and its destination under the mutable product. The static branch
also derives paths from safeTemporaryDirectory, not SharedSupport. Therefore
the initially staged `*-Static` directories are not a verified Recovery route.
Do not clear the Recovery environment marker or force a successful unarchive.

Instead, `guest-pack-boot120-local-payload.sh` is repackaging the master clone
into a normal local UpdateBundle.zip, initially using the existing ditto writer
with compression level zero and preserved resource metadata. The result is
**not** claimed to be Apple's original ZIP bitstream; embedded payload, manifest
and signature files are unchanged and later normal Apple validation must pass.
It writes a new `.partial`, performs a full unzip CRC test, then promotes the
archive and restores only the unused preference set by this task. No CDN is
used to build it, and the master clone is not overwritten.

The unused standalone B012 debugger was interrupted by exact PID/command/opt-in
checks, removed its breakpoint and detached with `repaired=False`; QMP remained
running, target I/O ok, zero failed reads/writes. One combined session is now
prepared to cover the unchanged B010 create/getattr contracts and one B012 NULL
cleanup. The bridge verifies the live protected anchor again before installing
mutators and disables existing-bundle relabelling. It has one continue, existing
observation limits and cleanup on error/SIGINT. **67 focused tests pass** in the
isolated Linux VM. This is prepared code, not proof of a successful repair or
installation. No recurring automation was created or resumed.

### ZIP64 preparation and validation, guest 11:16–11:22 UTC

The first repackaging command's output was **not a valid large ZIP**. Although
the file is 19,204,730,974 bytes, its legacy EOCD records central-directory
offset 2,024,544,885; the real central directory starts at 19,204,414,069. The
difference is exactly 17,179,869,184 (four 32-bit wraps). Neither ZIP64 EOCD nor
ZIP64 locator exists. A real member is 4,456,630,130 bytes, so individual sizes
also require ZIP64. Recovery's unzip explicitly supports ZIP64; this is not
just a missing feature in the checker. The retired BOM/ditto workflow now refuses
execution and the invalid output was preserved as
`/Volumes/macos26/macvm-rejected-bom-archive-25G83.zip`. Only its identified CRC
test PID 8357 was stopped; no installer/VM was stopped and no archive was deleted.

The existing guest tool reports bsdtar 3.5.3 / **libarchive 3.7.4**. Its
[upstream ZIP writer](https://github.com/libarchive/libarchive/blob/v3.7.4/libarchive/archive_write_set_format_zip.c)
has explicit ZIP64 entry offsets/sizes and ZIP64 end records. A tiny fixture using
`zip:zip64=1,zip:compression=store` passed unzip CRC and footer/locator checks.
A separate ditto read probe failed; the subsequent exact installer code review
establishes that ditto is **not its reader**: `OSISStreamingZipExtractor`
0x2333c unconditionally calls `_unzipViaLibarchiveWithError:`, using the archive
read APIs, not BOM. A matching libarchive extraction of the fixture then passed
and its Info.plist matched the original. This corrected the earlier mistaken
reader assumption before a second full archive was generated.

`guest-pack-boot120-zip64.sh resume-after-reader-check` now runs the full local
ZIP64/store archive build, followed by complete CRC verification. It neither
overwrites the retained payload nor fetches another system package. The prior
standalone cleanup debugger is detached, and combined B010/B012 **read-only live
contract verification passed**, including the exact protected staging anchor.
The actual combined correction and successful installer preflight remain pending.

An additional exact-length, one-shot local transfer endpoint is prepared to
retain a verified archive outside the inner APFS installation target, within
the isolated Linux data filesystem. It is not a GitHub upload and has not yet
received a payload. Its five new policy tests pass; prior evidence endpoints
retain their original 64 MiB limits. No automatic monitoring is involved.

The read-only local ZIP64 validator additionally rejects missing/wrapped end
records, out-of-bounds locators, trailing bytes, duplicate/unsafe paths,
inventory/Info.plist mismatches and CRC failures. Ten small regression cases pass;
the focused isolated-Linux total is **82 tests**. These are packaging/adapter
tests, not proof of an installed OS or Apple signature acceptance. The full ZIP64
archive was still growing at the latest guest 11:29 observation (16,420,915,200
bytes); no archive-backed installer launch or B012 live correction has occurred.

The writer subsequently completed at **19,203,380,932 bytes**. The guest's
single full CRC test is running (unzip PID 8673, parent packer 8506), and the
archive is still `.zip64.partial` until this check passes. QMP at 11:31:27 UTC
reports running, target I/O ok, zero failed reads/writes and no native crash.
A one-shot exact-length backup receiver is now listening on isolated Linux
loopback 18567; no upload/backup-completion claim follows from that listener.

The backup now overlaps the still-running guest CRC test. The candidate export
requires the exact closed archive size, the observed read-only unzip PID 8673
and parent 8506, and a stable device/inode/size/mtime across upload (allowing only
the packer's atomic rename of that same inode after CRC). The receiver remains
exclusive-create and exact-length. A received candidate is **not** an accepted
installer archive: guest CRC/promotion and full native Linux ZIP64/CRC/inventory
validation are still required. This changes no payload content and causes no
remote OS download. The current local copy is incomplete; don't claim backup
success from its existence.

The subsequent explicit guest status check observes `UpdateBundle.zip`
(19,203,380,932 bytes) and `LOCAL_ARCHIVE_READY` (29 bytes), with no `.partial`
or active unzip. The served `b012-z64-v2.sh` and the recorded packer match SHA-256
4472eaf44cf366bd9acac66108612d6a698b2f71b26714275a9793756820d88d;
that path only promotes the file and writes the marker after full CRC succeeds
and the unused static-unarchive preference is restored. A complete-log search
also confirms the explicit full-archive "No errors detected" message,
`MACVM_BOOT120_ZIP64_ARCHIVE_CRC_VALID` and `MACVM_BOOT120_ZIP64_PACK_END`.
The Linux copy remains incomplete and its native inventory/CRC check is pending.

A preparatory launcher-script fetch lost the first typed `c` under the loaded
VNC session (`url: command not found`, observed screenshot 76). It did **not**
launch an installer. The input is being re-staged with explicit line clearing,
a pause and a harmless leading space; actual launch remains gated on validated
assets and the combined compatibility session.

The explicit archive preflight at guest 11:55:16 UTC confirms: the static
preference is absent again; staging anchor/exec/tmp and the one retained exec
child already have `restricted`; tmp contains no stale child; no InstallAssistant,
UpdateBrain, helper or unzip remains. Only the deliberate local-copy curl runs.
The staged `/tmp/l2` launcher MD5 is 6bb68b9e3b6f22b7d464f5263bc40c1c, matching
the repository script. These checks do not claim B010's missing getattr response
is fixed; the combined session is still needed for the upcoming launch.

`guest-clean-boot120-rejected-archive.sh` is prepared but **not executed**. After
both replacement CRC and the exact Linux backup/native validation report pass,
it will preserve the rejected ZIP's prefix/central-directory/footer and remove
only the identified task-generated 19,204,730,974-byte invalid archive. All source
assets, the valid archive and the Linux copy remain. Its Linux syntax and
outside-ARM refusal check pass; it never touched the current guest's files.

### Pre-launch debugger lifetime correction

Read-only review of the old live `tmpfs-metadata-compat.log` found an actual
normal limit stop: create=132, existing=2, extflags=8710, observed=100001. The
initial combined script would have removed **both** guards at that point, before
the later B012 cleanup. This was corrected before launching any new installer:
metadata records an explicit limit/error reason; only a normal metadata limit
retires its own breakpoints and permits one further continue with the one-shot
NULL guard retained. Any metadata contract error, unknown stop, SIGINT or actual
NULL correction ends the session and detaches as before. No budget is enlarged
and existing-bundle relabelling stays disabled. Five new lifetime regression
cases pass; the focused isolated-Linux suite now has **87 passing tests**.
