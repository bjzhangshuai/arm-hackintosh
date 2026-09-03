# Boot119 installation progress — 2026-09-03

## Current boundary

The user requested completion of the installation and creation of local account
`jansurezhang`. The password remains out of repository files and logs.

The installer welcome **Continue** button was initially clicked once. It showed
**Loading Installation Information…**, then a generic content-download alert.
One post-metadata-correction attempt at 04:38 UTC also failed before target
selection. The subsequent source-corrected preflight succeeded: UpdateBrain runs,
wakeup reaches 100%, and the installer selects Tahoe 26.6.2 / 25G83. The license
page and confirmation sheet are genuinely displayed. The approved new blank
disk has been formatted (see below), but no OS installation has started and no
account has been created. Completed installation and installed-system boot are
not yet proven. The current boundary is target-volume preflight: genuine screen
`68-target-check.png` shows `macos26` selected but Continue disabled, with tooltip
"Unable to set target system volume for preflight". System.log records
MobileSoftwareUpdateErrorDomain / MSU_ERR_MISSING_TARGET (42), first at guest
06:21:57. `diskutil` still confirms the exact expected UUID, writable APFS,
owners enabled, ~137.1 GB free and only 24 KiB used. Do not erase/reformat or
repeat installer startup based on this tooltip. See B011 in `BLOCKERS.md`.

### Target storage root cause (06:55 UTC)

The exact UpdateBrain log is
`/System/Volumes/Data/MobileSoftwareUpdate/restore.log`. It receives the correct
target UUID but reports **Failed to locate update container for target**.
The matching, unmodified ARM64e UpdateBrainLibrary (2422.160.6,
UUID `8BB113CF-7583-3554-82B4-B4C009A16A16`) implements this decision in
`-[MSUTargetController setSystemTargetUUID:timeout:]` (file address `0xe7e4`).
An external target plus an embedded root device selects the primary internal
medium and requires a normal APFS physical store (role 0). Neither an iSC nor a
Recovery physical store qualifies. The failure branch is at `0xed98`, before
`configureUpdateVolumeWithReserve:andErase:withError:`. This is not evidence that
the existing target UUID is wrong or that its filesystem needs reformatting.

Read-only guest inventory (`MACVM_INSTALL_TOPOLOGY_BEGIN`, 06:55:56 UTC) confirms:

- Both AppleVirtIODiskStorageDevice instances report `EmbeddedDeviceTypeRoot=Yes`
  and `Physical Interconnect Location=Internal`.
- disk0 contains only `Apple_APFS_Recovery`; disk1 contains only `Apple_APFS_ISC`.
- The actual 128 GiB target is disk6, **external USB**, with a normal APFS store.
- Its APFS container UUID is `6C0D6E74-EBBB-4A40-A7F1-AFDE0A1B34FD`.

Proposed bounded correction: attach the **same existing installation image**
through the internal Apple virtio root interface on the next planned inner boot.
Preserve the AUX/iSC and Recovery state; do not erase any disk. A new run directory
and a consistent offline disk/configuration backup are required. Disk backups do
not preserve running RAM or the temporary tmpfs bridge. Guest shutdown/restart
approval was subsequently granted. That sequence is now complete: volatile logs
were exported, Boot119 shut down normally, offline disk/configuration/restore
inputs were backed up and verified, and Boot120 started once with the existing
target attached internally. See `docs/boot120-install-progress.md` for the live
checkpoint. The outer isolation VM and production resources were not restarted
or changed. Boot119's final preflight evidence above remains historical evidence,
not the current running process state.

Local evidence directory:

`artifacts/boot119/install-20260903032545/`

- `00-before.png`: installer welcome before Continue.
- `01-continue.png`: loading installation information after the click.
- `02-info.png`: subsequent state, still loading installation information.
- `03-info-later.png`: actual alert: "Installation of macOS could not continue.
  Installation requires downloading important content. That content can't be
  downloaded at this time. Try again later."
- `04-error-ack.png`: the alert after sending one OK click; UI response is delayed.

The corresponding original PPM files are retained locally and in the Boot119 run
directory inside the isolated Linux VM. The PNGs are format conversions, not
edited content.

### Failure evidence, not a network retry

