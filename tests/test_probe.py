from __future__ import annotations

from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "host"))

from macvm_host.probe import (  # noqa: E402
    _hugepages,
    _parse_cpuinfo,
    _parse_lscpu_json,
    _parse_nvidia_smi,
    _parse_vulkan_extensions,
    _parse_vulkan_summary,
    _resizable_bar,
    collect_host_capabilities,
    write_capabilities,
)
from macvm_host.command import CommandResult  # noqa: E402


class ProbeParserTests(unittest.TestCase):
    def test_cpu_features(self) -> None:
        text = """vendor_id : GenuineIntel
model name : Test CPU
flags : avx avx2 avx512f aes sha_ni bmi1 bmi2 fma pcid invpcid constant_tsc nonstop_tsc vmx
"""
        features, vendor, model = _parse_cpuinfo(text)
        self.assertEqual(vendor, "GenuineIntel")
        self.assertEqual(model, "Test CPU")
        self.assertTrue(features["avx512"])
        self.assertTrue(features["aes_ni"])
        self.assertTrue(features["invariant_tsc"])

    def test_cpu_features_are_unioned_across_processors(self) -> None:
        features, vendor, model = _parse_cpuinfo(
            "vendor_id: GenuineIntel\nmodel name: Unit CPU\nflags: avx aes\n"
            "vendor_id: DifferentIgnored\nmodel name: Other Ignored\nflags: avx2 sha_ni svm\n"
        )
        self.assertEqual(vendor, "GenuineIntel")
        self.assertEqual(model, "Unit CPU")
        self.assertTrue(features["avx"])
        self.assertTrue(features["avx2"])
        self.assertTrue(features["sha"])
        self.assertTrue(features["svm"])

    def test_empty_cpuinfo_returns_false_features_and_no_identity(self) -> None:
        features, vendor, model = _parse_cpuinfo("")
        self.assertIsNone(vendor)
        self.assertIsNone(model)
        self.assertFalse(features["avx2"])
        self.assertFalse(features["invariant_tsc"])

    def test_nvidia_csv(self) -> None:
        devices = _parse_nvidia_smi(
            "NVIDIA GeForce RTX 4060, GPU-abc, 00000000:01:00.0, 555.42, 8188, 8192, 8\n"
        )
        self.assertEqual(devices[0]["vram_mib"], 8188)
        self.assertEqual(devices[0]["pci_bdf"], "00000000:01:00.0")

    def test_nvidia_parser_handles_multiple_devices_and_units(self) -> None:
        devices = _parse_nvidia_smi(
            "RTX 4060, GPU-A, 00000000:01:00.0, 555.42, 8188 MiB, 8192 MiB, 8 MiB\n"
            "RTX 4090, GPU-B, 00000000:02:00.0, 555.42, 24564 MiB, 32768 MiB, 0 MiB\n"
        )
        self.assertEqual([device["uuid"] for device in devices], ["GPU-A", "GPU-B"])
        self.assertEqual(devices[1]["vram_mib"], 24564)

    def test_nvidia_parser_ignores_incomplete_rows(self) -> None:
        self.assertEqual(_parse_nvidia_smi("RTX 4060, GPU-A\n"), [])

    def test_lscpu_topology(self) -> None:
        topology = _parse_lscpu_json(
            '{"lscpu": ['
            '{"field": "CPU(s):", "data": "32"},'
            '{"field": "Thread(s) per core:", "data": "2"},'
            '{"field": "Core(s) per socket:", "data": "8"},'
            '{"field": "Socket(s):", "data": "2"},'
            '{"field": "NUMA node(s):", "data": "2"}'
            "]}"
        )
        self.assertEqual(topology["physical_cores"], 16)
        self.assertEqual(topology["logical_threads"], 32)

    def test_lscpu_invalid_json_is_empty(self) -> None:
        self.assertEqual(_parse_lscpu_json("not json"), {})

    def test_lscpu_missing_socket_data_does_not_invent_core_count(self) -> None:
        topology = _parse_lscpu_json('{"lscpu": [{"field": "CPU(s):", "data": "8"}]}')
        self.assertIsNone(topology["physical_cores"])
        self.assertEqual(topology["logical_threads"], 8)

    def test_vulkan_summary(self) -> None:
        devices = _parse_vulkan_summary(
            """GPU0:
    apiVersion         = 1.3.280
    deviceType         = PHYSICAL_DEVICE_TYPE_DISCRETE_GPU
    deviceName         = NVIDIA GeForce RTX 4060
    deviceUUID         = 0011
    vendorID           = 0x10de
"""
        )
        self.assertEqual(devices[0]["vendor"], "nvidia")
        self.assertEqual(devices[0]["name"], "NVIDIA GeForce RTX 4060")

    def test_vulkan_summary_splits_multiple_gpus_and_classifies_vendors(self) -> None:
        devices = _parse_vulkan_summary(
            """GPU0:
deviceName = Mystery Adapter A
vendorID = 0x8086
GPU1:
deviceName = Mystery Adapter B
vendorID = 0x1002
GPU2:
deviceName = Mystery Adapter
vendorID = 0xffff
"""
        )
        self.assertEqual([item["vendor"] for item in devices], ["intel", "amd", "unknown"])

    def test_vulkan_summary_ignores_properties_before_first_gpu(self) -> None:
        devices = _parse_vulkan_summary("apiVersion = 1.3\nGPU0:\ndeviceName = RTX 4060\n")
        self.assertEqual(len(devices), 1)
        self.assertNotIn("api_version", devices[0])

    def test_vulkan_extensions(self) -> None:
        self.assertEqual(
            _parse_vulkan_extensions("VK_KHR_surface VK_EXT_debug_utils VK_KHR_surface"),
            ["VK_EXT_DEBUG_UTILS", "VK_KHR_SURFACE"],
        )

    @patch("macvm_host.probe._read_text")
    @patch("macvm_host.probe.Path.is_dir", return_value=True)
    def test_hugepage_probe_decodes_one_gib_and_thp(self, _is_dir, read_text) -> None:
        read_text.side_effect = lambda path: (
            "4\n" if path.name == "nr_hugepages" else "always [madvise] never\n"
        )
        result = _hugepages()
        self.assertTrue(result["one_gib_supported"])
        self.assertEqual(result["one_gib_total"], 4)
        self.assertEqual(result["transparent_hugepage"], "always [madvise] never")

    @patch("macvm_host.probe.Path.exists", return_value=True)
    @patch("macvm_host.probe.run_command")
    def test_resizable_bar_probe_normalizes_nvidia_bdf(self, run, _exists) -> None:
        run.return_value = CommandResult(
            ("lspci",),
            True,
            0,
            "Capabilities: Physical Resizable BAR\nBAR 0: current size: 8GB, supported: 256MB 8GB\n",
            "",
        )
        result = _resizable_bar([{"pci_bdf": "00000000:01:00.0"}])
        record = result["devices"][0]
        self.assertEqual(record["state"], "enabled")
        self.assertEqual(record["current_sizes"], ["8GB"])
        run.assert_called_once_with(("lspci", "-vv", "-s", "0000:01:00.0"))

    @patch("macvm_host.probe.Path.exists", return_value=False)
    @patch("macvm_host.probe.run_command")
    def test_resizable_bar_is_unknown_without_pci_capability(self, run, _exists) -> None:
        run.return_value = CommandResult(("lspci",), False, None, "", "not installed")
        result = _resizable_bar([{"pci_bdf": "0000:01:00.0"}])
        self.assertEqual(result["devices"][0]["state"], "unknown")


