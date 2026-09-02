# Ubuntu 24.04 amd64 offline packages

`debs/` contains the resolved `Depends` and `Pre-Depends` closure for the roots in
`root-packages.txt`, as seen by the Ubuntu 24.04 repositories on 2026-08-07.

This is a build/test dependency bundle, not a Linux distribution mirror. It intentionally excludes:

- NVIDIA drivers and kernel modules;
- VFIO, bridge, TAP, or production-host configuration;
- Apple proprietary assets;
- recommended and suggested packages that are not strict dependencies.

Use only in a disposable Ubuntu 24.04 amd64 VM. Package versions and actual DEB metadata are listed
under `../../inventory/`.

