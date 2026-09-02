# Performance and evidence plan

Performance work starts only after correctness gates. Every result archives the locked commits,
config, host capability JSON, command line, logs, raw samples, and summary; no result from a software
Vulkan device may be labeled GPU-accelerated.

## Baselines

1. Phase 1: QEMU vmapple initialization time and idle memory, for regression only.
2. Phase 3: macOS 12 TCG boot time, userspace/SSH readiness, host CPU utilization, translated-block
   counts, TLB/helper/exception counters.
3. Phase 5: guest clear and triangle correctness plus frame time; capture `nvidia-smi` utilization,
   memory, clocks, and process evidence alongside Vulkan device UUID.
4. Phase 6: WindowServer interaction: compositor frame pacing, resizing, multiple windows, IOSurface
   video, and Retina resolution.

## CPU profile breakdown

Collect perf call graphs and QEMU trace events, then attribute samples to softmmu/TLB, helpers,
dispatcher, translation, exceptions, generated host code, and other. Report wall time, CPU time,
p50/p95/p99, and run-to-run variance. Tier-0 work is permitted only for a measured dominant bucket.

Compare every MacDBT change with TCG on deterministic instruction sequences: registers, NZCV,
memory, exception class/syndrome/address, and instruction count. Add cold/warm microbenchmarks and a
guest workload benchmark for every accepted lowering.

## GPU evidence

Use explicit UUID/BDF matching. Before each run record Vulkan driver/API/device/extensions and
NVIDIA driver/VRAM/BAR1/Resizable BAR. Correlate guest workload timestamps with host queue traces and
NVIDIA telemetry. Compare a reference backend and RTX path using framebuffer hashes, expected pixels,
synchronization outcomes, and shader outputs with declared floating-point tolerance.

## Optimization order

Correctness → observability → stable benchmark → profiling → targeted optimization. Expected later
experiments are Tier-0 DBT, software-TLB/fastmem approaches, immutable-code persistent cache, and only
then Tier-1 optimization. Kernel assistance is considered only after userspace memory-path profiling.

The reproducible compiler-level PGO workflow and its portability/acceptance constraints are recorded
in [cpu-optimization.md](cpu-optimization.md). It is a safe host-build optimization, not a substitute
for profiling before changing TCG lowering semantics.
