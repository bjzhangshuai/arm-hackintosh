from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import plistlib
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("macvm_probe_ipsw", ROOT / "tools" / "probe_ipsw.py")
assert SPEC and SPEC.loader
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


class IPSWProbeTests(unittest.TestCase):
    def make_ipsw(
        self,
        directory: str,
        *,
        version: object = "26.6",
        build: object = "25G72",
        product: str | None = "VirtualMac2,1",
        restore_bytes: bytes | None = None,
        build_bytes: bytes | None = None,
    ) -> Path:
        path = Path(directory) / "restore.ipsw"
        restore = {"ProductVersion": version, "ProductBuildVersion": build}
        manifest = {
            "SupportedProductTypes": [product] if product else ["Mac16,1"],
            "VirtualMachineMinCPUCount": 2,
            "VirtualMachineMinHostOS": "26.0",
            "VirtualMachineMinMemorySizeMB": 4096,
        }
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(
                "Restore.plist",
                restore_bytes if restore_bytes is not None else plistlib.dumps(restore),
            )
            archive.writestr(
                "BuildManifest.plist",
                build_bytes if build_bytes is not None else plistlib.dumps(manifest),
            )
            archive.writestr("payload.bin", b"payload")
        return path

    def test_accepts_matching_virtual_mac_restore(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_ipsw(directory)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            result = PROBE.inspect_ipsw(
                path,
                expected_size=path.stat().st_size,
                expected_sha256=digest.upper(),
                expected_version="26.6",
                expected_build="25G72",
                required_product="VirtualMac2,1",
            )
        self.assertEqual(result["virtual_mac_products"], ["VirtualMac2,1"])
        self.assertEqual(result["sha256"], digest)
        self.assertEqual(result["zip_members"], 3)

    def test_rejects_missing_file(self) -> None:
        with self.assertRaisesRegex(PROBE.IPSWError, "not a file"):
            PROBE.inspect_ipsw(Path("/definitely/missing/restore.ipsw"))

    def test_rejects_non_zip_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.ipsw"
            path.write_bytes(b"not a zip")
            with self.assertRaisesRegex(PROBE.IPSWError, "invalid IPSW ZIP"):
                PROBE.inspect_ipsw(path)

    def test_rejects_missing_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "restore.ipsw"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("Restore.plist", plistlib.dumps({}))
            with self.assertRaisesRegex(PROBE.IPSWError, "missing BuildManifest.plist"):
                PROBE.inspect_ipsw(path)

    def test_prefers_root_manifest_over_nested_restore_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_ipsw(directory)
            with zipfile.ZipFile(path, "a") as archive:
                archive.writestr("nested/Restore.plist", plistlib.dumps({}))
            result = PROBE.inspect_ipsw(path)
            self.assertEqual(result["product_version"], "26.6")

    def test_rejects_ambiguous_nested_manifest_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "restore.ipsw"
            restore = plistlib.dumps(
                {"ProductVersion": "26.6", "ProductBuildVersion": "25G72"}
            )
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("first/Restore.plist", restore)
                archive.writestr("second/Restore.plist", restore)
                archive.writestr("BuildManifest.plist", plistlib.dumps({}))
            with self.assertRaisesRegex(PROBE.IPSWError, "ambiguous Restore.plist"):
                PROBE.inspect_ipsw(path)

    def test_rejects_malformed_plist(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_ipsw(directory, restore_bytes=b"not a plist")
            with self.assertRaisesRegex(PROBE.IPSWError, "invalid Restore.plist"):
                PROBE.inspect_ipsw(path)

    def test_rejects_missing_string_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_ipsw(directory, version=26.6)
            with self.assertRaisesRegex(PROBE.IPSWError, "no ProductVersion"):
                PROBE.inspect_ipsw(path)

    def test_rejects_version_and_build_mismatches(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_ipsw(directory)
            with self.assertRaisesRegex(PROBE.IPSWError, "version mismatch"):
                PROBE.inspect_ipsw(path, expected_version="27.0")
            with self.assertRaisesRegex(PROBE.IPSWError, "build mismatch"):
                PROBE.inspect_ipsw(path, expected_build="26A5421a")

    def test_rejects_size_and_digest_mismatches(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_ipsw(directory)
            with self.assertRaisesRegex(PROBE.IPSWError, "size mismatch"):
                PROBE.inspect_ipsw(path, expected_size=1)
            with self.assertRaisesRegex(PROBE.IPSWError, "SHA-256 mismatch"):
                PROBE.inspect_ipsw(path, expected_sha256="0" * 64)

    def test_rejects_malformed_expected_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_ipsw(directory)
            with self.assertRaisesRegex(PROBE.IPSWError, "64 hexadecimal"):
                PROBE.inspect_ipsw(path, expected_sha256="xyz")

    def test_reports_absent_virtual_mac_and_can_require_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_ipsw(directory, product=None)
            result = PROBE.inspect_ipsw(path)
            self.assertEqual(result["virtual_mac_products"], [])
            with self.assertRaisesRegex(PROBE.IPSWError, "required product is absent"):
                PROBE.inspect_ipsw(path, required_product="VirtualMac2,1")


if __name__ == "__main__":
    unittest.main()