The guest `/var/log/install.log` records successful metadata/UpdateBrain download
at 03:29:35 UTC and successful extraction at 03:29:45. Brain startup then fails
with SUMacControllerError 7721 / MSU 27. The matching ARM64 crash report records
`CODESIGNING`, code 4, `Launch Constraint Violation`, rather than an instruction
exception. AMFI's `c[4]p[1]m[1]e[0]` identifies a failing self launch constraint.

The unmodified staged service's Apple signature was inspected in Recovery with
`codesign -d -vvvv`. Its self constraint requires `is-sip-protected=true` and
`validation-category=1`. AMFI reports category 1, but `ls -lO` shows no restricted
flag on the executable under the roleaccountd staging directory, which resides
on Recovery's tmpfs Data mount. The missing SIP-protected location is the current
mismatch; the directory initialization/flag inheritance cause is still being
checked. No signature replacement, constraint stripping, or global security
disable has been applied.

The matching tmpfs code subsequently established that its creation path omits
`va_flags`; XNU's generic fallback handles ACL metadata, not these flags. The
normal guest `chflags` path denied an attempted protection-bit addition to one
new, empty probe file. Probe directory retained in Recovery RAM:
`/private/var/db/com.apple.xpc.roleaccountd.staging/exec/macvm-flags-probe.GpA0fm`.
The probe did not modify an existing service.

A temporary GDB **metadata** compatibility bridge was implemented with explicit
Boot119 opt-in, exact instruction/layout checks, a protected ancestry check and
a narrow existing-cache allowlist. It adds only `SF_RESTRICTED`, preserving all
other flags and all Apple security checks. New objects must already request the
bit and have a protected parent. This is installation validation scaffolding,
**not a permanent filesystem fix or production deployment**. Its 11 contract
tests pass in isolated Linux; Python and shell syntax checks also pass there.

Live bridge log: `tmpfs-flags-compat-v2.log` in the Boot119 run directory.
Use `gdb-multiarch`, not native x86 GDB (the initial native invocation exited
before connecting). The bridge's `finally` block deletes its breakpoints and
detaches on exit; do not terminate the separate native QEMU crash watcher.
The first bridge session was detached with **zero metadata changes** after
confirming debugger-induced keyboard loss. A bounded enum-only HTTP control
helper was then delivered into Recovery before reattaching, avoiding live typing
under broad diagnostic breakpoints. The production hosts were not involved.

The live bridge now uses `tmpfs-flags-compat-v3.log`. It verified and repaired
**134 known staging/cache objects**. Guest `codesign --verify --strict` passed
both before and after the refresh (`valid on disk`, designated requirement
satisfied). `MACVM_TMPFS_EXISTING_REPAIR_DONE` closed the broad getattr repair
phase; only the narrow new-file inheritance bridge remains. This is evidence of
metadata correction, **not successful UpdateBrain startup**.

### Single post-correction attempt and new evidence

The reopened installer (PID 6400, osinstallersetupd PID 6426) received one Continue
click at 04:38 UTC. Product 140-93587 was selected; metadata and UpdateBrain
download completed at 04:41:12, extraction at 04:41:17. The generic alert returned
at 04:41:45 with the same outer SUMacController 7721 / MSU 27 error.

Crucially, the lower-level failure is now **xpcproxy initialization**, not a new
AMFI launch-constraint crash: `setup_role_account` returns **EFTYPE (79)** at
04:41:30 and 04:41:42 (PIDs 7004, 7017). No new UpdateBrain crash report appeared.
`xpcroleaccountd` PID 5583 is still alive. Its actual matching code returns this
error from multiple bundle/copy/signature/Info.plist failure paths; the exact
branch is not yet established. The signature of the newly extracted source
bundle at `/private/tmp/UpdateBrain-2WgUlaMr/AssetData/` passes strict verification.
The protected staging `tmp` is empty; the old known staged bundle remains.
Do not claim the previous metadata correction passed a launch test.

The live v3 bridge was then detached cleanly at about 04:45 UTC, leaving the VM
running. Final counters: **existing=134, create=0, observed=8266**. New-object
inheritance is therefore **not live-validated**. The separate native QEMU crash
watcher remains untouched. The enum control helper was interrupted in its own
Terminal foreground; it is not running at this checkpoint. The loopback HTTP
server remains available for reviewed read-only diagnostic scripts.

