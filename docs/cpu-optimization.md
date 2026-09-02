# CPU optimization profile

The production-oriented x86_64 build uses QEMU's existing TCG correctness path and optimizes its
host executable with four compiler techniques: `-O3`, link-time optimization (LTO), native CPU
tuning, and profile-guided optimization (PGO). This does not introduce an unverified instruction
lowering or change guest-visible semantics.

## Safe two-stage build

Both stages are accepted only inside an explicitly confirmed Linux x86_64 debug VM. They never
install the binary, invoke `sudo`, or delete an existing build directory. Parallelism defaults to
two jobs and is capped at four.

```sh
export MACVM_DEBUG_ENV_CONFIRMED=YES
export MACVM_QEMU_PGO_BUILD_DIR="$PWD/build/qemu-pgo-host-a"
scripts/build-performance.sh generate
```

Run the instrumented `qemu-system-aarch64` through a representative macOS workload. Include boot,
application launch, system calls, memory traffic, atomics, and the instruction families expected in
production. Verify correctness, then stop QEMU cleanly through QMP `quit`; an abrupt kill can prevent
GCC from flushing `.gcda` files. Build the optimized binary from that same directory:

```sh
scripts/build-performance.sh use
```

The default `-march=native -mtune=native` output is deployable only to x86_64 hosts exposing the same
instruction set as the training/build VM. For a fleet baseline, set `MACVM_PERF_CPU_FLAGS` to the
fleet's explicit minimum ISA and retrain. PGO profiles are workload- and source-revision-specific;
repeat both stages after changing QEMU or the representative workload.

## Acceptance

Compare an uninstrumented baseline and the final PGO binary using identical VM configuration,
guest image, CPU affinity, warm-up, and sample count. The comparison tool rejects incomplete logs,
unknown/missing cases, unequal sample counts, non-positive measurements, and any work/checksum
mismatch before reporting median speedup and run-to-run coefficient of variation:

```sh
tools/compare_cpu_bench.py \
  --baseline baseline-a.log --baseline baseline-b.log \
  --candidate pgo-a.log --candidate pgo-b.log \
  --csv comparison.csv --json comparison.json
```

Treat a Linux ARM64 `virt` guest as a TCG CPU-path proxy, not proof of macOS boot, `vmapple`, or GPU
performance. Re-run the same acceptance procedure with the final macOS image when it is available.
