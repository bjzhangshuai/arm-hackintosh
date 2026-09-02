# Test suite

The suite currently contains 136 cases using Python's standard-library `unittest` framework and does not require network access,
Apple boot assets, a real GPU, or root privileges. Hardware and subprocess behavior are mocked in
unit tests. The two source integration checks read the pinned local submodules and run only
`git apply --check`; they do not compile or modify QEMU.

Coverage groups:

- `test_command.py`: command availability, success, nonzero exit, text/byte timeout behavior.
- `test_gpu_policy.py`: device identity matching, multi-GPU selection, all software-renderer refusal
  branches, and explicit development fallback.
- `test_probe.py`: CPU topology/features, NVIDIA CSV, Vulkan devices/extensions, huge pages,
  Resizable BAR, complete mocked host collection, absent-tool behavior, and JSON persistence.
- `test_environment_guard.py`: positive and negative Python/shell dedicated-host gates.
- `test_probe_ipsw.py`: valid restore metadata plus missing/corrupt/ambiguous manifests, malformed
  plists, size/hash/version/build mismatches, root-manifest precedence, and VirtualMac targeting.
- `test_build_vmapple_aux.py`: DER/IMG4/IM4R wrapping, SHSH ticket and generator loading, both
  VMApple HUFA slots, the AVPBooter SHA-384 header check, diagnostic hash modes, byte layout, and
  malformed or undersized input rejection.
- `test_verify_local_policy.py`: exact 32-byte BNCH matching, payload and restore identity,
  production/security flags, exact next-stage and payload SHA-384 bindings, and missing, duplicate,
  or malformed field rejection.
- `test_upstream_audit.py`: valid lock, missing tree/path, wrong commit/URL, non-Git tree, and the
  checked-in four-upstream lock.
- `test_qemu_patch_contract.py`: touched-file boundary, TCG/HVF/PVG conditions, CPU model, AArch64
  registration, both placeholder MMIO regions, diagnostic-only BDIF tracing, optional USB BDIF
  restore-media plumbing, and applicability to the locked source.
- `test_project_policy.py`: exact RTX 4060 policy, TCG baseline, asset exclusion, required Phase 0
  documents, isolated no-download build, non-executing QMP machine smoke test, and the 32-byte
  LocalPolicy ApNonce contract.

Run only on the dedicated Linux x86_64 debug host:

```bash
export MACVM_DEBUG_ENV_CONFIRMED=YES
./scripts/test.sh
```

This suite has intentionally not been executed on the development workstation.
The generated AUX fixture contains no Apple firmware and the tool never downloads Apple assets.
