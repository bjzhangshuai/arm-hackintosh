MacVM cross-ISA proxy benchmark

All three modes execute inside the isolated x86_64 Linux test VM:
  x86_vm_native: x86_64 code executed by the KVM-backed test VM CPU
  x86_tcg:       the same x86_64 binary executed by qemu-x86_64 TCG
  arm64_tcg:     the same C source compiled for ARM64 and executed by qemu-aarch64 TCG

This is a CPU user-mode translation benchmark. It is not a macOS system benchmark and it is not a
cycle-accurate model of a future Apple CPU. Each mode is pinned to one vCPU. Five measured runs follow
one warm-up run. Cross-architecture checksums must agree before results are accepted.
