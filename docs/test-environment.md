# Isolated Test Environment Record

## 2026-08-31 Ubuntu 26.04 revalidation

The production x86_64 host was inventoried read-only and then used only to run a new outer Ubuntu
26.04 validation VM under `/home/jansurezhang/apple-m-macos-vm/validation-20260831`. The VM uses
QEMU user networking with one loopback-only SSH forward and has no bridge, TAP, VFIO, GPU, USB, or
physical-disk passthrough. It began at 2 vCPUs/8 GiB for the source build and was cleanly restarted
at the user's updated limit of 16 vCPUs/36 GiB for restore-image validation.

The host's Ubuntu QEMU packages remained at `1:10.2.1+ds-1ubuntu3.1`. The SHA-256 of
`/usr/bin/qemu-system-x86_64` remained
`e8143c590e74194763cd03ae334d194e1a9148bdd07cabb44913fd85b99a7704`. The isolated-validation
commands made no package, driver, library, QEMU binary, bridge, device-binding, or existing-VM
change on the host.

### Concurrent authorized host work

The final timestamp comparison found that a separate direct SSH session from `192.168.8.124`
modified production-host resources between 16:25 and 16:28 while this validation VM was running.
The user subsequently confirmed that these operations were explicitly assigned to another local
agent.
The system journal records `sudo install` commands replacing
`macvm-scripts/{start-vm.sh,hugepages-1g.py,set-mem-hugepage.py}`, replacing
`.macvm/vms/5016c857ab39/config.json`, installing and enabling
`/etc/systemd/system/macvm-hugepages.service`, and invoking the production `start-vm.sh`. These
commands are not part of the isolated validation workflow. No rollback was attempted because they
were authorized concurrent production maintenance and are outside this workflow's scope.

At the final snapshot the new service was enabled but inactive, both 1 GiB hugepage counts were
zero, no `qemu-system` process was running, and the validation SSH port was closed. Therefore the
record can prove that system QEMU itself remained unchanged, but it must **not** claim that all
production VM scripts/configuration remained unchanged during the wall-clock test window.

| Check | Result |
|---|---|
| Unit and policy tests | PASS, 182/182 |
| Locked upstream audit | PASS, 4/4 exact revisions |
| QEMU AArch64 TCG build | PASS, QEMU 11.0.93 with patches 0001-0016 |
| Built binary SHA-256 | `4f8da103c42b8ad05393b375da6832ff2435a607975b61cb98a07d3522026fda` |
| `vmapple` registration | PASS |
| Paused vmapple/QMP initialization | PASS |
| Apple iBoot `SVC #0xa0` PSCI conduit | PASS, opt-in `svc-a0-psci=on` returned PSCI version `0x10001` |
| Official macOS 26.6 IPSW integrity and metadata | PASS, including `VirtualMac2,1` |
| Decoded `vma2` iBoot under TCG | ENTERED iBootStage2, then deterministic iBoot panic |
| Signed iBootStage1/iBEC restore path | ENTERED remote boot; 32-byte-BNCH LocalPolicy accepted; signed iBEC decompresses and its manifest validates after the restore-workspace sizing fix; final `SVC #7` handoff reaches callback `0xaca00000`; relocated iBEC enters iBootStage2 recovery mode; USB restore chardev packet round trip PASS |
| macOS recovery/kernel/installer | NOT BOOTED |
| GPU/Vulkan/Metal/WindowServer | DEFERRED until RTX 4060 Ti installation |

The ARM64 execution result is stronger than the earlier paused-machine smoke test: real Apple
`vma2` firmware emitted serial output through TCG, and the later partial restore implementation
reached signed iBootStage1 remote boot, accepted LocalPolicy, validated a signed iBEC payload, and
entered iBootStage2 recovery mode. It is still not a macOS boot. A later trace fix moved the
synthetic return sentinel from real iBoot code address `0x700c56c8` to guest RAM address
`0x73fff000`; this removed an earlier false early-return reading. With that fix, the synthetic
restore path reaches the real final `SVC #7` stage switch and calls the handoff trampoline at
`0xaca00000`. Follow-on QEMU patches fixed the observed `SVC #0xa0`, low-scratch, USB restore cfg,
pending receive, queue selector, guest-out, and chardev transport gaps. The current first blocker is
the missing persistent host-side restore protocol/client behind that now-working USB restore
transport. The path still does not reach recovery ramdisk, kernel, installer GUI, networking,
storage install, or SMP. See `docs/macos-26-restore.md`.

