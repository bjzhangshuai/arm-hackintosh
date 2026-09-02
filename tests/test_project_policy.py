from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ProjectPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = tomllib.loads((ROOT / "config" / "macvm.toml").read_text(encoding="utf-8"))

    def test_production_gpu_is_explicit_rtx_4060_vulkan(self) -> None:
        gpu = self.config["gpu"]
        self.assertEqual(gpu["backend"], "vulkan")
        self.assertEqual(gpu["vendor"], "nvidia")
        self.assertEqual(gpu["device_name"], "NVIDIA GeForce RTX 4060")
        self.assertTrue(gpu["hardware_required"])
        self.assertFalse(gpu["allow_software_fallback"])

    def test_cpu_baseline_is_tcg_multi_thread(self) -> None:
        machine = self.config["machine"]
        self.assertEqual(machine["accel"], "tcg")
        self.assertEqual(machine["tcg_thread"], "multi")
        self.assertGreaterEqual(machine["memory_gib"], 1)
        self.assertGreaterEqual(machine["vcpus"], 1)

    def test_repository_does_not_embed_guest_asset_paths(self) -> None:
        guest = self.config["guest"]
        for key in ("avpbooter", "aux", "disk"):
            with self.subTest(key=key):
                self.assertTrue(guest[key].startswith("/path/to/"))

    def test_guest_assets_are_gitignored(self) -> None:
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        for pattern in ("*.ipsw", "*.dmg", "*.img", "*.qcow2", "AVPBooter"):
            with self.subTest(pattern=pattern):
                self.assertIn(pattern, ignore)

    def test_required_phase_zero_documents_exist_and_are_nonempty(self) -> None:
        names = (
            "architecture.md",
            "upstream-analysis.md",
            "cpu-gap.md",
            "gpu-gap.md",
            "gpu-backend-decision.md",
            "performance-plan.md",
            "cpu-optimization.md",
            "test-environment.md",
        )
        for name in names:
            with self.subTest(document=name):
                path = ROOT / "docs" / name
                self.assertTrue(path.is_file())
                self.assertGreater(path.stat().st_size, 200)

    def test_build_is_isolated_and_disables_meson_wrap_fallback(self) -> None:
        text = (ROOT / "scripts" / "build.sh").read_text(encoding="utf-8")
        self.assertIn("MESON_WRAP_MODE=nodownload", text)
        self.assertIn("--target-list=aarch64-softmmu", text)
        self.assertIn("--enable-tcg", text)
        self.assertIn("--disable-hvf", text)
        self.assertIn("--disable-pvg", text)
        self.assertNotIn("sudo", text)
        self.assertNotIn("ninja install", text)

    def test_build_parallelism_defaults_to_two_and_is_capped_at_four(self) -> None:
        text = (ROOT / "scripts" / "build.sh").read_text(encoding="utf-8")
        self.assertIn('NINJA_JOBS="${MACVM_BUILD_JOBS:-2}"', text)
        self.assertIn('[[ ! "$NINJA_JOBS" =~ ^[1-4]$ ]]', text)
        self.assertIn('"$NINJA_BIN" -j "$NINJA_JOBS" qemu-system-aarch64', text)

    def test_machine_smoke_test_does_not_execute_dummy_firmware(self) -> None:
        text = (ROOT / "scripts" / "check-vmapple-machine.sh").read_text(encoding="utf-8")
        self.assertIn("-S", text)
        self.assertIn("-qmp stdio", text)
        self.assertIn('"execute":"query-status"', text)
        self.assertIn('"execute":"query-pci"', text)
        self.assertIn("vmapple-virtio-blk-pci", text)
        self.assertIn("-accel tcg,thread=multi", text)

    def test_machine_smoke_selects_the_apple_root_block_variant(self) -> None:
        text = (ROOT / "scripts" / "check-vmapple-machine.sh").read_text(encoding="utf-8")
        self.assertIn("vmapple-virtio-blk-pci,variant=root", text)
        self.assertNotIn("vmapple-virtio-blk-pci,drive=", text)

    def test_validation_record_does_not_claim_untested_gpu_support(self) -> None:
        text = (ROOT / "docs" / "test-environment.md").read_text(encoding="utf-8")
        self.assertIn("GPU, Vulkan", text)
        self.assertIn("**not tested**", text.lower())
        self.assertIn("no RTX 4060", text)
        self.assertIn("macOS boot | NOT RUN", text)

    def test_local_policy_helper_requires_the_iboot_nonce_width(self) -> None:
        text = (ROOT / "tools" / "fetch_local_policy.c").read_text(
            encoding="utf-8"
        )
        self.assertIn("#define LOCAL_POLICY_APNONCE_SIZE 32", text)
        self.assertIn(
            "ap_nonce_size != LOCAL_POLICY_APNONCE_SIZE",
            text,
        )
        self.assertIn("LocalPolicy ApNonce must be exactly", text)


if __name__ == "__main__":
    unittest.main()
