from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import re
from typing import Any

from .command import CommandResult, run_command


CPU_FLAGS = (
    "avx",
    "avx2",
    "avx512f",
    "aes",
    "sha_ni",
    "bmi1",
    "bmi2",
    "fma",
    "pcid",
    "invpcid",
    "constant_tsc",
    "nonstop_tsc",
    "vmx",
    "svm",
)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _command_record(result: CommandResult) -> dict[str, Any]:
    return {
        "command": list(result.command),
        "available": result.available,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _parse_cpuinfo(text: str) -> tuple[dict[str, bool], str | None, str | None]:
    flags: set[str] = set()
    vendor = None
    model = None
    for line in text.splitlines():
        key, separator, value = line.partition(":")
        if not separator:
            continue
        key = key.strip().casefold()
        value = value.strip()
        if key == "vendor_id" and vendor is None:
            vendor = value
        elif key == "model name" and model is None:
            model = value
        elif key in {"flags", "features"}:
            flags.update(value.split())

    present = {flag: flag in flags for flag in CPU_FLAGS}
    present["avx512"] = any(flag.startswith("avx512") for flag in flags)
    present["sha"] = "sha_ni" in flags or "sha1" in flags or "sha2" in flags
    present["aes_ni"] = "aes" in flags
    present["invariant_tsc"] = "constant_tsc" in flags and "nonstop_tsc" in flags
    return present, vendor, model


def _parse_lscpu_json(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {}

    fields: dict[str, str] = {}
    for item in payload.get("lscpu", []):
        field = str(item.get("field", "")).strip().rstrip(":").casefold()
        if field:
            fields[field] = str(item.get("data", "")).strip()

    def integer(name: str) -> int | None:
        try:
            return int(fields[name])
        except (KeyError, ValueError):
            return None

    sockets = integer("socket(s)")
    cores_per_socket = integer("core(s) per socket")
    physical_cores = sockets * cores_per_socket if sockets and cores_per_socket else None
    return {
        "architecture": fields.get("architecture"),
        "sockets": sockets,
        "cores_per_socket": cores_per_socket,
        "physical_cores": physical_cores,
        "threads_per_core": integer("thread(s) per core"),
        "logical_threads": integer("cpu(s)"),
        "numa_nodes": integer("numa node(s)"),
    }


def _parse_nvidia_smi(text: str) -> list[dict[str, Any]]:
    devices: list[dict[str, Any]] = []
    for line in text.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 7:
            continue
        memory_mib = None
        match = re.search(r"\d+", parts[4])
        if match:
            memory_mib = int(match.group(0))
        devices.append(
            {
                "name": parts[0],
                "uuid": parts[1],
                "pci_bdf": parts[2],
                "driver_version": parts[3],
                "vram_mib": memory_mib,
                "bar1_total": parts[5],
                "bar1_used": parts[6],
            }
        )
    return devices


def _parse_vulkan_summary(text: str) -> list[dict[str, Any]]:
    devices: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if re.match(r"GPU\d+:$", line):
            if current:
                devices.append(current)
            current = {}
            continue
        if current is None or "=" not in line:
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        mapping = {
            "deviceName": "name",
            "deviceType": "device_type",
            "deviceUUID": "uuid",
            "driverName": "driver_name",
            "driverInfo": "driver_info",
            "apiVersion": "api_version",
            "vendorID": "vendor_id",
            "deviceID": "device_id",
        }
        if key in mapping:
            current[mapping[key]] = value
    if current:
        devices.append(current)

    for device in devices:
        name = str(device.get("name", ""))
        vendor_id = str(device.get("vendor_id", ""))
        if "nvidia" in name.casefold() or vendor_id.casefold() in {"0x10de", "4318"}:
            device["vendor"] = "nvidia"
        elif "intel" in name.casefold() or vendor_id.casefold() in {"0x8086", "32902"}:
            device["vendor"] = "intel"
        elif (
            "amd" in name.casefold()
            or "radeon" in name.casefold()
            or vendor_id.casefold() in {"0x1002", "4098"}
        ):
            device["vendor"] = "amd"
        else:
            device["vendor"] = "unknown"
    return devices


def _parse_vulkan_extensions(text: str) -> list[str]:
    return sorted({name.upper() for name in re.findall(r"\bVK_[A-Za-z0-9_]+\b", text)})


def _hugepages() -> dict[str, Any]:
    one_gib = Path("/sys/kernel/mm/hugepages/hugepages-1048576kB")
    return {
        "one_gib_supported": one_gib.is_dir(),
        "one_gib_total": int(_read_text(one_gib / "nr_hugepages").strip() or 0),
        "transparent_hugepage": _read_text(Path("/sys/kernel/mm/transparent_hugepage/enabled")).strip(),
    }


def _resizable_bar(nvidia_devices: list[dict[str, Any]]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for device in nvidia_devices:
        bdf = str(device.get("pci_bdf", ""))
        lspci_bdf = re.sub(r"^[0-9a-fA-F]{4}([0-9a-fA-F]{4}:)", r"\1", bdf)
        resource = Path("/sys/bus/pci/devices") / lspci_bdf / "resource"
        lspci = run_command(("lspci", "-vv", "-s", lspci_bdf))
        capability_present = bool(re.search(r"Resizable BAR", lspci.stdout, re.IGNORECASE))
        current_sizes = re.findall(r"current size:\s*([^,\n]+)", lspci.stdout, re.IGNORECASE)
        records.append(
            {
                "pci_bdf": bdf,
                "resource_present": resource.exists(),
                "capability_present": capability_present,
                "current_sizes": current_sizes,
                "state": "enabled" if current_sizes else ("capable" if capability_present else "unknown"),
                "lspci": _command_record(lspci),
            }
        )
    return {
        "devices": records,
        "note": "State is decoded from lspci PCIe Resizable BAR capabilities when pciutils is available.",
    }


def collect_host_capabilities() -> dict[str, Any]:
    cpuinfo = _read_text(Path("/proc/cpuinfo"))
    flags, vendor, model = _parse_cpuinfo(cpuinfo)
    lscpu = run_command(("lscpu", "--json"))
    numa = run_command(("lscpu", "-p=CPU,NODE"))
    nvidia = run_command(
        (
            "nvidia-smi",
            "--query-gpu=name,uuid,pci.bus_id,driver_version,memory.total,bar1_memory.total,bar1_memory.used",
            "--format=csv,noheader,nounits",
        )
    )
    vulkan = run_command(("vulkaninfo", "--summary"), timeout_seconds=40)

    nvidia_devices = _parse_nvidia_smi(nvidia.stdout) if nvidia.returncode == 0 else []
    vulkan_devices = _parse_vulkan_summary(vulkan.stdout) if vulkan.returncode == 0 else []
    cpu_topology = _parse_lscpu_json(lscpu.stdout) if lscpu.returncode == 0 else {}
    return {
        "schema_version": 1,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "host": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "hostname": platform.node(),
        },
        "cpu": {
            "vendor": vendor,
            "model": model,
            "physical_cores": cpu_topology.get("physical_cores"),
            "logical_threads": cpu_topology.get("logical_threads") or os.cpu_count(),
            "topology": cpu_topology,
            "features": flags,
            "lscpu": _command_record(lscpu),
            "numa": _command_record(numa),
            "hugepages": _hugepages(),
            "virtualization": {
                "vmx": flags.get("vmx", False),
                "svm": flags.get("svm", False),
                "dev_kvm": Path("/dev/kvm").exists(),
            },
        },
        "nvidia": {
            "devices": nvidia_devices,
            "command": _command_record(nvidia),
            "resizable_bar": _resizable_bar(nvidia_devices),
        },
        "vulkan": {
            "devices": vulkan_devices,
            "extensions_reported_by_summary": _parse_vulkan_extensions(vulkan.stdout),
            "command": _command_record(vulkan),
        },
    }


def write_capabilities(path: Path) -> dict[str, Any]:
    capabilities = collect_host_capabilities()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(capabilities, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return capabilities
