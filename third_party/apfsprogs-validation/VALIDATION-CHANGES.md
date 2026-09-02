# Isolated-VM APFS volume builder

This is a separate working copy of the existing `apfsprogs-src` used by the
validation VM (upstream: https://github.com/eafer/apfsprogs). The original tools
and installed binaries are not replaced. The upstream LICENSE is retained.

`mkapfs -V label,uuid,role` may be repeated for 1–4 empty volumes. Supported
roles are None (0), Preboot (0x10), xART (0x100), and Hardware (0x140).
Do not combine `-V` with legacy `-L`/`-u`. Legacy single-volume mode is retained.

Changes account for each volume in the container object map, its own catalog
map/trees, `apfs_fs_index`, allocation bitmap and free-space counters. Metadata
block ranges are disjoint; volume ids do not overlap ephemeral object ids.
Container size must satisfy the existing maximum-volume calculation.

This remains an experimental formatter, not a general APFS editor. Run only
inside `macvm-validation`, against newly created disposable image files. Never
run against block devices, mounted images, current AUX storage, or production.
The new code must pass `apfsck` and explicit structure/negative-input tests
before its output is used in a future boot. No Apple binaries or activation
records are included or forged by this formatter.
