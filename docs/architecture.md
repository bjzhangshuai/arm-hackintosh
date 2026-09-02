# Architecture

## Correctness baseline

```text
ARM64 macOS guest
  XNU / Metal / WindowServer / AppleParavirtGPU.kext
                         |
                         | VMApple MMIO, IRQ, shared guest memory
                         v
patched upstream QEMU vmapple machine
  CPU: AArch64 TCG (`max`)        GPU: Linux PVG MMIO device
  GICv3 / cfg / bdif / AES             |
  GPEX PCIe / vmapple virtio-blk       v
                         reims-vgpu wire + runtime
                                  |
                           metal2vulkan
                                  |
                              Vulkan
                                  |
                 NVIDIA driver → explicit RTX 4060
```

The first working CPU is upstream TCG. MacDBT is a later alternative execution engine, never a boot
prerequisite. The GPU is paravirtualized: the RTX 4060 stays owned by the Linux driver and is not
passed through to the guest.

## Phase 1 boundary

The first QEMU patch changes only machine availability and initialization:

- build `VMAPPLE` when TCG or HVF is available;
- keep Apple's native `apple-gfx-mmio` only when the Apple framework backend is built;
- map named, observable sentinels over the PVG and IOSFC ranges on a non-Apple host;
- use QEMU's TCG-capable `max` AArch64 CPU rather than `host`;
- register the machine only in `qemu-system-aarch64`.

The sentinels are not a fake GPU. A guest access is logged as unimplemented until the real Linux PVG
MMIO device replaces them. This lets CPU, RAM, GIC, PCIe, cfg, bdif, and block construction be tested
independently.

## Ownership boundaries

| Layer | Primary owner | Rule |
|---|---|---|
| VMApple machine and generic devices | upstream QEMU | inherit; patch minimally |
| AArch64 correctness | QEMU TCG | permanent differential oracle |
| Cross-ISA speed | future MacDBT | only profile-selected hot paths |
| Guest PVG wire/device runtime | reims-vgpu | one production protocol implementation |
| Linux memory/protocol reference | libapplegfx-vulkan | reference and test oracle |
| AIR/LLVM to SPIR-V | metal2vulkan | explicit fallback/error, never assume coverage |
| Physical GPU selection | MacVM host policy | exact device, no silent software fallback |

## Data and trust boundaries

Guest-provided ring entries, task page tables, addresses, sizes, shader blobs, and synchronization
values are untrusted. The backend must bounds-check before mapping or decoding, preserve monotonic
stamp semantics, and attach errors to a task/channel/opcode. Host Vulkan handles and pointers never
cross the guest ABI. Apple boot assets are user-supplied and remain outside the repository.
