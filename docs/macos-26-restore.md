# macOS 26 restore validation on x86_64 Ubuntu 26.04

## Current checkpoint (2026-09-03)

Boot119 reaches the real **ARM64 macOS Tahoe 26.6/25G72 installer welcome UI**.
The QMP capture at 2026-09-03 03:09:33 +0800 shows the artwork, title, instructions
and Continue button with no stale Recovery contents. Exact ARM64 executable,
kernel/version evidence and image hashes are recorded in
[Boot119 installer acceptance](boot119-installer-acceptance.md).
Boot119 remains running in the isolated x86_64 VM. Installation to disk and a boot
of the installed system have not been validated. Boot118 exited normally after its
final evidence was retained; no production QEMU or VM resource was replaced.
See [BLOCKERS.md](../BLOCKERS.md) for remaining graphics gaps and test gates.

## Historical restore-chain result

The official macOS Tahoe 26.6 `VirtualMac2,1` restore IPSW is genuine and its ARM64 iBootStage2
payload executes under QEMU TCG on x86_64. The later signed restore-chain experiment reaches
iBootStage1 remote boot, accepts LocalPolicy, validates signed iBEC, decompresses iBEC after a
restore-workspace sizing fix, reaches the final iBSS `SVC #7` stage switch, calls the iBEC handoff
callback at `0xaca00000`, enters relocated iBEC/iBootStage2 recovery mode, and completes
bidirectional USB restore endpoint-event round trips over a socket-backed QEMU chardev. It now also
answers a libirecovery-style EP0 `getenv build-version` command with `mBoot-18000.161.9`. macOS
itself did **not** boot or install. The observed boundary is now the missing persistent host-side
restore protocol/client after iBEC enters tethered restore.

All ARM64 execution, package installation, build, and test commands in this record ran inside a
disposable Ubuntu 26.04 x86_64 VM. The validation workflow changed no host QEMU package, binary,
bridge, device binding, or passthrough configuration. A separate concurrent SSH session performed
production-VM maintenance authorized by the user while validation was running. That work is recorded
in `docs/test-environment.md`; it was outside this isolated validation workflow and was not reverted.

## Restore image

- product: macOS Tahoe 26.6, build `25G72`;
- Apple CDN file: `UniversalMac_26.6_25G72_Restore.ipsw`;
- exact size: `19772077142` bytes;
- SHA-256: `a8d59bdec11a16f704c1a41edc86461c77e71c790ac834a05266b9670287142c`;
- ZIP members: 1527, with a complete CRC pass;
- root restore metadata: `ProductVersion=26.6`, `ProductBuildVersion=25G72`;
- supported virtual product found in the manifest: `VirtualMac2,1`.

`tools/probe_ipsw.py` performs these checks without extracting the operating-system payload. The
test suite covers corrupt ZIPs, missing or malformed manifests, the nested BootabilityBundle
manifests found in real IPSWs, metadata mismatches, hashes, and product targeting.

## Executed boot payload

The IPSW contains `Firmware/all_flash/iBoot.vma2.RELEASE.im4p`. Its IM4P OCTET STRING is LZFSE
compressed. Decoding it produced a 738376-byte AArch64 image with SHA-256
`045256c693c626e1144511b984f09668e20efc02e7cbbcf699e32c21e32e2d4d`.

With that image as vmapple firmware, QEMU 11.0.93 TCG produced this serial state before a reset:

```text
======== Start of iBootStage2 serial output. ========
iBoot Panic
Board: vma2ap:0
Chip: fe00:00
Build: RELEASE:mBoot-18000.161.9
```

This proves the decoded ARM64 firmware entered iBootStage2 through TCG. It does not prove a macOS
kernel, recovery environment, installer, APFS root, SMP, storage, or networking boot.

## Restore-chain progress after the direct-IPSW baseline

The later isolated experiment implemented enough of the restore storage path to move past the raw
IPSW limitation. `tools/build_vmapple_aux.py` creates a two-slot HUFA image, and AVPBooter tracing
showed that the 32-byte HUFA validation field is the first 32 bytes of SHA-384 over the 32-byte
header prefix. With that correction, AVPBooter read the signed LLB/iBSS path and reached
iBootStage1 remote boot.