class HostCollectionTests(unittest.TestCase):
    @staticmethod
    def _command_result(command: tuple[str, ...], stdout: str, returncode: int = 0) -> CommandResult:
        return CommandResult(command, True, returncode, stdout, "")

    @patch("macvm_host.probe.Path.exists", return_value=True)
    @patch("macvm_host.probe.Path.is_dir", return_value=True)
    @patch("macvm_host.probe.platform.node", return_value="debug-host")
    @patch("macvm_host.probe.platform.machine", return_value="x86_64")
    @patch("macvm_host.probe.platform.release", return_value="6.12-test")
    @patch("macvm_host.probe.platform.system", return_value="Linux")
    @patch("macvm_host.probe.os.cpu_count", return_value=32)
    @patch("macvm_host.probe._read_text")
    @patch("macvm_host.probe.run_command")
    def test_collect_host_capabilities_combines_all_sources(
        self,
        run,
        read_text,
        _cpu_count,
        _system,
        _release,
        _machine,
        _node,
        _is_dir,
        _exists,
    ) -> None:
        def fake_read(path: Path) -> str:
            if str(path) == "/proc/cpuinfo":
                return "vendor_id: GenuineIntel\nmodel name: Debug CPU\nflags: avx2 aes vmx\n"
            if path.name == "nr_hugepages":
                return "2\n"
            if path.name == "enabled":
                return "always [madvise] never\n"
            return ""

        def fake_run(command, **_kwargs):
            command = tuple(command)
            if command == ("lscpu", "--json"):
                return self._command_result(
                    command,
                    '{"lscpu": ['
                    '{"field":"CPU(s):","data":"32"},'
                    '{"field":"Socket(s):","data":"1"},'
                    '{"field":"Core(s) per socket:","data":"16"}]}'
                )
            if command == ("lscpu", "-p=CPU,NODE"):
                return self._command_result(command, "# CPU,NODE\n0,0\n")
            if command[0] == "nvidia-smi":
                return self._command_result(
                    command,
                    "NVIDIA GeForce RTX 4060, GPU-A, 00000000:01:00.0, 555.42, 8188, 8192, 8\n",
                )
            if command == ("vulkaninfo", "--summary"):
                return self._command_result(
                    command,
                    "GPU0:\napiVersion = 1.3.280\ndeviceName = NVIDIA GeForce RTX 4060\n"
                    "deviceUUID = GPU-A\nvendorID = 0x10de\nVK_KHR_surface\n",
                )
            if command[0] == "lspci":
                return self._command_result(command, "Physical Resizable BAR\ncurrent size: 8GB,\n")
            raise AssertionError(f"unexpected command: {command}")

        read_text.side_effect = fake_read
        run.side_effect = fake_run
        result = collect_host_capabilities()

        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(result["host"]["system"], "Linux")
        self.assertEqual(result["cpu"]["physical_cores"], 16)
        self.assertTrue(result["cpu"]["virtualization"]["vmx"])
        self.assertTrue(result["cpu"]["virtualization"]["dev_kvm"])
        self.assertEqual(result["nvidia"]["devices"][0]["uuid"], "GPU-A")
        self.assertEqual(result["nvidia"]["resizable_bar"]["devices"][0]["state"], "enabled")
        self.assertEqual(result["vulkan"]["devices"][0]["vendor"], "nvidia")
        self.assertIn("VK_KHR_SURFACE", result["vulkan"]["extensions_reported_by_summary"])

    def test_write_capabilities_creates_stable_json_file(self) -> None:
        payload = {"schema_version": 1, "host": {"system": "Linux"}}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "nested" / "capabilities.json"
            with patch("macvm_host.probe.collect_host_capabilities", return_value=payload):
                returned = write_capabilities(output)
            decoded = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(returned, payload)
        self.assertEqual(decoded, payload)

    @patch("macvm_host.probe.Path.exists", return_value=False)
    @patch("macvm_host.probe.Path.is_dir", return_value=False)
    @patch("macvm_host.probe.platform.node", return_value="minimal-host")
    @patch("macvm_host.probe.platform.machine", return_value="x86_64")
    @patch("macvm_host.probe.platform.release", return_value="test")
    @patch("macvm_host.probe.platform.system", return_value="Linux")
    @patch("macvm_host.probe.os.cpu_count", return_value=1)
    @patch("macvm_host.probe._read_text", return_value="")
    @patch("macvm_host.probe.run_command")
    def test_missing_optional_host_tools_produce_explicit_empty_records(
        self,
        run,
        _read_text,
        _cpu_count,
        _system,
        _release,
        _machine,
        _node,
        _is_dir,
        _exists,
    ) -> None:
        run.side_effect = lambda command, **_kwargs: CommandResult(
            tuple(command), False, None, "", f"{command[0]}: command not found"
        )
        result = collect_host_capabilities()

        self.assertEqual(result["cpu"]["logical_threads"], 1)
        self.assertFalse(result["cpu"]["virtualization"]["dev_kvm"])
        self.assertEqual(result["nvidia"]["devices"], [])
        self.assertFalse(result["nvidia"]["command"]["available"])
        self.assertEqual(result["vulkan"]["devices"], [])
        self.assertFalse(result["vulkan"]["command"]["available"])


if __name__ == "__main__":
    unittest.main()
