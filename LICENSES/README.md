# Third-party licensing

MacVM's original scaffolding has no distribution license selected yet. Do not redistribute it until
the project owner chooses one.

Pinned source dependencies keep their own licenses:

| Component | License declared upstream | Local license |
|---|---|---|
| QEMU | GPL-2.0-or-later and component licenses | `third_party/qemu/COPYING` |
| reims-vgpu | LGPL-3.0-or-later | `third_party/reims-vgpu/LICENSE` |
| metal2vulkan | LGPL-3.0-or-later | `third_party/metal2vulkan/LICENSE` |
| libapplegfx-vulkan | MIT | `third_party/libapplegfx-vulkan/LICENSE` |

QEMU patches are intended for use under QEMU's applicable GPL terms. Apple trademarks and software
remain the property of their respective owners; no Apple binary is included here.
