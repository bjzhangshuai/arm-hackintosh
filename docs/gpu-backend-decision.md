# GPU backend decision

## Decision

Choose the document's option C, with a single production path:

- **Production protocol/runtime:** reims-vgpu wire parser, decoder, device runtime, Vulkan backend,
  and metal2vulkan integration.
- **Reference and differential oracle:** libapplegfx-vulkan tests and implementation evidence for
  Linux task-memory aliasing, radix translation, protocol framing, stamps/IRQ behavior, and expected
  pixels.

Do not ship both as independently selectable production PVG devices.

## Rationale

reims-vgpu already keeps the QEMU C shim thin, has the correct ARM MMIO device shape on the Apple
host pathway, and has Linux Vulkan plus metal2vulkan on its x86 pathway. Combining those two halves
adds a host integration seam without replacing the guest wire model.

libapplegfx-vulkan has deeper clean-room Linux protocol and memory evidence and is valuable for
cross-checking behavior. Adopting it wholesale would still require a new vmapple MMIO attachment and
would introduce a second AIR translator beside the document's required metal2vulkan evaluation.
Keeping it as an oracle reduces duplicate production ownership while preserving its strongest value.

## Revisit conditions

Revisit only if a measured blocker shows that reims-vgpu cannot meet one of these contracts and the
libapplegfx implementation demonstrably can: ARM MMIO attach, guest-memory coherence, protocol
coverage, NVIDIA Vulkan correctness, or sustained upstream maintainability. Record the reproduction
and API migration cost before changing the owner.
