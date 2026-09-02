from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import plistlib
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "macvm_extract_restore_bundle", ROOT / "tools" / "extract_restore_bundle.py"
)
assert SPEC and SPEC.loader
EXTRACT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXTRACT)


def component(path: str) -> dict[str, object]:
    return {"Info": {"Path": path}}


class RestoreBundleExtractionTests(unittest.TestCase):
    def make_ipsw(
        self,
        directory: str,
        *,
        product: str = "VirtualMac2,1",
        device_class: str = "vma2macosap",
        erase_ramdisk: str = "094-96989-085.dmg",
        upgrade_ramdisk: str = "094-97199-085.dmg",
        erase_trustcache: str = "Firmware/094-96989-085.dmg.trustcache",
        omit_role: str | None = None,
        unsafe_role_path: tuple[str, str] | None = None,
        include_duplicate_erase_identity: bool = False,
        omit_zip_member: str | None = None,
    ) -> tuple[Path, dict[str, bytes]]:
        payloads = {
            "kernelcache.release.vma2": b"kernelcache-erase-and-upgrade",
            "Firmware/all_flash/DeviceTree.vma2macosap.im4p": b"devicetree",
            erase_ramdisk: b"erase-ramdisk",
            upgrade_ramdisk: b"upgrade-ramdisk",
            erase_trustcache: b"erase-trustcache",
            "Firmware/094-97199-085.dmg.trustcache": b"upgrade-trustcache",
            "Firmware/094-96884-084.dmg.aea.trustcache": b"static-trustcache",
            "094-96884-084.dmg.aea": b"os-aea",
            "022-22048-085.dmg.aea": b"basesystem-aea",
        }

        def identity(variant: str, ramdisk: str, trustcache: str) -> dict[str, object]:
            manifest = {
                "RestoreKernelCache": component("kernelcache.release.vma2"),
                "RestoreDeviceTree": component("Firmware/all_flash/DeviceTree.vma2macosap.im4p"),
                "RestoreRamDisk": component(ramdisk),
                "RestoreTrustCache": component(trustcache),
                "StaticTrustCache": component("Firmware/094-96884-084.dmg.aea.trustcache"),
                "OS": component("094-96884-084.dmg.aea"),
                "BaseSystem": component("022-22048-085.dmg.aea"),
            }
            if omit_role:
                manifest.pop(omit_role, None)
            if unsafe_role_path is not None:
                role, unsafe_path = unsafe_role_path
                manifest[role] = component(unsafe_path)
            return {
                "Info": {
                    "DeviceClass": device_class,
                    "RestoreBehavior": "Erase" if variant == "erase" else "Update",
                    "Variant": (
                        "Customer Erase Install (IPSW)"
                        if variant == "erase"
                        else "Customer Upgrade Install (IPSW)"
                    ),
                    "VariantContents": [
                        "RestoreKernelCache",
                        "RestoreDeviceTree",
                        "RestoreRamDisk",
                        "RestoreTrustCache",
                    ],
                },
                "Manifest": manifest,
                "SupportedProductTypes": [product],
            }

        unsupported = {
            "Info": {
                "DeviceClass": "j999ap",
                "RestoreBehavior": "Erase",
                "Variant": "Customer Erase Install (IPSW)",
            },
            "Manifest": {
                "RestoreKernelCache": component("other-kernelcache"),
                "RestoreDeviceTree": component("other-dtree"),
                "RestoreRamDisk": component("other-ramdisk"),
                "RestoreTrustCache": component("other.trustcache"),
            },
            "SupportedProductTypes": ["Mac16,1"],
        }
        identities = [
            unsupported,
            identity("erase", erase_ramdisk, erase_trustcache),
            identity("upgrade", upgrade_ramdisk, "Firmware/094-97199-085.dmg.trustcache"),
        ]
        if include_duplicate_erase_identity:
            identities.append(identity("erase", erase_ramdisk, erase_trustcache))

        path = Path(directory) / "restore.ipsw"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(
                "Restore.plist",
                plistlib.dumps({"ProductVersion": "26.6", "ProductBuildVersion": "25G72"}),
            )
            archive.writestr(
                "BuildManifest.plist",
                plistlib.dumps(
                    {
                        "SupportedProductTypes": [product],
                        "BuildIdentities": identities,
                    }
                ),
            )
            for name, data in payloads.items():
                if name == omit_zip_member:
                    continue
                archive.writestr(name, data)
            archive.writestr("other-kernelcache", b"unsupported")
            archive.writestr("other-dtree", b"unsupported")
            archive.writestr("other-ramdisk", b"unsupported")
            archive.writestr("other.trustcache", b"unsupported")
        return path, payloads

    def test_extracts_erase_restore_assets_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ipsw, payloads = self.make_ipsw(directory)
            out_dir = Path(directory) / "bundle"
            result = EXTRACT.extract_restore_bundle(ipsw, out_dir=out_dir, variant="erase")

            self.assertEqual(result["product_version"], "26.6")
            self.assertEqual(result["product_build_version"], "25G72")
            self.assertEqual(result["selected_identity"]["index"], 1)
            self.assertEqual(result["selected_identity"]["restore_behavior"], "Erase")
            self.assertFalse(result["dry_run"])
            self.assertEqual(
                (out_dir / "kernelcache.release.vma2").read_bytes(),
                payloads["kernelcache.release.vma2"],
            )
            self.assertEqual((out_dir / "094-96989-085.dmg").read_bytes(), b"erase-ramdisk")
            self.assertEqual(
                (out_dir / "094-96989-085.dmg.trustcache").read_bytes(),
                b"erase-trustcache",
            )
            self.assertTrue((out_dir / "restore-bundle.json").is_file())
            self.assertIn("StaticTrustCache", result["optional_assets"])
            self.assertNotIn("sha256", result["optional_assets"]["OS"])

            ramdisk = result["assets"]["RestoreRamDisk"]
            expected_digest = hashlib.sha256(b"erase-ramdisk").hexdigest()
            self.assertEqual(ramdisk["sha256"], expected_digest)
            self.assertEqual(ramdisk["output_path"], str(out_dir / "094-96989-085.dmg"))

    def test_hashes_optional_assets_only_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ipsw, _ = self.make_ipsw(directory)
            result = EXTRACT.extract_restore_bundle(
                ipsw,
                out_dir=Path(directory) / "bundle",
                variant="erase",
                hash_optional_assets=True,
            )

            self.assertEqual(
                result["optional_assets"]["OS"]["sha256"],
                hashlib.sha256(b"os-aea").hexdigest(),
            )

    def test_selects_upgrade_restore_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ipsw, _ = self.make_ipsw(directory)
            out_dir = Path(directory) / "upgrade"
            result = EXTRACT.extract_restore_bundle(ipsw, out_dir=out_dir, variant="upgrade")

            self.assertEqual(result["selected_identity"]["index"], 2)
            self.assertEqual(result["assets"]["RestoreRamDisk"]["archive_path"], "094-97199-085.dmg")
            self.assertEqual((out_dir / "094-97199-085.dmg").read_bytes(), b"upgrade-ramdisk")

    def test_dry_run_hashes_assets_without_writing_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ipsw, _ = self.make_ipsw(directory)
            out_dir = Path(directory) / "dry-run"
            result = EXTRACT.extract_restore_bundle(
                ipsw,
                out_dir=out_dir,
                variant="erase",
                dry_run=True,
            )

            self.assertTrue(result["dry_run"])
            self.assertNotIn("metadata_path", result)
            self.assertFalse(out_dir.exists())
            self.assertNotIn("output_path", result["assets"]["RestoreRamDisk"])

    def test_refuses_missing_ipws_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(EXTRACT.RestoreBundleError, "not a file"):
                EXTRACT.extract_restore_bundle(Path(directory) / "missing.ipsw", out_dir=Path(directory))

    def test_refuses_non_zip_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.ipsw"
            path.write_bytes(b"not a zip")
            with self.assertRaisesRegex(EXTRACT.RestoreBundleError, "invalid IPSW ZIP"):
                EXTRACT.extract_restore_bundle(path, out_dir=Path(directory) / "bundle")

    def test_refuses_when_out_dir_is_missing_for_real_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ipsw, _ = self.make_ipsw(directory)
            with self.assertRaisesRegex(EXTRACT.RestoreBundleError, "--out-dir"):
                EXTRACT.extract_restore_bundle(ipsw, out_dir=None)

    def test_refuses_missing_build_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ipsw, _ = self.make_ipsw(directory, product="Mac16,1")
            with self.assertRaisesRegex(EXTRACT.RestoreBundleError, "no VirtualMac2,1"):
                EXTRACT.extract_restore_bundle(ipsw, out_dir=Path(directory) / "bundle")

    def test_refuses_identity_without_required_restore_asset(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ipsw, _ = self.make_ipsw(directory, omit_role="RestoreTrustCache")
            with self.assertRaisesRegex(EXTRACT.RestoreBundleError, "lacked required restore assets"):
                EXTRACT.extract_restore_bundle(ipsw, out_dir=Path(directory) / "bundle")

    def test_refuses_required_member_absent_from_zip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ipsw, _ = self.make_ipsw(directory, omit_zip_member="094-96989-085.dmg")
            with self.assertRaisesRegex(EXTRACT.RestoreBundleError, "RestoreRamDisk member is missing"):
                EXTRACT.extract_restore_bundle(ipsw, out_dir=Path(directory) / "bundle")

    def test_refuses_unsafe_manifest_member_paths(self) -> None:
        unsafe_paths = (
            "/absolute/ramdisk.dmg",
            "../ramdisk.dmg",
            "Firmware/../ramdisk.dmg",
            r"Firmware\\ramdisk.dmg",
        )
        for unsafe_path in unsafe_paths:
            with self.subTest(path=unsafe_path):
                with tempfile.TemporaryDirectory() as directory:
                    ipsw, _ = self.make_ipsw(
                        directory,
                        unsafe_role_path=("RestoreRamDisk", unsafe_path),
                    )
                    with self.assertRaisesRegex(EXTRACT.RestoreBundleError, "unsafe|non-POSIX"):
                        EXTRACT.extract_restore_bundle(ipsw, out_dir=Path(directory) / "bundle")

    def test_refuses_ambiguous_matching_restore_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ipsw, _ = self.make_ipsw(directory, include_duplicate_erase_identity=True)
            with self.assertRaisesRegex(EXTRACT.RestoreBundleError, "ambiguous"):
                EXTRACT.extract_restore_bundle(ipsw, out_dir=Path(directory) / "bundle")

    def test_idempotent_extract_accepts_same_existing_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ipsw, _ = self.make_ipsw(directory)
            out_dir = Path(directory) / "bundle"
            first = EXTRACT.extract_restore_bundle(ipsw, out_dir=out_dir, variant="erase")
            second = EXTRACT.extract_restore_bundle(ipsw, out_dir=out_dir, variant="erase")
            self.assertEqual(
                first["assets"]["RestoreRamDisk"]["sha256"],
                second["assets"]["RestoreRamDisk"]["sha256"],
            )

    def test_refuses_to_overwrite_different_existing_file_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ipsw, _ = self.make_ipsw(directory)
            out_dir = Path(directory) / "bundle"
            out_dir.mkdir()
            (out_dir / "094-96989-085.dmg").write_bytes(b"wrong")
            with self.assertRaisesRegex(EXTRACT.RestoreBundleError, "refusing to overwrite"):
                EXTRACT.extract_restore_bundle(ipsw, out_dir=out_dir, variant="erase")

            result = EXTRACT.extract_restore_bundle(ipsw, out_dir=out_dir, variant="erase", force=True)
            self.assertEqual((out_dir / "094-96989-085.dmg").read_bytes(), b"erase-ramdisk")
            self.assertEqual(result["assets"]["RestoreRamDisk"]["size"], len(b"erase-ramdisk"))


if __name__ == "__main__":
    unittest.main()
