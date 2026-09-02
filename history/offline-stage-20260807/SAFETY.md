# Safety Boundary

- The production hypervisor is storage only for this bundle.
- Do not run package installation, QEMU builds, macOS boot attempts, GPU probes, or benchmarks on
  the production hypervisor.
- Run every mutable or executable workflow in a separate disposable Linux x86_64 VM.
- Maximum test-VM allocation: 4 vCPUs and 16 GiB RAM. Bundle defaults: 2 vCPUs and 8 GiB RAM.
- Do not attach host PCI, GPU, USB, physical disks, TAP, bridges, or VFIO devices.
- Do not install or replace NVIDIA drivers. No RTX 4060 is present in the current host.
- Do not overwrite imported Apple assets. Conversion scripts write separate outputs.
- Keep the source Apple Silicon VM and its machineId/ECID, auxiliary storage, and disk together.