Recovery excludes `logd` via its `HasFullLogging` variant. `log show` reports no
local log-store connection; no production logging service has been changed.
Read-only matching `xpcroleaccountd` / `xpcproxy` code and process state are being
used to localize error 79 before any further installer retry.

Additional read-only checks: the new source bundle also satisfies the exact
Apple-anchor + `com.apple.private.xpc.role-account` requirement used by the
matching role-account daemon. Its XPCService has `_RoleAccount=root`, an
`_AllowedClients` array and `ServiceType=Application`; no source symlink was
reported. The staging root's `com.apple.rootless` xattr is `RoleAccountStaging`.
The initial CLI requirement check omitted codesign's literal `=` prefix and was
invalid; the corrected check in `guest-role-launch-state.sh` explicitly passes.

The read-only `sample` tool identifies the live daemon as ARM64E, PID 5583,
base `0x102d60000`, UUID `863A20EC-1739-3237-9D85-E5BD71A4C904`. A bounded,
observe-only breakpoint script verifies that UUID and exact instructions, then
records copy, signature, Info.plist and error-reply branches. It removes all
breakpoints and detaches on its first error reply. The failed softwareupdated
PID domain no longer contains the UpdateBrain service, so it cannot be directly
kickstarted. The failed installer was acknowledged and reopened once, with this
observer armed, to collect a precise failure branch rather than guess a fix.
The first observer (`roleaccount-stage-trace-v1.log`) detached with zero
observations after a signed-address conversion error. Its read helper was fixed
to mask GDB's high addresses to uint64. The v2 observer then captured the first
error at 05:03 UTC and detached normally: cache absent, `copyfile=0`, static-code
object null, signed Info.plist result null, errno 79. The signature requirement
and signing-information calls were **not reached**. This rules out a requirement
mismatch at this particular failure, but does not establish why object creation
failed. The installer's three automatic attempts ended at 05:03:35 UTC.

The v3 read-only observer adds the input path, CFURL creation result, and raw
`SecStaticCodeCreateWithPath` result. It was armed after the automatic attempts
finished and initially had zero hits. A single targeted follow-up is planned to
capture that missing evidence; no VM restart occurred. The foreground enum
control helper has been resumed. The metadata bridge remains detached.

### Missing staged directory established (05:18 UTC)

The single follow-up installer instance is PID 8347 / setup daemon 8384. Its
catalog evaluation took several minutes; it was not interrupted. Observers v3
and v4 were each detached with zero hits during that evaluation to add copy-error
callback capture and correct the observation limit (normal progress callbacks
must not consume the error budget). The v5 read-only observer captured 185
meaningful observations and detached at the first error reply. No VM was stopped
or restarted.

The new source was `UpdateBrain-8U3B9PWJ/AssetData/...UpdateBrainService.xpc`.
First copy error was for creation/copy of the staging root itself:
`/private/var/db/com.apple.xpc.roleaccountd.staging/tmp/8A431C49-83E9-4B9E-AFC4-361DF9A89974`.
Directory, file and directory-cleanup callbacks then reported errors throughout
the tree, including the executable and Info.plist. The daemon's callback ignores
`COPYFILE_ERR` (3) and returns continue, so the recursive copy still returns 0.
CFURL creation succeeds. `SecStaticCodeCreateWithPath` returns **-67068**,
`errSecCSStaticCodeNotFound`, not a signature-requirement rejection or invalid
signature. This explains the later null object and EFTYPE reply. It does not yet
establish the errno of the first directory creation failure. Keep that boundary
explicit; do not call the zero copy return a verified successful copy.

