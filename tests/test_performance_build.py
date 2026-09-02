from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PerformanceBuildContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = (ROOT / "scripts" / "build-performance.sh").read_text(encoding="utf-8")

    def test_uses_debug_environment_guard(self) -> None:
        self.assertIn('source "$SCRIPT_DIR/lib/require-debug-env.sh"', self.text)
        self.assertIn("macvm_require_debug_env", self.text)

    def test_only_accepts_explicit_generate_or_use_phases(self) -> None:
        self.assertIn('generate|use)', self.text)
        self.assertIn('*) usage ;;', self.text)

    def test_build_is_targeted_and_headless(self) -> None:
        for option in (
            "--target-list=aarch64-softmmu",
            "--enable-tcg",
            "--disable-hvf",
            "--disable-pvg",
            "--disable-docs",
            "--disable-gtk",
            "--disable-sdl",
            "--disable-opengl",
            "--disable-virglrenderer",
            "--disable-tools",
            "--disable-guest-agent",
            "--disable-plugins",
        ):
            with self.subTest(option=option):
                self.assertIn(option, self.text)

    def test_enables_measured_optimization_stack(self) -> None:
        for option in (
            "-Doptimization=3",
            "-Db_lto=true",
            "-Db_pgo=generate",
            "-Db_pgo=use",
            "-march=native",
            "-mtune=native",
            "-fno-semantic-interposition",
            "-fno-plt",
        ):
            with self.subTest(option=option):
                self.assertIn(option, self.text)

    def test_parallelism_is_capped_at_four(self) -> None:
        self.assertIn('NINJA_JOBS="${MACVM_BUILD_JOBS:-2}"', self.text)
        self.assertIn('[[ ! "$NINJA_JOBS" =~ ^[1-4]$ ]]', self.text)
        self.assertIn('"$NINJA_BIN" -j "$NINJA_JOBS"', self.text)

    def test_use_requires_collected_profiles(self) -> None:
        self.assertIn("-name '*.gcda'", self.text)
        self.assertIn('[[ "$profile_count" -eq 0 ]]', self.text)

    def test_generate_refuses_to_overwrite_an_existing_build(self) -> None:
        self.assertIn('[[ -e "$BUILD_DIR/build.ninja" ]]', self.text)
        self.assertIn("no directory is deleted automatically", self.text)

    def test_does_not_install_or_escalate_privileges(self) -> None:
        self.assertNotIn("sudo", self.text)
        self.assertNotIn("ninja install", self.text)
        self.assertNotIn("rm -rf", self.text)


if __name__ == "__main__":
    unittest.main()
