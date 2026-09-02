# Upstream source analysis

Analysis is pinned by `upstreams.lock.toml`; paths below refer to those exact commits.

## QEMU

Reusable without redesign:

- `hw/vmapple/vmapple.c`: RAM map, firmware range, CPU construction, GICv3, cfg, bdif, AES, PL011,
  RTC, GPIO, GPEX PCIe, USB defaults, and boot plumbing.
- `hw/vmapple/cfg.c`, `bdif.c`, `aes.c`, `virtio-blk.c`: VMApple-specific device behavior.
- `target/arm`, `target/arm/tcg`, `accel/tcg`, and `tcg/i386`: the initial execution baseline and
  future profiling surface.

Host-locked portions:

- `hw/vmapple/Kconfig` requires HVF and selects `MAC_PVG_MMIO`.
- `configs/devices/aarch64-softmmu/default.mak` disables VMAPPLE.
- `hw/display/apple-gfx*.m` imports ParavirtualizedGraphics and Metal and is compiled only with the
  Darwin framework dependency configured in top-level `meson.build`.
- `hw/vmapple/vmapple.c:create_gfx()` constructs `apple-gfx-mmio` unconditionally, and the machine
  defaults to the `host` CPU, which is not a TCG CPU model.

The Phase 1 patch separates machine construction from the native Apple graphics backend. It does not
change the VMApple memory map or guest ABI.

## reims-vgpu

The repository has three declared pathways: Linux/x86_64 guest/Vulkan; Apple Silicon host/ARM64
guest/Metal; and Apple Silicon host/ARM64 guest/Vulkan through MoltenVK. It therefore contains both
halves needed by MacVM but not the Linux host + ARM64 guest intersection.

Reusable pieces are `crates/reims-vgpu-wire`, the Rust command decoder/runtime, Vulkan integration,
and the thin MMIO QEMU shim design. Missing integration is a non-Darwin AArch64 QEMU build, Linux
guest-memory callbacks for that MMIO shim, and target-hardware validation. Its QEMU build script
currently rejects AArch64 on a non-Darwin host.

## metal2vulkan

The crate translates sanitized AIR/LLVM IR to SPIR-V with vertex, fragment, kernel/compute, and
passthrough stage entry points. Its contract honestly returns `FALLBACK` on unsupported input. The
repository is alpha and does not establish complete Metal language, texture, synchronization, or
pipeline coverage; successful `spirv-val` is not pixel correctness. MacVM must preserve translation
repros and never convert fallback into apparent success.

## libapplegfx-vulkan

This clean-room C library provides a PGDevice-shaped API, Apple PVG protocol decoding, three-level
radix guest-VA translation, render/compute/blit paths, Linux memory aliasing, Vulkan rendering, and
its own AIR-to-SPIR-V work. It reports a full render chain on lavapipe and integrates with a separate
x86 PCI QEMU device.

It is valuable evidence and a differential oracle, especially for Linux task-memory coherence,
protocol framing, stamps, interrupts, and framebuffer tests. It is not directly an ARM vmapple MMIO
device and does not by itself prove the NVIDIA RTX 4060 path.

## Reuse estimate

The machine model and TCG baseline are largely reusable. Most PVG protocol and shader translation
logic exists in upstream projects. The high-risk new work is integration rather than greenfield
emulation: Linux-enable the ARM MMIO shim, implement correct QEMU guest-memory mappings and IRQ
delivery, reconcile runtime APIs, and validate synchronization on the proprietary NVIDIA Vulkan
driver. CPU Apple-specific gaps cannot be estimated honestly until the first boot trace.
