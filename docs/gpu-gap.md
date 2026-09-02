# GPU gap analysis

## Required path

```text
guest Metal → AppleParavirtGPU.kext → PVG MMIO/shared memory
→ host protocol decoder → AIR/SPIR-V translation → Vulkan → RTX 4060
```

Direct GPU passthrough and a CUDA graphics translation layer are outside the architecture.

## Existing capabilities

- QEMU vmapple defines the guest-visible PVG and IOSFC MMIO ranges and IRQs, but its upstream host
  implementation is Apple's macOS-only framework bridge.
- reims-vgpu has an ARM sysbus MMIO shim and an independent Linux Vulkan runtime pathway, but they
  are not built together on Linux AArch64-target QEMU today.
- metal2vulkan covers important shader stages and resource metadata but explicitly has unsupported
  inputs and alpha-level compatibility.
- libapplegfx-vulkan supplies a substantial Linux clean-room protocol/reference implementation and
  tests, mainly demonstrated with its PCI device and lavapipe.

## Missing for RTX 4060

1. Compile and attach the reims ARM MMIO QEMU shim on Linux.
2. Translate QEMU guest physical memory into the runtime's task/radix mapping contract without stale
   aliases or host-pointer leakage.
3. Deliver PVG/IOSFC interrupts with correct pending-bit and monotonic-stamp semantics.
4. Make Vulkan physical-device selection match configured vendor, name, UUID/BDF; reject software.
5. Establish memory visibility and synchronization across guest CPU writes, decoder threads, Vulkan
   queues, presentation/readback, reset, and teardown.
6. Validate AIR/SPIR-V output, render/compute/blit command coverage, IOSurface formats, and display
   pacing on the NVIDIA proprietary driver.
7. Prove execution with NVIDIA telemetry correlated to a guest Metal workload.

## Bring-up gates

The sequence is attach → resource creation → clear → triangle → guest Metal triangle → WindowServer.
Each gate captures protocol traces and a framebuffer/pixel oracle. A successful device attach is not
GPU acceleration, and a valid SPIR-V module is not visual correctness.