The next deterministic failure was LocalPolicy's inner manifest. The rejected Apple ticket carried a
48-byte BNCH, while an unmodified comparison trace showed that this iBootStage1 path requires
exactly 32 bytes. The first 32 bytes matched, so the failure was length-specific rather than a
different nonce value. A new Apple TSS response was then requested with the required 32-byte nonce.
`tools/verify_local_policy.py` independently parses `img4tool -a` output and confirms an exact
32-byte BNCH, matching `VirtualMac2,1` board/chip identity and test ECID, production/security mode,
local-boot mode, payload type, and both manifest digest widths. That replacement now executes:
LocalPolicy outer validation returns accepted, the LocalPolicy handler returns zero, and iBSS
advances to signed iBEC.

iBEC itself is structurally valid for this restore identity. The signed iBEC IMG4 validates, and
BVX2 decompression produces a 738376-byte AArch64 runtime image. The decompression path initially
failed because iBootStage1 reported a 512 KiB restore workspace maximum while the compressed iBEC,
uncompressed iBEC, and scratch window require about 784 KiB. Patching only the traced workspace-size
return inside the stopped disposable-VM experiment from `0x80000` to `0x200000` lets iBoot allocate
its own larger high-memory workspace. With that sizing fix, BVX2 decompression returns zero and the
iBEC manifest validation returns zero.

The next blocker was the restore object contract after iBEC manifest validation. An earlier
trace reused `0x700c56c8`, a real iBoot code address, as the synthetic handler-return sentinel; that
created a false early-return reading. The current trace uses a private guest-RAM sentinel at
`0x73fff000`. With that correction, the synthetic restore path reaches `IBEC_STAGE_SVC7`, resolves
the final stage-switch descriptors, and calls `IBEC_FINAL_HANDOFF_CALLBACK callback=0xaca00000`.
The callback dumper confirms `0xaca00000` is the real handoff trampoline: it disables interrupts,
clears memory windows, disables `sctlr_el1`, and prepares to enter the stage image. Relocating the
decompressed iBEC image to its preferred low base before that callback runs iBEC's prologue, sets
`VBAR_EL1`, and reaches the relocated iBEC entry at `0x70080178`.

The next deterministic failure is now inside iBEC: selector `0xa7` chooses the `root` object slot,
but the descriptor pointer passed to the presence checker is `0x0`. The checker at the traced
descriptor-present path rejects that null descriptor, iBEC enters its panic/log path, reports panic
line `3742`, and finally spins at `0x7006c438`. The observed `svc #0xa0` happens after this panic
path is already active, so it is treated as a secondary logging/exception symptom rather than the
root QEMU/CPU blocker.

A diagnostic-only GDB shim then injected a minimal descriptor at the lookup return point. That
descriptor used the iBEC-provided root base/span values and caused the descriptor-present check to
return `basic_ok=1`, so the null descriptor is confirmed as a real wall after relocated entry. The
run advanced further and then failed at iBEC's `svc #0xa0` service-call path with panic line `192`.
Code inspection showed those calls use PSCI-style function IDs: `0x84000000` for PSCI_VERSION,
`0x84000008` for SYSTEM_OFF, and `0x84000009` for SYSTEM_RESET. Upstream QEMU TCG recognized PSCI
only through HVC/SMC, so this was a genuine QEMU model gap; it was not evidence of a missing ARM64
CPU instruction. Patch `0006-vmapple-route-iboot-svc-a0-psci.patch` adds an opt-in filtered
`svc-a0-psci` conduit for vmapple. In the isolated VM, a smoke test single-stepped `svc #0xa0` with
`x0=0x84000000` and observed `x0=0x10001`, proving QEMU returned its PSCI 1.1 version through the
new conduit.

Further isolated QEMU patches moved the boundary again. Patch `0007` maps iBEC's required low
scratch RAM window. Patch `0009` makes the USB BDIF function report cfg `0x1a01`, which this iBEC
expects for restore USB rather than ordinary block media. Patches `0011` through `0014` keep restore
receives pending instead of delivering bogus zero packets, add a one-shot first-packet probe, track
the selected USB queue, and consume iBEC guest-out packets. With those in place, a first-packet probe
using `000000000202` reaches iBootStage2 recovery mode and observes iBEC's first response packet
`0402`.

