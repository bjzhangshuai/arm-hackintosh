# MacVM

MacVM is an experimental platform for running an Apple Silicon ARM64 macOS guest on an x86_64
Linux host. The correctness baseline is QEMU AArch64 TCG with the upstream `vmapple` machine. The
long-term graphics path is the unmodified guest AppleParavirtGPU driver through a Linux PVG host
implementation, Metal/AIR translation, Vulkan, and an explicitly selected NVIDIA RTX 4060.

This repository is at **Phase 1 bring-up**, not at usable-VM status. It contains pinned upstream
sources, source-level feasibility analysis, an isolated QEMU patch, a guarded host probe, explicit
Vulkan device policy, and a vmapple machine-initialization smoke test. It contains no Apple firmware,
IPSW, recovery image, or macOS disk.

## Current status

| Capability | Status | Evidence |
|---|---|---|
| Reproducible upstream checkout | Working | `upstreams.lock.toml`, `scripts/check-upstreams.sh` |
| Physical-host safety inventory | Validation commands were read-only; separate authorized host work was observed | See the boundary note in `docs/test-environment.md` |
| Unit test suite | 136 cases passing in isolated Ubuntu 26.04 VM | `tests/`, `docs/test-environment.md` |
| Linux AArch64 QEMU build recipe | Working in isolated VM | `scripts/build.sh`, `docs/test-environment.md` |
| Host-tuned CPU build | O3/LTO/native/PGO measured in isolated VM | `scripts/build-performance.sh`, `docs/cpu-optimization.md` |
| `vmapple` under TCG | Builds and registers | `patches/qemu/`, `docs/test-environment.md` |
| Machine init: CPU/RAM/GIC/PCIe/cfg/bdif/block | QMP smoke test passing, with optional restore USB BDIF backend | `scripts/check-vmapple-machine.sh`, `patches/qemu/0005-vmapple-bdif-add-optional-usb-backend.patch` |
| PV GPU | Partial: address-map sentinels only | Linux MMIO backend not connected |
| macOS 26 boot / SMP / networking / storage | Signed iBootStage1 restore path and signed iBEC validation reached; macOS does not boot | LocalPolicy is accepted, iBEC decompresses and its manifest validates after the restore-workspace sizing fix; handoff currently fails before recovery/kernel/installer |
| GPU / Metal / compute / WindowServer | Deferred; not tested | Validate after the user installs the RTX 4060 Ti |
| Audio / sleep / shutdown / reboot | Not implemented | Out of current priority |

Commands that execute code refuse to run unless the operator sets
`MACVM_DEBUG_ENV_CONFIRMED=YES` inside a dedicated disposable Linux x86_64 test VM.

## Repository layout

```text
config/             runtime policy, including exact GPU selection
docs/               architecture, upstream gaps, and performance plan
host/macvm_host/    host probing and hardware-GPU selection policy
patches/qemu/       small ordered patches against the locked QEMU commit
scripts/            guarded build and validation entry points
tests/              host-side unit tests (run only in the debug environment)
third_party/        pinned Git submodules
tools/              Python command-line helpers
```

## Dedicated test-VM workflow

Do not run these commands on a workstation or production hypervisor. Run them only inside a
disposable Linux x86_64 test VM:

```bash
export MACVM_DEBUG_ENV_CONFIRMED=YES
./scripts/check-upstreams.sh
./scripts/probe-host.sh
./scripts/build.sh
./scripts/check-vmapple-machine.sh
./scripts/test.sh
python3 tools/probe_ipsw.py /path/to/UniversalMac_Restore.ipsw \
  --expected-version 26.6 --require-product VirtualMac2,1
```

After establishing a correctness-checked representative workload, the optional two-stage
`scripts/build-performance.sh generate|use` flow produces a host-specific PGO build. See
`docs/cpu-optimization.md`; do not deploy a `-march=native` binary to a different CPU baseline.

Required build packages include a C compiler, Python 3.11+, Meson, Ninja, pkg-config, GLib,
Pixman, and system libfdt development headers. `MESON_WRAP_MODE=nodownload` prevents Meson's normal
wrap fallback. QEMU's own first-run Python bootstrap and subproject update helpers can still fetch
their pinned packages; this must happen only inside the disposable test VM or a pre-populated build
cache.

The verified test record includes direct iBootStage2 execution, the later signed iBootStage1
restore path, accepted LocalPolicy, and signed iBEC decompression/manifest validation. It does not
claim a macOS kernel, recovery, or installer boot. See
`docs/test-environment.md`, `docs/macos-26-restore.md`, `BLOCKERS.md`, and
`docs/performance-plan.md` for the exact boundary and next experiments.
