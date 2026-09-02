# CPU gap analysis

## Known before execution

Upstream QEMU already supplies the AArch64 decoder, TCG IR, x86_64 TCG backend, MMU/softmmu,
exceptions, GICv3, generic timers, atomics, crypto helpers, and many architectural system registers.
That is the only defensible correctness baseline.

The upstream vmapple machine's default `host` CPU assumes HVF and cannot be instantiated by TCG.
Phase 1 selects QEMU's `max` AArch64 CPU so the machine can initialize on x86_64. This is a build and
machine-model gap, not proof that macOS can boot.

## Unknown until the first boot trace

The first failing dependency may be an unsupported ID/system register, exception-level behavior,
timer semantics, PAC behavior, an Apple-specific instruction, cache-maintenance behavior, memory
ordering, or a device MMIO contract. Adding guessed Apple features before observing that failure
would weaken the baseline.

Phase 2 must capture the first deterministic blocker with PC, disassembly, exception syndrome,
registers, serial output, and MMIO log. One isolated compatibility change follows one recorded
blocker, with a regression test.

## Performance work deliberately deferred

After macOS reaches userspace and GPU bring-up is stable, profile TCG into translation, dispatcher,
helpers, softmmu/TLB, exception, and other buckets. Only then evaluate a Tier-0 direct AArch64 to
x86_64 DBT, block linking, SIMD/crypto lowering, fastmem, larger software TLBs, and persistent cache.

Every new lowering must compare registers, flags, memory, and exceptions against TCG. Self-modifying
code, executable-page invalidation, W^X/JIT transitions, and dyld shared-cache identity are mandatory
cache-correctness concerns.
