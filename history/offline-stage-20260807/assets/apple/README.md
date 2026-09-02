# Apple asset import

`installers/macos-26.6/` contains the locally cached, official Apple CDN restore image
`UniversalMac_26.6_25G72_Restore.ipsw`. Its internal `Restore.plist` includes `VirtualMac2,1`, but
this only establishes Apple restore-image metadata; it does not prove compatibility with the
project's Linux/QEMU implementation.

Place original, legally obtained VM exports in `incoming/`:

| File | Source | Handling |
|---|---|---|
| `AVPBooter.vmapple2.bin` | Apple Virtualization.framework resources | copy unchanged to `ready/` |
| `aux.img` | installed macOS 12.x VM | trim the first 0x4000 bytes into `ready/aux.img.trimmed` |
| `disk.img` | same installed VM | copy unchanged to `ready/` |
| `macosvm.json` | same installed VM | extract machineId/ECID into `ready/ecid.txt` |

These four items must belong to the same source VM. Do not put an IPSW in place of the installed
disk image. Newer macOS guests are not claimed supported by the locked QEMU documentation.

The `incoming/` and `ready/` directories intentionally contain no VM-specific Apple files in this
bundle. The restore IPSW is retained separately under `installers/`.

