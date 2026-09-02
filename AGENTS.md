# Repository operating rules

1. Correctness order is Phase 0 → Phase 1 → boot chain → macOS 12 → PVG → performance. Do not add
   a DBT optimizer before profiling proves TCG translation is the active bottleneck.
2. Never modify a system QEMU or install into `/usr`; build only under `build/`.
3. Never download or commit Apple firmware, IPSWs, recovery images, macOS disks, keys, or secrets.
4. Never run build, probe, VM, benchmark, or test commands outside the dedicated Linux x86_64 debug
   host. Execution scripts must call `macvm_require_debug_env`.
5. Do not reset a dirty upstream tree. Keep QEMU changes as ordered patches under `patches/qemu/`.
6. Do not silently select a Vulkan device. Production and performance paths must reject llvmpipe,
   lavapipe, SwiftShader, and other software renderers.
7. A missing feature is `Partial`, `Broken`, or `Not implemented`; a placeholder is not completion.
8. Every discovered boot blocker records evidence, source location, root cause, attempted solution,
   and the next bounded experiment in `BLOCKERS.md`.
9. Any future lowering needs a unit test, differential comparison against TCG, and a benchmark.
10. Crash and performance claims must preserve configuration, host capabilities, logs, and metrics.