## Safety boundary

All execution on 2026-08-07 took place in a newly created Ubuntu 24.04 x86_64 test VM. The
production hypervisor was used only to hold and run that isolated VM. No packages, drivers,
libraries, kernels, QEMU binaries, device assignments, bridges, TAP interfaces, VFIO bindings, or
existing VM resources were installed or replaced on the production hypervisor. The physical host
capability probe was not run.

The isolated VM configuration was:

- 2 vCPUs, capped well below the permitted maximum of 4;
- 8 GiB RAM, capped below the permitted maximum of 16 GiB;
- one 60 GiB sparse qcow2 overlay backed by an official Ubuntu cloud image;
- QEMU user networking with a single SSH forward bound to host loopback;
- no GPU, PCI, USB, disk, bridge, TAP, or VFIO passthrough;
- host QEMU process constrained with CPU affinity, positive nice value, idle I/O priority, and QEMU
  sandbox restrictions.

The host has no NVIDIA RTX 4060. GPU, Vulkan, Metal translation, compute, WindowServer, and GPU
passthrough were therefore **not tested**.

After validation, the test VM was shut down normally. Its QEMU process is stopped and the loopback
SSH forward is closed. The retained 60 GiB sparse overlay consumes approximately 1.5 GiB of host
storage and preserves the guest build artifacts for a later controlled restart.

## Reproducibility inputs

The guest used Linux 6.8.0-136-generic on x86_64, with 2 visible CPUs and 7.8 GiB visible memory.
The four locked upstream revisions were checked before each build:

- QEMU: `3e3ccab106f879b1512f8e0d51a827dd4de30e22`;
- reims-vgpu: `a9adcac950f73ac9b659f0f26e28d11fde3940e9`;
- metal2vulkan: `8d982e649eb164923721b6cf4cd68cc35bd17cec`;
- libapplegfx-vulkan: `2f0bcd653bfb85d4499a38632acce5d1722fd99c`.

The first QEMU configure bootstrapped pinned Python build packages and QEMU subprojects inside the
test VM. `MESON_WRAP_MODE=nodownload` does not suppress those QEMU-specific bootstrap helpers, so
the build is not claimed to be fully offline.

## Results

| Check | Result | Evidence |
|---|---|---|
| Unit and policy tests | PASS, 69/69 | `MACVM_DEBUG_ENV_CONFIRMED=YES ./scripts/test.sh` |
| Locked upstream audit | PASS, 4/4 | all revisions above reported `OK` |
| QEMU AArch64 TCG build | PASS | QEMU 11.0.93, `qemu-system-aarch64` produced |
| Built binary SHA-256 | Recorded | `0f1fc928174e4d35cbe452e97f721e8185920c588c1d37d4a737b30f2f56519c` |
| `vmapple` registration | PASS | machine list reports `Apple aarch64 Virtual Machine` |
| Paused machine initialization | PASS | QMP reached `prelaunch`; CPU/RAM/GIC/PCIe/cfg/bdif/root block initialized |
| PVG behavior | Sentinel only | both Apple PVG MMIO ranges are observable unimplemented devices |
| Guest instruction execution | NOT RUN | smoke test uses `-S`; dummy firmware was never executed |
| macOS boot | NOT RUN | no authorized AVPBooter, auxiliary image, or macOS disk was supplied |
| Physical GPU path | NOT RUN | no RTX 4060 is installed on the host |

The first compile exposed a real GCC portability error in `hw/vmapple/aes.c`: a block-scope
`static const size_t` was used as an initialized array bound. Patch 0002 changes that bound to an
integer constant expression. A second smoke-test failure showed the Apple block device requires an
explicit `variant=root`; the test script and its contract test now enforce it.

These results establish that the locked source can build an AArch64 TCG system emulator on x86_64
Linux and initialize the non-GPU `vmapple` machine graph. They do not establish that macOS boots,
that Apple CPU behavior is complete, or that the planned GPU architecture works.