Patches `0015` and `0016` replace the one-shot probe with a socket-backed restore chardev. Bytes
from the host are buffered, parsed as restore endpoint events, and delivered to iBEC's pending USB
restore receive buffer; iBEC guest-out packets are written back to the chardev. Validation run
`/home/macvm/runs/aux-26.6/ibec-usb-chardev-in-0202-20260901-061634` connected a host helper, sent
`000000000202`, traced `chardev-buffered`, `chardev-in`, `guest-out`, and `chardev-out`, and the
helper received `0402`. The same serial log shows:

```text
Microkernel iBootStage2 for vma2
aborting autoboot due to tethered restore
Entering iBootStage2 recovery mode, starting command prompt
```

Further endpoint-event tracing confirmed the host-to-iBEC frame shape as
`uint32_le(payload_len) + endpoint byte + kind byte + payload`. Run
`/home/macvm/runs/aux-26.6/ibec-usb-callback-map-20260901-073422` shows the bootstrap `event:02,2`
packet reaches the relocated iBEC endpoint-event callback path at `0x7008d4cc` and returns raw guest
packet `0402`. Run `/home/macvm/runs/aux-26.6/ibec-usb-ep04-kind1-callback-20260901-074013` shows
`event:04,1:0000000000000800` is delivered intact to the same callback and returns `0104`. Run
`/home/macvm/runs/aux-26.6/ibec-usb-ep04-kind1-kind3-probe-20260901-074205` shows that adding
`event:04,3` returns `0504` but still does not enter the inner packet dispatcher at `0x7009190c` or
the type-0/control handler at `0x7008ec60`. This narrows the current work to the host-side mapping
from libirecovery-style control/bulk transfers into iBEC's inner USB request objects; the outer
BDIF/chardev endpoint-event transport is no longer the observed blocker.

The next code-level root cause check showed those failed command attempts were sent to inactive
bulk endpoint slots (`0x02`/`0x04`) before iBEC had configured them. At that phase, iBEC's endpoint
engine is consuming EP0 control slots `0x00` and `0x80`. After adding semantic restore-session
steps, run `/home/macvm/runs/aux-26.6/ibec-usb-control-getenv-semantic-20260901-004752` sends
`event:02,2`, then `command:getenv build-version`, receives the short status `0100`, sends
`control-in:0xff`, and receives
`01006d426f6f742d31383030302e3136312e3900` (`0100 + "mBoot-18000.161.9\0"`).

This record therefore claims LocalPolicy acceptance, iBEC validation, final iBSS `SVC #7`
stage-switch execution, handoff callback `0xaca00000`, relocated iBEC/iBootStage2 recovery entry, a
verified QEMU fix for the Apple iBoot `SVC #0xa0` PSCI conduit, verified bidirectional USB restore
endpoint-event exchanges, and a verified EP0 control command/result exchange. It does not claim
restore ramdisk, kernel, installer GUI, storage install, networking, SMP, or UI.

`tools/fetch_local_policy.c` now rejects non-32-byte ApNonce input before constructing or sending a
request, preventing the known-bad ticket shape from recurring. The verifier and its synthetic
fixtures add no Apple firmware or ticket data to the repository.

## Why the IPSW did not install directly

Passing the 19.7 GB IPSW as `-bios` fails because vmapple's firmware region is 1 MiB and the IPSW is
a ZIP archive, not a ROM. Passing it read-only as the root block device produces byte-identical
iBoot panic output to an empty root image. The firmware therefore does not interpret the raw ZIP as
an installed or restorable disk.

The manifest describes a restore flow involving iBSS/iBEC, a restore ramdisk, device tree,
kernelcache, encrypted AEA operating-system images, trust caches, and a MobileDevice-compatible
restore host. The current QEMU machine model supplies a firmware memory region, config MMIO, an
auxiliary block device, and a root block device; it does not implement that IPSW restore service.

The existing launch contract instead requires a matching set of firmware/AVPBooter,
AuxiliaryStorage, installed macOS disk, and machine identifier/ECID. Those assets were not copied
from the production machine or its existing macOS VM.

## QEMU restore-media plumbing

Patch `0005-vmapple-bdif-add-optional-usb-backend.patch` adds an optional third BDIF backend for
restore media. It keeps the existing AUX and root block-device requirements intact, does not touch
system QEMU, and is covered by the QEMU patch-contract tests. Attaching the complete IPSW through
this optional backend did not work because iBEC's restore USB path is a packet transport, not a raw
block device. The later USB restore patches therefore model that path explicitly: cfg `0x1a01`,
pending host-input reads, queue-select-aware readiness, guest-out packets, and finally a
bidirectional chardev.

