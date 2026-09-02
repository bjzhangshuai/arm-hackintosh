from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "host"))

from macvm_host.gpu_policy import (  # noqa: E402
    GpuPolicyError,
    GpuSelection,
    is_software_device,
    select_vulkan_device,
)


class GpuPolicyTests(unittest.TestCase):
    def test_empty_device_list_is_an_error(self) -> None:
        with self.assertRaisesRegex(GpuPolicyError, "no Vulkan physical devices"):
            select_vulkan_device([], vendor="nvidia", device_name="RTX 4060")

    def test_selects_configured_nvidia_device(self) -> None:
        devices = [
            {"name": "llvmpipe (LLVM 19)", "vendor": "mesa", "device_type": "CPU"},
            {
                "name": "NVIDIA GeForce RTX 4060",
                "vendor": "nvidia",
                "device_type": "DISCRETE_GPU",
                "uuid": "GPU-123",
                "pci_bdf": "00000000:01:00.0",
            },
        ]
        selected = select_vulkan_device(
            devices,
            vendor="nvidia",
            device_name="NVIDIA GeForce RTX 4060",
        )
        self.assertEqual(selected.uuid, "GPU-123")
        self.assertFalse(selected.software)

    def test_matching_is_case_insensitive(self) -> None:
        selected = select_vulkan_device(
            [{"name": "NVIDIA GeForce RTX 4060", "vendor": "NVIDIA"}],
            vendor="nViDiA",
            device_name="geforce rtx 4060",
        )
        self.assertEqual(selected.name, "NVIDIA GeForce RTX 4060")

    def test_bdf_selects_one_of_two_same_name_devices(self) -> None:
        selected = select_vulkan_device(
            [
                {
                    "name": "NVIDIA GeForce RTX 4060",
                    "vendor": "nvidia",
                    "pci_bdf": "0000:01:00.0",
                },
                {
                    "name": "NVIDIA GeForce RTX 4060",
                    "vendor": "nvidia",
                    "pci_bdf": "0000:02:00.0",
                },
            ],
            vendor="nvidia",
            device_name="RTX 4060",
            pci_bdf="0000:02:00.0",
        )
        self.assertEqual(selected.pci_bdf, "0000:02:00.0")

    def test_uuid_selects_one_of_two_same_name_devices(self) -> None:
        selected = select_vulkan_device(
            [
                {"name": "RTX 4060", "vendor": "nvidia", "uuid": "GPU-A"},
                {"name": "RTX 4060", "vendor": "nvidia", "uuid": "GPU-B"},
            ],
            vendor="nvidia",
            device_name="RTX 4060",
            device_uuid="gpu-b",
        )
        self.assertEqual(selected.uuid, "GPU-B")

    def test_wrong_bdf_does_not_fall_back_to_same_named_gpu(self) -> None:
        with self.assertRaisesRegex(GpuPolicyError, "configured Vulkan device was not found"):
            select_vulkan_device(
                [{"name": "RTX 4060", "vendor": "nvidia", "pci_bdf": "0000:01:00.0"}],
                vendor="nvidia",
                device_name="RTX 4060",
                pci_bdf="0000:02:00.0",
            )

    def test_wrong_uuid_does_not_fall_back_to_same_named_gpu(self) -> None:
        with self.assertRaisesRegex(GpuPolicyError, "configured Vulkan device was not found"):
            select_vulkan_device(
                [{"name": "RTX 4060", "vendor": "nvidia", "uuid": "GPU-A"}],
                vendor="nvidia",
                device_name="RTX 4060",
                device_uuid="GPU-B",
            )

    def test_hardware_is_preferred_when_software_match_appears_first(self) -> None:
        selected = select_vulkan_device(
            [
                {"name": "NVIDIA compatibility llvmpipe", "vendor": "nvidia"},
                {"name": "NVIDIA GeForce RTX 4060", "vendor": "nvidia"},
            ],
            vendor="nvidia",
            device_name="NVIDIA",
        )
        self.assertEqual(selected.name, "NVIDIA GeForce RTX 4060")

    def test_missing_configured_gpu_reports_discovered_names(self) -> None:
        with self.assertRaisesRegex(GpuPolicyError, "Intel Arc, AMD Radeon"):
            select_vulkan_device(
                [
                    {"name": "Intel Arc", "vendor": "intel"},
                    {"name": "AMD Radeon", "vendor": "amd"},
                ],
                vendor="nvidia",
                device_name="RTX 4060",
            )

    def test_refuses_silent_software_fallback(self) -> None:
        with self.assertRaisesRegex(GpuPolicyError, "software Vulkan"):
            select_vulkan_device(
                [{"name": "llvmpipe", "vendor": "mesa", "device_type": "CPU"}],
                vendor="mesa",
                device_name="llvmpipe",
                hardware_required=True,
                allow_software_fallback=False,
            )

    def test_allows_explicit_development_fallback(self) -> None:
        selected = select_vulkan_device(
            [{"name": "lavapipe", "vendor": "mesa", "device_type": "CPU"}],
            vendor="mesa",
            device_name="lavapipe",
            hardware_required=False,
            allow_software_fallback=True,
        )
        self.assertTrue(selected.software)

    def test_hardware_not_required_still_needs_explicit_software_permission(self) -> None:
        with self.assertRaisesRegex(GpuPolicyError, "fallback is disabled"):
            select_vulkan_device(
                [{"name": "SwiftShader", "vendor": "google"}],
                vendor="google",
                device_name="SwiftShader",
                hardware_required=False,
                allow_software_fallback=False,
            )

    def test_all_known_software_markers_are_rejected(self) -> None:
        for name in (
            "llvmpipe (LLVM 19)",
            "Mesa lavapipe",
            "Google SwiftShader Device",
            "Generic Software Rasterizer",
        ):
            with self.subTest(name=name):
                self.assertTrue(is_software_device({"name": name}))

    def test_cpu_device_type_is_software_even_with_hardware_sounding_name(self) -> None:
        self.assertTrue(is_software_device({"name": "RTX 4060", "device_type": "CPU"}))
        self.assertTrue(
            is_software_device(
                {"name": "Generic Vulkan", "device_type": "PHYSICAL_DEVICE_TYPE_CPU"}
            )
        )

    def test_selection_serializes_all_identity_fields(self) -> None:
        selection = GpuSelection(
            name="RTX 4060",
            vendor="nvidia",
            uuid="GPU-1",
            pci_bdf="0000:01:00.0",
            software=False,
        )
        self.assertEqual(
            selection.to_dict(),
            {
                "name": "RTX 4060",
                "vendor": "nvidia",
                "uuid": "GPU-1",
                "pci_bdf": "0000:01:00.0",
                "software": False,
            },
        )


if __name__ == "__main__":
    unittest.main()
