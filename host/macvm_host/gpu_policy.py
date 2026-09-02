from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping


SOFTWARE_MARKERS = ("llvmpipe", "lavapipe", "swiftshader", "software rasterizer")


class GpuPolicyError(RuntimeError):
    """Raised when no Vulkan device satisfies the configured hardware policy."""


@dataclass(frozen=True)
class GpuSelection:
    name: str
    vendor: str
    uuid: str | None
    pci_bdf: str | None
    software: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "vendor": self.vendor,
            "uuid": self.uuid,
            "pci_bdf": self.pci_bdf,
            "software": self.software,
        }


def _normalized(value: object) -> str:
    return str(value or "").strip().casefold()


def is_software_device(device: Mapping[str, Any]) -> bool:
    name = _normalized(device.get("name"))
    device_type = _normalized(device.get("device_type"))
    cpu_device = device_type == "cpu" or device_type.endswith("_type_cpu")
    return cpu_device or any(marker in name for marker in SOFTWARE_MARKERS)


def select_vulkan_device(
    devices: Iterable[Mapping[str, Any]],
    *,
    vendor: str,
    device_name: str,
    pci_bdf: str = "auto",
    device_uuid: str = "auto",
    hardware_required: bool = True,
    allow_software_fallback: bool = False,
) -> GpuSelection:
    candidates = list(devices)
    if not candidates:
        raise GpuPolicyError("no Vulkan physical devices were reported")

    wanted_vendor = _normalized(vendor)
    wanted_name = _normalized(device_name)
    wanted_bdf = _normalized(pci_bdf)
    wanted_uuid = _normalized(device_uuid)

    def matches(device: Mapping[str, Any]) -> bool:
        if wanted_vendor and wanted_vendor not in _normalized(device.get("vendor")):
            return False
        if wanted_name and wanted_name not in _normalized(device.get("name")):
            return False
        if wanted_bdf != "auto" and wanted_bdf != _normalized(device.get("pci_bdf")):
            return False
        if wanted_uuid != "auto" and wanted_uuid != _normalized(device.get("uuid")):
            return False
        return True

    matching = [device for device in candidates if matches(device)]
    if not matching:
        names = ", ".join(str(device.get("name", "<unnamed>")) for device in candidates)
        raise GpuPolicyError(
            f"configured Vulkan device was not found: vendor={vendor!r}, "
            f"device_name={device_name!r}; discovered: {names}"
        )

    hardware = [device for device in matching if not is_software_device(device)]
    if hardware:
        chosen = hardware[0]
    elif hardware_required and not allow_software_fallback:
        raise GpuPolicyError("only a software Vulkan implementation matched; hardware is required")
    else:
        chosen = matching[0]

    software = is_software_device(chosen)
    if software and not allow_software_fallback:
        raise GpuPolicyError("software Vulkan fallback is disabled")

    return GpuSelection(
        name=str(chosen.get("name", "")),
        vendor=str(chosen.get("vendor", "")),
        uuid=chosen.get("uuid"),
        pci_bdf=chosen.get("pci_bdf"),
        software=software,
    )