Reference: Apple's [Code Signing status definitions](https://github.com/apple-oss-distributions/Security/blob/main/OSX/libsecurity_codesigning/lib/CSCommon.h)
and [recursive copy callback handling](https://github.com/apple-oss-distributions/copyfile/blob/main/copyfile.c).
The next experiment is filesystem-level evidence rather than another complete
installer attempt. Both the metadata bridge and guest role-account observer are
detached. The enum control helper was told `stop` to return its Terminal prompt;
the HTTP server remains available. This stops only that helper, not either VM.

### tmpfs storage-class contract (05:24–05:34 UTC)

Guest filesystem evidence rules out capacity exhaustion: Recovery Data tmpfs is
2.5 GiB, 161 MiB used, about 2.3 GiB free. `macos26` remains empty at 24 KiB used.
The ordinary new-directory probe succeeds; a root-shell probe under the protected
staging `tmp` is denied with EPERM. That shell does not have the daemon's
entitlements, so its errno alone is not evidence of the daemon's errno.

Read-only matching Sandbox code and a targeted mktemp observation then establish
a deeper contract mismatch. `_rootless_get_storage_class` reads the protected
`tmp` directory (flags 0x80000), gets ENOATTR (93), and obtains its parent vnode.
The parent `vnode_getattr` succeeds but returns supported mask **0x1600450** for
requested mask **0x200000000400**. The missing bit is `va_extflags` (bit 45).
The matching tmpfs implementation does not return that attribute, and XNU's
generic getter does not synthesize it. The Sandbox lookup therefore takes its
fallback and returns class ID **03**, default **`system`**, without reading the
parent's `RoleAccountStaging` xattr. The fallback string was independently read
from the exact live kernel. No policy decision or attribute was modified by this
observation. Log: `tmpfs-storage-class-trace-v1.log`; observer detached normally.

The daemon's unmodified entitlements include RoleAccountStaging access, not
general installer-equivalent access. This mismatch explains why merely restoring
restricted flags is insufficient. Native APFS staging is the next differential
test, covering extended attributes and new-file flag inheritance together, without
disabling security checks or extending the temporary metadata bridge.

A NEW **1 GiB** scratch image was created inside the already approved data
filesystem: `/home/macvm/installation-data/metadata-contract-20260903.raw`.
This is not the 128 GiB system target. Node `macvm-metadata-contract`, file node
`macvm-metadata-contract-file`, USB device `macvm-metadata-usb`, serial
`MACVMMETA20260903`; QMP confirms writable, io-status ok, exact filename and size
1073741824. Initially device_add rejected a serial longer than 20 characters;
the image/node were preserved and attached with the shortened validated serial.
The new disk has not been formatted at this checkpoint. No host resource or
existing guest disk was replaced, and neither VM was restarted.

The first automatic USB-port assignment then created a new USB hub on root port
4 and attached the scratch disk below it. Apple xHCI reported that the parent slot
was not a hub, so **no macOS disk8 existed** and no formatting was performed.
QEMU `hw/usb/bus.c:usb_claim_port` confirms this automatic expansion when one free
root port remains. Only the newly created scratch USB device and its now-empty
automatic hub (`/machine/unattached/device[26]`) were unplugged. The same image and
block node were then attached explicitly at root port **4**, avoiding the hub.
Keyboard remains port 1, tablet port 2, original installation disk port 3. No
image was deleted or recreated. Guest recognition then succeeded at 05:37 UTC:
blank whole `disk8`, external USB, 1073741824 bytes, and the expected serial.

At 05:43–05:45 UTC a guarded one-time format of only that blank scratch disk
succeeded. It is now APFS `macvm-staging`, **disk9s1**, physical store **disk8s1**,
volume UUID **2DEFBA24-3C0E-4BC2-BA2D-A66AF5879A3A**, mounted at
`/Volumes/macvm-staging`, with ownership enabled. Never erase it again on resume.
The 128 GiB system installation target remains unchanged. The next contract test
uses the original Apple `ditto --persistRootless` and `codesign` on the new
scratch volume only; no staging mount or installer retry has yet been performed.

The 05:45 copy contract **failed**: copying to the pre-existing volume root did
not copy its mode, xattr or restricted flag. The signed bundle itself copied and
strict Apple requirement verification passed, but its flags were zero. The old
script's PASS marker is invalid; raw metadata takes precedence. Guards have been
changed to explicit failure exits, and one-time erase actions retired. Readback
confirmed normal false/conditional status and a minimal `set -e` child exits 1;
the first script's failure to stop is not attributed to an emulated CPU bug.

A fresh subdirectory copy at 05:50 copied the RoleAccountStaging xattr and mode,
but still had flags=0, so its explicit guard correctly exited 1. Merely using
`ditto --persistRootless` is not a verified protection initializer.

Matching `/usr/libexec/rootless-init` code provides the vendor startup repair
entry `-b`: it calls `rootless_apply_internal` with the existing unmodified
`/System/Library/Sandbox/rootless.conf`. That configuration explicitly declares
RoleAccountStaging at the normal staging path. The repair marker is absent in
this Recovery image. The next bounded experiment uses that normal initializer
on a fresh APFS volume mounted at the staging path, preserving the entire old
tmpfs tree below the mount. No `xpcroleaccountd -boot` cleanup is used.

A new empty APFS volume was created at 05:54 **inside the same 1 GiB container**:
`macvm-role-staging`, **disk9s2**, UUID
**489C9422-DAD7-4130-8DBC-9C934B031438**; physical store remains disk8s1, container
UUID **0126FF8F-749C-48BD-967D-4CAA0FE1284B**. Ownership enabled. This is a separate
volume from the failed copy evidence, not another disk or host resource.
Creation is retired from the helper to prevent accidental repeats. The normal
staging mount and protection repair still require result verification.

The 05:56 mount attempt was denied with EPERM. The guarded helper remounted
disk9s2 normally at `/Volumes/macvm-role-staging`; the original tmpfs staging
tree remained visible and unchanged. **rootless-init was not executed.** Do not
attempt more mount variations without a new reason; both APFS volumes are now
preserved evidence, not active staging.

The tmpfs compatibility code was updated based on the exact allocation path:
the new vnode has no reliable cached name yet at the success hook, while x22
contains the already named parent and x24 the componentname. New-file repair now
validates that parent and its requested inherited flag, rather than requiring
the new vnode's name cache. A second narrow compatibility response supplies only
the absent, explicitly requested `va_extflags=0`, under the exact protected
anchor vnode captured by the earlier read-only trace. Existing supported
attributes are untouched, and existing-object flag repair defaults off.
16 contract tests pass in isolated Linux, including absent/requested/supported
mask combinations, stale output values, idempotence, path boundaries, integer
overflow and type rejection.

The first v2 bridge attachment was detached after input loss prevented the guest
probe command from executing: counts create=0, existing=0, extflags=0,
observed=25655. It made **no metadata writes**, and the VM was not restarted.
The next run preloads a fixed enum controller before attaching GDB, so no long
USB keyboard command is needed while kernel observation is active. No new
installer preflight attempt has occurred during these filesystem tests.

With the preloaded controller, the signed-copy probe finally executed at
06:08 UTC. The compatibility response supplied nine absent extended-attribute
results for the staging root/tmp. `ditto` still returned EPERM before creating
the destination: create=0, existing repair=0. Its entitlements differ from the
real role daemon, so this is not presented as a daemon authorization result.
The v3 bridge was detached normally after 15335 observations, without an inode
flag write. The controller now records probe failures without exiting.

Read-only launch inspection found the old installer clients 8384/8347 gone and
their launch domains slain/empty; there is no existing UpdateBrain job to simply
kickstart. A single new installer preflight is therefore instrumented with the
same metadata compatibility plus read-only storage-class observations scoped to
`xpcroleaccountd` and the exact protected anchor. No policy result is modified.
Log: `tmpfs-metadata-compat-v4-role.log`. Installation is still incomplete.

### Actual daemon metadata progress (06:19 guest UTC)

The single instrumented preflight uses InstallAssistant **10028** and
osinstallersetupd **10066**. Product **140-93587** was selected; its metadata and
UpdateBrain download proceeded. The `/rom@0` JavaScript warnings also appear in
older successful-download attempts; they are not treated as a new fatal blocker.

The real `xpcroleaccountd` now resolves the staging root, `tmp`, and new children
to **RoleAccountStaging**, type 4, class **0f**, errno 0, anchored at
**0xfffffe1e3f8db8c8**. This replaces the previously observed fallback `system`
class 03. Its new temporary directory is
`tmp/00B2721D-22F3-4435-9DBE-0263FA8889EA`. Creation hooks have now actually
restored requested inherited flags on new objects (88 at the first checkpoint),
and the missing extended-attribute responses have been supplied repeatedly.
This is a real directory-creation advance, not a zero copy return being mistaken
for success. Signature evaluation, UpdateBrain execution and subsequent
installer screens still require verification. The v4 bridge remains active.

**Verified UpdateBrain wakeup:** the new cache was promoted to
`exec/872415233.7287.xpc`; launchd successfully spawned UpdateBrainService
**PID 10501** at guest 06:20:03. At 06:20:17 the installer reports wakeup 100%,
adds the MobileSoftwareUpdate product, and identifies **macOS 26.6.2 / 25G83**.
At 06:20:18 it reports **Device is supported** and loads the bundled license.
No new launch-constraint crash report was generated. This crosses the original
staging/launch preflight blocker; it is not yet a completed OS installation.

The v4 debugger reached its preconfigured 100000-observation budget and detached
normally: **132 new-object inherited-flag repairs**, **0 existing-object
repairs**, **8974 absent extended-attribute responses**, 100001 observations.
The VM and UpdateBrain continued running. There is currently no guest debugger
attached; the independent native QEMU crash watcher remains untouched. Extended
attribute synthesis was transient per call, not a persistent filesystem-code
fix, so future role-account launches may still need the compatibility bridge.

Reference semantics: Apple's [launch-constraint diagnostics](https://developer.apple.com/documentation/security/applying-launch-environment-and-library-constraints)
and [constraint facts](https://developer.apple.com/documentation/security/defining-launch-environment-and-library-constraints).
XNU's `bsd/vfs/vfs_subr.c` explicitly inherits `SF_RESTRICTED` from the destination
directory during vnode creation/copy; a correct staging hierarchy matters.

The failed installer was dismissed and Recovery Terminal opened. Use the
isolated Linux VNC client with **`--force-caps`**: without it, QEMU receives wrong
shifted symbols. Confirm a command's completion from a serial end marker before
sending another one. Long commands at 20 ms can exceed the guest's input handling;
prefer a short invocation of a reviewed script, delivered from a loopback-only
HTTP server inside the isolated Linux VM, at 100 ms typing delay. Never issue a
destructive command based on an unverified typed line.

## Storage prerequisite

Read-only QMP inspection of Boot119 confirmed these attached storage objects:

- `aux.img`: 2 GiB run-scoped firmware/iSC image, intentionally shared by the
  pflash, iSC and utility frontends. Not an installation target.
- `root.img` and `usb.img`: 64 MiB scratch images. Not installation targets.
- `recovery-overlay.qcow2`: approximately 2.5 GiB, backed by the immutable
  prepared Recovery template. Not a newly provisioned system disk.

This was the initial disk inventory. A new disk was subsequently added as
described below; none of those existing images was resized or replaced.

The outer Linux isolation VM has a 100 GiB system disk; its mounted root
filesystem has approximately 23 GiB available. No other writable persistent data
filesystem was found. The production host filesystem containing the test VM
directory has approximately 2.0 TiB available; this is capacity information, not
permission to change production resources.

The user explicitly **approved a new 200 GiB virtual data disk** under the existing
test directory, for the outer isolation VM only. Existing PCI disks in both live
VMs returned `hotpluggable=false`; the outer IDE CD-ROM did too. No hotplug attempt
was made against those buses. To preserve both running VMs, the new data disk uses
the outer test QEMU's NBD export interface instead. The inner USB bus separately
returned `hotpluggable=true`.

### Newly created storage — do not overwrite on resume

- Host image:
  `/home/jansurezhang/apple-m-macos-vm/validation-20260831/installation-data-20260903.qcow2`
  (200 GiB virtual size, new QCOW2, mode restricted by umask 077).
- It was created as a new test-VM resource using the existing host `qemu-img`;
  no host package, executable, existing image, or startup script was replaced.
- Outer QMP node: `macvm-install-data-20260903`; file node:
  `macvm-install-data-file`; export ID: `macvm-install-data-export`.
- NBD endpoint: **host loopback only**, `127.0.0.1:10893`, one simultaneous
  connection maximum. The only export is `macvm-install-data-20260903`.
- Isolated Linux reaches that endpoint through its existing user-network host
  gateway, `10.0.2.2`. No public listener or firewall change was introduced.
- Linux NBD client: `/dev/nbd0`, managed by `qemu-nbd` PID `935618` at creation;
  kernel NBD PID `935621`; PID file `/run/macvm-install-data-nbd.pid`; local socket
  `/run/macvm-install-data-client.sock`. Check current identities before reuse.
- After independently verifying the 200 GiB size, exact NBD source, absence of
  filesystem signatures and absence of mounts, the **new disk only** was formatted
  with ext4 **inside the isolated Linux VM**. Label: `MACVM_INSTALL`; UUID:
  `432e46d4-88c5-4885-bf16-1ecdb0f90ba5`.
- Mounted at `/home/macvm/installation-data`, approximately 196 GiB available.
- New inner target: `/home/macvm/installation-data/macos-26-system.raw`,
  **128 GiB** sparse raw image, initially blank.
- Inner QMP node: `macvm-install-system`; file node: `macvm-install-system-file`.
- Successfully attached online through existing `usb-bus.0` as `usb-storage`,
  ID `macvm-install-usb`, serial `MACVMINSTALL20260903`, logical block 512 bytes,
  physical block 4096 bytes. QMP reports `io-status=ok`, read-write, expected image
  path and capacity. macOS identifies the blank whole device as **disk6**,
  QEMU HARDDISK, USB, external/fixed, read-write, exactly **137438953472 bytes**.
  USB serial is `MACVMINSTALL20260903`. After rechecking this identity and
  visually verifying the typed command before Enter, `diskutil eraseDisk APFS
  macos26 GPT /dev/disk6` completed successfully. Screenshot
  `19-format-complete.png` shows **Finished erase on disk6** and the returned
  prompt. New APFS volume `macos26` is `disk7s1`, physical store `disk6s2`.
  This formats only the newly provisioned blank target; no existing user data
  was removed. Never repeat erase on resume.

The NBD export, connection and mount were established live. They are **not yet
automatically recreated after restarting the outer VM**. Preserve the running
environment and implement an explicit idempotent resume procedure before treating
this storage attachment as a persistent deployment.

Outer VM identity resolved read-only:

- Directory: `/home/jansurezhang/apple-m-macos-vm/validation-20260831`
- Name: `macvm-validation-20260831`
- PID at inspection: `502194`
- QMP socket: that directory's `qmp.sock`
- SSH forwarding: host loopback port `30222` to guest port `22`
- Configured resources: 16 vCPU / 36 GiB

Boot119 remains running as inner QEMU PID `925112`, with 8 vCPU / 16 GiB. Neither
VM was restarted. The production QEMU, other VMs, disks, services, and passthrough
assignments were not modified.

## Resume safely

### Installer reboot boundary

The original `validation-boot119.sh` is not a resume launcher: it creates fresh
scratch root/USB images, copies the iSC template over the run AUX, and creates a
Recovery overlay. **Never rerun that script against this installation run.**
QEMU `hw/vmapple/vmapple.c:create_bdif` connects pflash index 1 to firmware root;
the current 64 MiB scratch root is not the new USB installation target. A future
installed-system launch must preserve the current AUX, target disk and Recovery
overlay and explicitly arrange the firmware and OS storage paths.

Before target installation, exact Boot119 process, 8 CPUs, 16 GiB memory, running
state and target path/capacity were checked. Its QMP `set-action` now sets
`reboot=shutdown, shutdown=pause`. Per `qapi/run-state.json` and
`system/runstate.c:qemu_system_reset_request/main_loop_should_exit`, this retains
the VM only when the guest requests shutdown/reboot. No immediate stop or reset
was sent; QMP still reported running afterward. Evidence:
`install-reboot-policy.json`. The production host and outer VM were not changed.
Do not merely resume halted guest CPUs after a completed guest shutdown; inspect
the installation state and prepare the next boot deliberately.

1. Recheck live VM identities, the existing NBD export/client/mount and the
   installer screen. Do not recreate or format the approved disk again.
2. Continue the current installer after successful UpdateBrain preflight. Do not
   reopen the installer or repeat the earlier staging attempts. If a later stage
   fails, collect its own evidence; the original generic alert was not a DNS fault.
3. Plan both target-disk preparation and installed-system reboot before starting
   disk writes. The current launcher is a recovery bootstrap, not an already
   verified installed-system boot launcher.
4. Verify any format/erase target against the newly created test disk's identity;
   never use the auxiliary or Recovery images as a guessed installation target.
5. Finish installation, create the requested account through Setup Assistant,
   and verify a real desktop/login and system identity before claiming completion.

No build, test, or macOS guest execution occurred on the production Mac or the
production Linux host during this installation attempt. Host writes were limited
to the explicitly approved new test data image and the existing test QEMU's
in-memory configuration for that image and its loopback NBD export. Filesystem
formatting, mounting, the NBD client and the inner raw image creation ran only in
the isolated Linux VM.