`tools/extract_restore_bundle.py` stages the BuildManifest-selected `VirtualMac2,1` restore assets
from the IPSW: restore kernelcache, DeviceTree, restore ramdisk, and restore trust cache. It also
records metadata for OS/BaseSystem/static trust cache assets without transforming or committing
Apple payloads. The next QEMU/restore-side code should use this staged bundle to build the missing
iBEC descriptor/object graph instead of pointing iBEC at the raw IPSW ZIP.

## QEMU Apple iBoot SVC #0xa0 PSCI conduit

The relocated iBEC diagnostic exposed an iBEC service-call path using AArch64 `svc #0xa0` with PSCI
function IDs in `x0`. Before patching, QEMU delivered that SVC back to guest EL1, producing
`esr=0x560000a0` and panic line `192`. Source inspection found the reason in QEMU TCG:
`target/arm/tcg/psci.c:arm_is_psci_call()` accepted only HVC and SMC conduits, while vmapple set
CPUs to the HVC conduit by default.

`patches/qemu/0006-vmapple-route-iboot-svc-a0-psci.patch` adds a new internal conduit value and a
vmapple machine property, `svc-a0-psci=on`. When enabled, only AArch64 `SVC #0xa0` calls whose `x0`
matches a QEMU-implemented PSCI function ID are routed to the existing PSCI handler. The default
remains HVC, so unrelated vmapple launches are unchanged and non-PSCI Apple SVC calls are still left
to guest firmware.

Validation in the disposable Ubuntu VM after patches 0001-0016 and the endpoint-event helper
updates:

- unit tests: `MACVM_DEBUG_ENV_CONFIRMED=YES python3 -m unittest discover -s tests -v` →
  220 tests OK;
- QEMU build: `MACVM_BUILD_JOBS=4 ./scripts/build.sh` → produced
  `/home/macvm/src/macvm/build/qemu/qemu-system-aarch64`;
- patch queue idempotency: `./scripts/apply-qemu-patches.sh` reports 0001–0016 already applied or
  applies the missing patch cleanly;
- smoke: a stopped vmapple VM single-stepped `svc #0xa0` with `x0=0x84000000`; after the step,
  `pc=0x70000004` and `x0=0x10001`;
- smoke: `ibec-usb-chardev-out-0202-20260901-061402` proved iBEC's first `0402` response can be
  written from QEMU to a host socket when the old debug first-packet injector is enabled;
- smoke: `ibec-usb-chardev-in-0202-20260901-061634` proved the real chardev input path too: the
  host socket sent `000000000202`, QEMU traced `chardev-in`, iBEC traced `guest-out`, QEMU traced
  `chardev-out`, and the host socket received `0402`;
- smoke: `ibec-usb-event-syntax-smoke-20260901-074605` proved the semantic helper syntax
  `event:02,2` emits the same `000000000202` frame, reaches the Stage2 recovery prompt, and records
  endpoint/kind/payload metadata in `session.jsonl`;
- smoke: `ibec-usb-control-getenv-semantic-20260901-004752` proved semantic EP0 control command
  steps: `command:getenv build-version` returns status `0100`, and `control-in:0xff` returns
  `0100 + "mBoot-18000.161.9\0"`;
- probes: `ibec-usb-ep04-kind1-callback-20260901-074013` and
  `ibec-usb-ep04-kind1-kind3-probe-20260901-074205` confirm endpoint `0x04`, kind `1` and kind `3`
  events are valid outer events, but are not the correct pre-configuration path for command/status
  traffic.

## Next safe step

Extend the persistent host-side restore session behind `vmapple-bdif.usb-restore-chardev` from the
proven EP0 `getenv` exchange into the full idevicerestore sequence. The next layer is component
command/status handling, recovery send-buffer start (`0x41`), bulk endpoint `0x04` uploads, and
RestoreRamDisk/DeviceTree/KernelCache handoff backed by the staged BuildManifest-selected
`VirtualMac2,1` assets. If a subsequent packet exposes another unsupported QEMU Apple VM
device/register/transport behavior, identify the exact source path, patch the isolated QEMU tree,
rebuild, and retry. Do not bypass IMG4 validation, do not change TCG validation behavior, and do not
change production-host resources. GPU/Vulkan work remains deferred until the RTX 4060 Ti is
installed.
