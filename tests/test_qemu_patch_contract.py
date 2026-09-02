from __future__ import annotations

from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches" / "qemu" / "0001-vmapple-enable-linux-tcg-machine-init.patch"
AES_PATCH = ROOT / "patches" / "qemu" / "0002-vmapple-aes-use-integer-constant-array-bound.patch"
BDIF_TRACE_PATCH = ROOT / "patches" / "qemu" / "0003-vmapple-bdif-trace-read-context.patch"
RESTORE_RND_PATCH = (
    ROOT / "patches" / "qemu" / "0004-vmapple-expose-restore-random-seed.patch"
)
USB_BDIF_PATCH = (
    ROOT / "patches" / "qemu" / "0005-vmapple-bdif-add-optional-usb-backend.patch"
)
SVC_A0_PSCI_PATCH = (
    ROOT / "patches" / "qemu" / "0006-vmapple-route-iboot-svc-a0-psci.patch"
)
IBOOT_LOW_SCRATCH_PATCH = (
    ROOT / "patches" / "qemu" / "0007-vmapple-map-iboot-low-scratch.patch"
)
BDIF_ACCESS_TRACE_PATCH = (
    ROOT / "patches" / "qemu" / "0008-vmapple-trace-bdif-device-registers.patch"
)
USB_RESTORE_CFG_PATCH = (
    ROOT / "patches" / "qemu" / "0009-vmapple-report-usb-restore-bdif-cfg.patch"
)
BDIF_VBLK_FAILURE_TRACE_PATCH = (
    ROOT / "patches" / "qemu" / "0010-vmapple-trace-bdif-vblk-command-failures.patch"
)
USB_RESTORE_PENDING_PATCH = (
    ROOT / "patches" / "qemu" / "0011-vmapple-keep-usb-restore-bdif-transfers-pending.patch"
)
USB_RESTORE_FIRST_PACKET_PATCH = (
    ROOT / "patches" / "qemu" / "0012-vmapple-add-debug-usb-restore-first-packet.patch"
)
USB_RESTORE_QUEUE_SELECTOR_PATCH = (
    ROOT / "patches" / "qemu" / "0013-vmapple-track-usb-restore-queue-selector.patch"
)
USB_RESTORE_OUT_PACKET_PATCH = (
    ROOT / "patches" / "qemu" / "0014-vmapple-handle-usb-restore-out-packets.patch"
)
USB_RESTORE_CHARDEV_PATCH = (
    ROOT / "patches" / "qemu" / "0015-vmapple-add-usb-restore-chardev.patch"
)
USB_RESTORE_CHARDEV_PRIME_PATCH = (
    ROOT / "patches" / "qemu" / "0016-vmapple-prime-usb-restore-chardev-input.patch"
)
BDIF_BLOCK_WRITE_PATCH = (
    ROOT / "patches" / "qemu" / "0017-vmapple-implement-bdif-block-writes.patch"
)
BOOT_PREP_MMIO_PATCH = (
    ROOT / "patches" / "qemu" / "0018-vmapple-map-boot-prep-mmio.patch"
)
CTRR_MMIO_PATCH = ROOT / "patches" / "qemu" / "0019-vmapple-map-ctrr-mmio.patch"
BDIF_QUEUE_NOTIFY_PATCH = (
    ROOT / "patches" / "qemu" / "0020-vmapple-model-bdif-queue-notify-status.patch"
)
XNU_EARLY_HVC_PATCH = (
    ROOT / "patches" / "qemu" / "0021-vmapple-handle-xnu-early-hvc-bootstrap.patch"
)
XNU_PAC_HVC_PATCH = (
    ROOT / "patches" / "qemu" / "0022-vmapple-handle-xnu-pac-hvc-family.patch"
)
XNU_HVC_DISCOVERY_PATCH = (
    ROOT / "patches" / "qemu" / "0023-vmapple-handle-pac-nop-oem-discovery.patch"
)
PSCI_PC_TRACE_PATCH = (
    ROOT / "patches" / "qemu" / "0024-arm-trace-psci-guest-pc.patch"
)
APPLE_ERROR_STATUS_SYSREG_PATCH = (
    ROOT
    / "patches"
    / "qemu"
    / "0025-vmapple-model-apple-error-status-sysregs.patch"
)
IMPLDEF_EL1_ACCESS_PATCH = (
    ROOT
    / "patches"
    / "qemu"
    / "0026-arm-cpreg-allow-opt-in-impldef-el1-access.patch"
)
VMAPPLE_PCIE_MSI_PATCH = (
    ROOT
    / "patches"
    / "qemu"
    / "0027-vmapple-model-pcie-msi-frame.patch"
)
VMAPPLE_LINUX_REIMS_VGPU_PATCH = (
    ROOT
    / "patches"
    / "qemu"
    / "0028-vmapple-connect-linux-reims-vgpu-mmio.patch"
)
MACVM_REIMS_KCONFIG_FIX_PATCH = (
    ROOT / "patches" / "qemu" / "0029-display-keep-macvm-kconfig-minimal.patch"
)
VMAPPLE_TARGET_CONFIG_PATCH = (
    ROOT / "patches" / "qemu" / "0030-vmapple-include-target-device-config.patch"
)
VMAPPLE_EL0_PAC_PATCH = (
    ROOT / "patches" / "qemu" / "0031-vmapple-model-el0-pac-key-domains.patch"
)
REIMS_GENERATOR_DEP_PATCH = (
    ROOT
    / "patches"
    / "qemu"
    / "0032-reims-mmio-generator-track-transform-script.patch"
)
REIMS_VGPU_MMIO_FIRMWARE_CONSOLE_PATCH = (
    ROOT
    / "patches"
    / "reims-vgpu"
    / "0005-mmio-paint-firmware-console.patch"
)
QEMU = ROOT / "third_party" / "qemu"


class QemuPatchContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.patch_text = PATCH.read_text(encoding="utf-8")

    def test_patch_changes_only_expected_qemu_files(self) -> None:
        changed = [
            line.removeprefix("diff --git a/").split(" b/", 1)[0]
            for line in self.patch_text.splitlines()
            if line.startswith("diff --git a/")
        ]
        self.assertEqual(
            changed,
            [
                "configs/devices/aarch64-softmmu/default.mak",
                "hw/vmapple/Kconfig",
                "hw/vmapple/vmapple.c",
            ],
        )

    def test_patch_enables_tcg_without_enabling_apple_framework_gpu(self) -> None:
        self.assertIn("+    depends on TCG || HVF", self.patch_text)
        self.assertIn("+    select MAC_PVG_MMIO if HVF", self.patch_text)
        self.assertIn("+    select UNIMP if !MAC_PVG_MMIO", self.patch_text)
        self.assertNotIn("diff --git a/hw/display/apple-gfx", self.patch_text)

    def test_patch_uses_tcg_cpu_and_aarch64_machine_filter(self) -> None:
        self.assertIn('+    mc->default_cpu_type = ARM_CPU_TYPE_NAME("max");', self.patch_text)
        self.assertIn("+    .interfaces    = aarch64_machine_interfaces,", self.patch_text)

    def test_pvg_placeholder_covers_both_guest_mmio_ranges(self) -> None:
        self.assertIn('create_unimplemented_device("vmapple-pvg"', self.patch_text)
        self.assertIn("VMAPPLE_APV_GFX", self.patch_text)
        self.assertIn('create_unimplemented_device("vmapple-iosfc"', self.patch_text)
        self.assertIn("VMAPPLE_APV_IOSFC", self.patch_text)

    def test_patch_matches_locked_qemu_tree_or_is_already_applied(self) -> None:
        qemu_default_mak = (
            QEMU / "configs" / "devices" / "aarch64-softmmu" / "default.mak"
        ).read_text(encoding="utf-8")
        qemu_kconfig = (QEMU / "hw" / "vmapple" / "Kconfig").read_text(
            encoding="utf-8"
        )
        qemu_vmapple = (QEMU / "hw" / "vmapple" / "vmapple.c").read_text(
            encoding="utf-8"
        )
        already_applied_under_later_patches = (
            "CONFIG_VMAPPLE=y" in qemu_default_mak
            and "depends on TCG || HVF" in qemu_kconfig
            and "select MAC_PVG_MMIO if HVF" in qemu_kconfig
            and "select UNIMP if !MAC_PVG_MMIO" in qemu_kconfig
            and '#include "hw/arm/machines-qom.h"' in qemu_vmapple
            and '#include "hw/misc/unimp.h"' in qemu_vmapple
            and 'create_unimplemented_device("vmapple-pvg"' in qemu_vmapple
            and 'create_unimplemented_device("vmapple-iosfc"' in qemu_vmapple
            and 'mc->default_cpu_type = ARM_CPU_TYPE_NAME("max");' in qemu_vmapple
            and ".interfaces    = aarch64_machine_interfaces," in qemu_vmapple
        )
        apply_check = subprocess.run(
            ("git", "-C", str(QEMU), "apply", "--check", str(PATCH)),
            check=False,
            capture_output=True,
            text=True,
        )
        reverse_check = subprocess.run(
            ("git", "-C", str(QEMU), "apply", "--reverse", "--check", str(PATCH)),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertTrue(
            apply_check.returncode == 0
            or reverse_check.returncode == 0
            or already_applied_under_later_patches,
            f"forward: {apply_check.stderr}\nreverse: {reverse_check.stderr}",
        )

    def test_reims_mmio_firmware_console_patch_stays_in_the_thin_shim(self) -> None:
        text = REIMS_VGPU_MMIO_FIRMWARE_CONSOLE_PATCH.read_text(encoding="utf-8")
        changed = [
            line.removeprefix("diff --git a/").split(" b/", 1)[0]
            for line in text.splitlines()
            if line.startswith("diff --git a/")
        ]
        self.assertEqual(changed, ["vendor/qemu/hw/display/reims-vgpu-mmio.c"])
        self.assertIn("reims_vgpu_mmio_copy_early_console", text)
        self.assertIn("reims_vgpu_qemu_efi_console_copy", text)
        self.assertIn("REIMS_VGPU_CONSOLE_FEED_FIRMWARE", text)
        self.assertIn("qemu_console_update_full(s->con);", text)

    def test_reims_mmio_firmware_console_patch_does_not_repush_product_frames(self) -> None:
        text = REIMS_VGPU_MMIO_FIRMWARE_CONSOLE_PATCH.read_text(encoding="utf-8")
        firmware_branch = text[text.index("REIMS_VGPU_CONSOLE_FEED_FIRMWARE") :]

        self.assertIn("reims_vgpu_mmio_copy_early_console(s)", firmware_branch)
        self.assertIn("s->new_frame_ready = false;", firmware_branch)
        self.assertIn("return true;", firmware_branch)

    def test_aes_compatibility_patch_is_minimal_and_uses_an_integer_constant(self) -> None:
        text = AES_PATCH.read_text(encoding="utf-8")
        changed = [
            line.removeprefix("diff --git a/").split(" b/", 1)[0]
            for line in text.splitlines()
            if line.startswith("diff --git a/")
        ]
        self.assertEqual(changed, ["hw/vmapple/aes.c"])
        self.assertIn("+    enum { MAX_LEN = 0x1000 };", text)
        self.assertIn('-    static const size_t MAX_LEN = 0x1000;', text)

    def test_apple_error_status_sysregs_are_exact_read_only_zero_models(self) -> None:
        text = APPLE_ERROR_STATUS_SYSREG_PATCH.read_text(encoding="utf-8")
        changed = [
            line.removeprefix("diff --git a/").split(" b/", 1)[0]
            for line in text.splitlines()
            if line.startswith("diff --git a/")
        ]
        self.assertEqual(changed, ["hw/vmapple/vmapple.c"])

        expected_registers = {
            "VMAPPLE_MMU_ERR_STS": ".opc0 = 3, .opc1 = 6, .crn = 15, .crm = 0, .opc2 = 0",
            "VMAPPLE_LLC_ERR_STS": ".opc0 = 3, .opc1 = 3, .crn = 15, .crm = 8, .opc2 = 0",
            "VMAPPLE_LLC_ERR_ADR": ".opc0 = 3, .opc1 = 3, .crn = 15, .crm = 9, .opc2 = 0",
            "VMAPPLE_LLC_ERR_INF": ".opc0 = 3, .opc1 = 3, .crn = 15, .crm = 10, .opc2 = 0",
            "VMAPPLE_LSU_ERR_STS": ".opc0 = 3, .opc1 = 3, .crn = 15, .crm = 0, .opc2 = 0",
            "VMAPPLE_FED_ERR_STS": ".opc0 = 3, .opc1 = 4, .crn = 15, .crm = 0, .opc2 = 0",
        }
        for name, encoding in expected_registers.items():
            with self.subTest(register=name):
                register_start = text.index(f'.name = "{name}"')
                register_end = text.index("},", register_start)
                definition = text[register_start:register_end]
                self.assertIn(encoding, definition)
                self.assertIn(".state = ARM_CP_STATE_AA64", definition)
                self.assertIn(".access = PL1_R", definition)
                self.assertIn(".type = ARM_CP_CONST", definition)
                self.assertIn(".resetvalue = 0", definition)

        self.assertEqual(text.count(".access = PL1_R, .type = ARM_CP_CONST"), 6)
        self.assertEqual(text.count(".resetvalue = 0"), 6)
        self.assertNotIn("CP_ANY", text)

    def test_apple_error_status_sysregs_are_vmapple_tcg_only(self) -> None:
        text = APPLE_ERROR_STATUS_SYSREG_PATCH.read_text(encoding="utf-8")

        self.assertIn('+#include "system/tcg.h"', text)
        self.assertIn('+#include "target/arm/cpregs.h"', text)
        self.assertIn("+    if (tcg_enabled()) {", text)
        self.assertIn(
            "+        define_arm_cp_regs(cpu, vmapple_tcg_error_status_regs);",
            text,
        )
        self.assertIn(
            "+        vmapple_register_tcg_error_status_regs(ARM_CPU(cpu));",
            text,
        )
        self.assertIn(
            'cpu = object_new(possible_cpus->cpus[n].type);\n+\n'
            "+        /* Must be registered before the CPU is realized. */",
            text,
        )
        self.assertNotIn("diff --git a/target/arm/", text)
        self.assertNotIn("diff --git a/system/", text)

    def test_impldef_el1_access_override_is_explicit_and_narrow(self) -> None:
        text = IMPLDEF_EL1_ACCESS_PATCH.read_text(encoding="utf-8")
        changed = [
            line.removeprefix("diff --git a/").split(" b/", 1)[0]
            for line in text.splitlines()
            if line.startswith("diff --git a/")
        ]
        self.assertEqual(
            changed,
            [
                "target/arm/cpregs.h",
                "target/arm/helper.c",
                "hw/vmapple/vmapple.c",
            ],
        )
        self.assertIn("+    ARM_CP_IMPLDEF_EL1           = 1 << 24", text)
        self.assertIn("+        !(r->type & ARM_CP_IMPLDEF_EL1)) {", text)
        self.assertEqual(
            text.count("ARM_CP_CONST | ARM_CP_IMPLDEF_EL1, .resetvalue = 0"),
            6,
        )
        self.assertNotIn("+            mask = PL0_RW", text)
        self.assertNotIn("-            mask = PL3_RW", text)
        self.assertNotIn("CP_ANY", text)

    def test_apple_error_status_sysreg_patch_matches_locked_tree_or_is_applied(
        self,
    ) -> None:
        text = (QEMU / "hw" / "vmapple" / "vmapple.c").read_text(
            encoding="utf-8"
        )
        already_applied = (
            'VMAPPLE_MMU_ERR_STS' in text
            and 'VMAPPLE_LLC_ERR_STS' in text
            and 'VMAPPLE_LLC_ERR_ADR' in text
            and 'VMAPPLE_LLC_ERR_INF' in text
            and 'VMAPPLE_LSU_ERR_STS' in text
            and 'VMAPPLE_FED_ERR_STS' in text
            and "if (tcg_enabled())" in text
            and "vmapple_register_tcg_error_status_regs(ARM_CPU(cpu));" in text
        )
        apply_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--check",
                str(APPLE_ERROR_STATUS_SYSREG_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        reverse_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--reverse",
                "--check",
                str(APPLE_ERROR_STATUS_SYSREG_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertTrue(
            apply_check.returncode == 0
            or reverse_check.returncode == 0
            or already_applied,
            f"forward: {apply_check.stderr}\nreverse: {reverse_check.stderr}",
        )

    def test_vmapple_pcie_msi_patch_models_the_device_tree_frame(self) -> None:
        text = VMAPPLE_PCIE_MSI_PATCH.read_text(encoding="utf-8")
        changed = [
            line.removeprefix("diff --git a/").split(" b/", 1)[0]
            for line in text.splitlines()
            if line.startswith("diff --git a/")
        ]
        self.assertEqual(
            changed,
            ["hw/intc/arm_gicv2m.c", "hw/vmapple/vmapple.c"],
        )
        self.assertIn(
            "+    [VMAPPLE_GIC_MSI] =            { 0x1fff0000, 0x00010000 },",
            text,
        )
        self.assertIn('+    dev = qdev_new("arm-gicv2m");', text)
        self.assertIn(
            '+    sysbus_mmio_map(sbd, 0, vms->memmap[VMAPPLE_GIC_MSI].base);',
            text,
        )
        self.assertIn("+    create_msi(vms);", text)

    def test_vmapple_pcie_msi_patch_uses_a_non_overlapping_vector_range(self) -> None:
        text = VMAPPLE_PCIE_MSI_PATCH.read_text(encoding="utf-8")
        self.assertIn("+#define VMAPPLE_MSI_IRQ_BASE 0x30", text)
        self.assertIn("+#define VMAPPLE_MSI_NUM_IRQS 64", text)
        self.assertIn(
            '+    qdev_prop_set_uint32(dev, "base-spi", VMAPPLE_MSI_IRQ_BASE);',
            text,
        )
        self.assertIn(
            '+    qdev_prop_set_uint32(dev, "num-spi", VMAPPLE_MSI_NUM_IRQS);',
            text,
        )
        self.assertIn(
            "+                                            VMAPPLE_MSI_IRQ_BASE + i));",
            text,
        )
        self.assertNotIn("VMAPPLE_PCIE] = 0x30", text)

    def test_vmapple_pcie_msi_typer_valid_bit_is_opt_in(self) -> None:
        text = VMAPPLE_PCIE_MSI_PATCH.read_text(encoding="utf-8")
        self.assertIn("+    bool msi_typer_valid;", text)
        self.assertIn("+        if (s->msi_typer_valid) {", text)
        self.assertIn("+            val |= 1U << 31;", text)
        self.assertIn(
            '+    DEFINE_PROP_BOOL("msi-typer-valid", ARMGICv2mState, '
            "msi_typer_valid, false),",
            text,
        )
        self.assertIn(
            '+    qdev_prop_set_bit(dev, "msi-typer-valid", true);',
            text,
        )
        self.assertNotIn(
            '+    DEFINE_PROP_BOOL("msi-typer-valid", ARMGICv2mState, '
            "msi_typer_valid, true),",
            text,
        )

    def test_vmapple_pcie_msi_patch_matches_locked_tree_or_is_applied(
        self,
    ) -> None:
        qemu_gicv2m = (QEMU / "hw" / "intc" / "arm_gicv2m.c").read_text(
            encoding="utf-8"
        )
        qemu_vmapple = (QEMU / "hw" / "vmapple" / "vmapple.c").read_text(
            encoding="utf-8"
        )
        already_applied = (
            "bool msi_typer_valid;" in qemu_gicv2m
            and 'DEFINE_PROP_BOOL("msi-typer-valid"' in qemu_gicv2m
            and "VMAPPLE_GIC_MSI" in qemu_vmapple
            and 'qdev_new("arm-gicv2m")' in qemu_vmapple
            and 'qdev_prop_set_bit(dev, "msi-typer-valid", true);' in qemu_vmapple
            and "create_msi(vms);" in qemu_vmapple
        )
        apply_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--check",
                str(VMAPPLE_PCIE_MSI_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        reverse_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--reverse",
                "--check",
                str(VMAPPLE_PCIE_MSI_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertTrue(
            apply_check.returncode == 0
            or reverse_check.returncode == 0
            or already_applied,
            f"forward: {apply_check.stderr}\nreverse: {reverse_check.stderr}",
        )

    def test_linux_reims_vgpu_patch_connects_both_vmapple_windows(self) -> None:
        text = VMAPPLE_LINUX_REIMS_VGPU_PATCH.read_text(encoding="utf-8")
        changed = [
            line.removeprefix("diff --git a/").split(" b/", 1)[0]
            for line in text.splitlines()
            if line.startswith("diff --git a/")
        ]
        self.assertEqual(
            changed,
            [
                "hw/display/Kconfig",
                "hw/display/meson.build",
                "hw/display/trace-events",
                "hw/vmapple/Kconfig",
                "hw/vmapple/vmapple.c",
            ],
        )
        self.assertIn("+config MACVM_REIMS_VGPU", text)
        self.assertIn("+    select MACVM_REIMS_VGPU if TCG", text)
        self.assertIn('+    gfx = SYS_BUS_DEVICE(qdev_new("reims-vgpu-mmio"));', text)
        self.assertIn(
            "+    sysbus_mmio_map(gfx, 0, vms->memmap[VMAPPLE_APV_GFX].base);",
            text,
        )
        self.assertIn(
            "+    sysbus_mmio_map(gfx, 1, vms->memmap[VMAPPLE_APV_IOSFC].base);",
            text,
        )

    def test_linux_reims_vgpu_patch_links_pinned_vulkan_backend(self) -> None:
        text = VMAPPLE_LINUX_REIMS_VGPU_PATCH.read_text(encoding="utf-8")
        self.assertIn("reims_vgpu_repo_dir = meson.global_source_root() / '..' / 'reims-vgpu'", text)
        self.assertIn("--locked", text)
        self.assertIn("--no-default-features --features backend-vulkan", text)
        self.assertIn("prepare_reims_qemu_mmio.py", text)
        self.assertNotIn("backend-metal", text)
        self.assertNotIn("host-window", text)
        self.assertNotIn("ninja install", text)
        self.assertNotIn("/usr/local", text)

    def test_linux_reims_vgpu_patch_matches_series_or_is_applied(self) -> None:
        display_kconfig = (QEMU / "hw" / "display" / "Kconfig").read_text(
            encoding="utf-8"
        )
        display_meson = (QEMU / "hw" / "display" / "meson.build").read_text(
            encoding="utf-8"
        )
        vmapple_kconfig = (QEMU / "hw" / "vmapple" / "Kconfig").read_text(
            encoding="utf-8"
        )
        vmapple = (QEMU / "hw" / "vmapple" / "vmapple.c").read_text(
            encoding="utf-8"
        )
        already_applied = (
            "config MACVM_REIMS_VGPU" in display_kconfig
            and "macvm-reims-vgpu-mmio-source" in display_meson
            and "select MACVM_REIMS_VGPU if TCG" in vmapple_kconfig
            and 'qdev_new("reims-vgpu-mmio")' in vmapple
        )
        forward = subprocess.run(
            ("git", "-C", str(QEMU), "apply", "--check", str(VMAPPLE_LINUX_REIMS_VGPU_PATCH)),
            check=False,
            capture_output=True,
            text=True,
        )
        reverse = subprocess.run(
            (
                "git", "-C", str(QEMU), "apply", "--reverse", "--check",
                str(VMAPPLE_LINUX_REIMS_VGPU_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        series = subprocess.run(
            (
                "git", "-C", str(QEMU), "apply", "--check", str(PATCH),
                str(VMAPPLE_LINUX_REIMS_VGPU_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertTrue(
            forward.returncode == 0
            or reverse.returncode == 0
            or series.returncode == 0
            or already_applied,
            f"forward: {forward.stderr}\nreverse: {reverse.stderr}\nseries: {series.stderr}",
        )

    def test_reims_kconfig_fix_removes_only_unsupported_help(self) -> None:
        text = MACVM_REIMS_KCONFIG_FIX_PATCH.read_text(encoding="utf-8")
        changed = [
            line.removeprefix("diff --git a/").split(" b/", 1)[0]
            for line in text.splitlines()
            if line.startswith("diff --git a/")
        ]
        self.assertEqual(changed, ["hw/display/Kconfig"])
        self.assertIn("-    help", text)
        self.assertIn("-      Linux host implementation", text)
        self.assertNotIn("+config ", text)

    def test_reims_kconfig_fix_matches_series_or_is_applied(self) -> None:
        kconfig = (QEMU / "hw" / "display" / "Kconfig").read_text(
            encoding="utf-8"
        )
        already_applied = (
            "config MACVM_REIMS_VGPU" in kconfig
            and "Linux host implementation of the VMApple PVG" not in kconfig
        )
        forward = subprocess.run(
            ("git", "-C", str(QEMU), "apply", "--check", str(MACVM_REIMS_KCONFIG_FIX_PATCH)),
            check=False,
            capture_output=True,
            text=True,
        )
        reverse = subprocess.run(
            (
                "git", "-C", str(QEMU), "apply", "--reverse", "--check",
                str(MACVM_REIMS_KCONFIG_FIX_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertTrue(
            forward.returncode == 0 or reverse.returncode == 0 or already_applied,
            f"forward: {forward.stderr}\nreverse: {reverse.stderr}",
        )

    def test_vmapple_target_config_patch_exposes_per_target_device_symbols(self) -> None:
        text = VMAPPLE_TARGET_CONFIG_PATCH.read_text(encoding="utf-8")
        changed = [
            line.removeprefix("diff --git a/").split(" b/", 1)[0]
            for line in text.splitlines()
            if line.startswith("diff --git a/")
        ]
        self.assertEqual(changed, ["hw/vmapple/vmapple.c"])
        self.assertIn('+#include CONFIG_DEVICES', text)
        self.assertIn("MACVM_REIMS_VGPU branch were removed", text)

    def test_vmapple_target_config_patch_matches_series_or_is_applied(self) -> None:
        vmapple = (QEMU / "hw" / "vmapple" / "vmapple.c").read_text(
            encoding="utf-8"
        )
        already_applied = '#include CONFIG_DEVICES' in vmapple
        forward = subprocess.run(
            ("git", "-C", str(QEMU), "apply", "--check", str(VMAPPLE_TARGET_CONFIG_PATCH)),
            check=False,
            capture_output=True,
            text=True,
        )
        reverse = subprocess.run(
            (
                "git", "-C", str(QEMU), "apply", "--reverse", "--check",
                str(VMAPPLE_TARGET_CONFIG_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertTrue(
            forward.returncode == 0 or reverse.returncode == 0 or already_applied,
            f"forward: {forward.stderr}\nreverse: {reverse.stderr}",
        )

    def test_aes_compatibility_patch_matches_locked_tree_or_is_already_applied(self) -> None:
        apply_check = subprocess.run(
            ("git", "-C", str(QEMU), "apply", "--check", str(AES_PATCH)),
            check=False,
            capture_output=True,
            text=True,
        )
        reverse_check = subprocess.run(
            ("git", "-C", str(QEMU), "apply", "--reverse", "--check", str(AES_PATCH)),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertTrue(
            apply_check.returncode == 0 or reverse_check.returncode == 0,
            f"forward: {apply_check.stderr}\nreverse: {reverse_check.stderr}",
        )

    def test_bdif_trace_patch_is_diagnostic_only(self) -> None:
        text = BDIF_TRACE_PATCH.read_text(encoding="utf-8")
        changed = [
            line.removeprefix("diff --git a/").split(" b/", 1)[0]
            for line in text.splitlines()
            if line.startswith("diff --git a/")
        ]
        self.assertEqual(changed, ["hw/vmapple/bdif.c", "hw/vmapple/trace-events"])
        self.assertIn("current_cpu ? current_cpu->cc->get_pc(current_cpu) : 0", text)
        self.assertIn("ldq_le_p(buf)", text)
        self.assertNotIn("dma_memory_write", text)
        self.assertNotIn("blk_pwrite", text)

    def test_bdif_trace_patch_matches_locked_tree_or_is_already_applied(self) -> None:
        qemu_bdif = (QEMU / "hw" / "vmapple" / "bdif.c").read_text(
            encoding="utf-8"
        )
        qemu_trace_events = (QEMU / "hw" / "vmapple" / "trace-events").read_text(
            encoding="utf-8"
        )
        already_applied_under_later_patches = (
            '#include "hw/core/cpu.h"' in qemu_bdif
            and "current_cpu ? current_cpu->cc->get_pc(current_cpu) : 0" in qemu_bdif
            and "ldq_le_p(buf)" in qemu_bdif
            and "bdif_vblk_read(const char *dev, uint64_t addr, uint64_t offset, uint32_t len, int r, uint64_t pc, uint64_t header)"
            in qemu_trace_events
        )
        apply_check = subprocess.run(
            ("git", "-C", str(QEMU), "apply", "--check", str(BDIF_TRACE_PATCH)),
            check=False,
            capture_output=True,
            text=True,
        )
        reverse_check = subprocess.run(
            ("git", "-C", str(QEMU), "apply", "--reverse", "--check", str(BDIF_TRACE_PATCH)),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertTrue(
            apply_check.returncode == 0
            or reverse_check.returncode == 0
            or already_applied_under_later_patches,
            f"forward: {apply_check.stderr}\nreverse: {reverse_check.stderr}",
        )

    def test_restore_random_patch_is_scoped_to_the_machine(self) -> None:
        text = RESTORE_RND_PATCH.read_text(encoding="utf-8")
        changed = [
            line.removeprefix("diff --git a/").split(" b/", 1)[0]
            for line in text.splitlines()
            if line.startswith("diff --git a/")
        ]
        self.assertEqual(changed, ["hw/vmapple/vmapple.c"])
        self.assertNotIn("hw/vmapple/cfg.c", text)
        self.assertNotIn("0x713471fb", text)

    def test_restore_random_patch_preserves_random_by_default(self) -> None:
        text = RESTORE_RND_PATCH.read_text(encoding="utf-8")
        self.assertIn("+    uint32_t rnd;", text)
        self.assertIn("+    uint32_t rnd = vms->rnd;", text)
        self.assertIn("+    if (!rnd) {", text)
        self.assertIn("qemu_guest_getrandom_nofail(&rnd, sizeof(rnd));", text)
        self.assertIn("zero selects random", text)

    def test_restore_random_patch_exposes_a_machine_property(self) -> None:
        text = RESTORE_RND_PATCH.read_text(encoding="utf-8")
        self.assertIn(
            '+    object_property_add_uint32_ptr(obj, "rnd", &vms->rnd,', text
        )
        self.assertIn("OBJ_PROP_FLAG_READWRITE", text)
        self.assertNotIn("DEFINE_PROP_UINT32", text)

    def test_restore_random_patch_matches_locked_tree_or_is_already_applied(self) -> None:
        apply_check = subprocess.run(
            ("git", "-C", str(QEMU), "apply", "--check", str(RESTORE_RND_PATCH)),
            check=False,
            capture_output=True,
            text=True,
        )
        reverse_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--reverse",
                "--check",
                str(RESTORE_RND_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertTrue(
            apply_check.returncode == 0 or reverse_check.returncode == 0,
            f"forward: {apply_check.stderr}\nreverse: {reverse_check.stderr}",
        )

    def test_bdif_usb_patch_exposes_an_optional_backend(self) -> None:
        text = USB_BDIF_PATCH.read_text(encoding="utf-8")
        changed = [
            line.removeprefix("diff --git a/").split(" b/", 1)[0]
            for line in text.splitlines()
            if line.startswith("diff --git a/")
        ]
        self.assertEqual(changed, ["hw/vmapple/bdif.c", "hw/vmapple/vmapple.c"])
        self.assertIn("+    BlockBackend *usb;", text)
        self.assertIn("+    case DEVID_USB:", text)
        self.assertIn('+    DEFINE_PROP_DRIVE("usb", VMAppleBdifState, usb),', text)
        self.assertIn("+    DriveInfo *di_usb = drive_get(IF_PFLASH, 0, 2);", text)
        self.assertIn("+static BlockBackend *bdif_backend_for_devid", text)
        self.assertIn("+    bool present = bdif_backend_for_devid(s, devid) != NULL;", text)
        self.assertIn("+        ret = present ? REG_STATUS_ACTIVE : 0;", text)
        self.assertIn("+        if (blk) {", text)

    def test_bdif_usb_patch_preserves_existing_aux_and_root_requirements(self) -> None:
        text = USB_BDIF_PATCH.read_text(encoding="utf-8")
        self.assertNotIn('error_report("No usb device', text)
        self.assertIn('error_report("No AUX device', text)
        self.assertIn("DriveInfo *di_root = drive_get(IF_PFLASH, 0, 1);", text)
        self.assertIn('qdev_prop_set_drive(DEVICE(bdif), "root"', text)
        self.assertIn('+    if (di_usb) {', text)
        self.assertIn('+                            blk_by_legacy_dinfo(di_usb));', text)

    def test_bdif_usb_patch_matches_patch_series_or_is_already_applied(self) -> None:
        qemu_bdif = (QEMU / "hw" / "vmapple" / "bdif.c").read_text(
            encoding="utf-8"
        )
        qemu_vmapple = (QEMU / "hw" / "vmapple" / "vmapple.c").read_text(
            encoding="utf-8"
        )
        already_applied_under_later_patches = (
            "BlockBackend *usb;" in qemu_bdif
            and "case DEVID_USB:" in qemu_bdif
            and 'DEFINE_PROP_DRIVE("usb", VMAppleBdifState, usb),' in qemu_bdif
            and "DriveInfo *di_usb = drive_get(IF_PFLASH, 0, 2);" in qemu_vmapple
            and 'qdev_prop_set_drive(DEVICE(bdif), "usb"' in qemu_vmapple
        )
        reverse_check = subprocess.run(
            ("git", "-C", str(QEMU), "apply", "--reverse", "--check", str(USB_BDIF_PATCH)),
            check=False,
            capture_output=True,
            text=True,
        )
        current_forward_check = subprocess.run(
            ("git", "-C", str(QEMU), "apply", "--check", str(USB_BDIF_PATCH)),
            check=False,
            capture_output=True,
            text=True,
        )
        series_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--check",
                str(PATCH),
                str(AES_PATCH),
                str(BDIF_TRACE_PATCH),
                str(RESTORE_RND_PATCH),
                str(USB_BDIF_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertTrue(
            reverse_check.returncode == 0
            or current_forward_check.returncode == 0
            or series_check.returncode == 0
            or already_applied_under_later_patches,
            "reverse: "
            f"{reverse_check.stderr}\ncurrent forward: {current_forward_check.stderr}\n"
            f"series: {series_check.stderr}",
        )

    def test_svc_a0_psci_patch_is_scoped_to_tcg_and_vmapple(self) -> None:
        text = SVC_A0_PSCI_PATCH.read_text(encoding="utf-8")
        changed = [
            line.removeprefix("diff --git a/").split(" b/", 1)[0]
            for line in text.splitlines()
            if line.startswith("diff --git a/")
        ]
        self.assertEqual(
            changed,
            ["hw/vmapple/vmapple.c", "target/arm/cpu.h", "target/arm/tcg/psci.c"],
        )
        self.assertNotIn("target/arm/hvf", text)
        self.assertNotIn("target/arm/kvm", text)

    def test_svc_a0_psci_patch_is_opt_in_and_keeps_existing_default(self) -> None:
        text = SVC_A0_PSCI_PATCH.read_text(encoding="utf-8")
        self.assertIn("+    bool svc_a0_psci;", text)
        self.assertIn('+    object_property_add_bool(obj, "svc-a0-psci"', text)
        self.assertIn("+                                vms->svc_a0_psci ? QEMU_PSCI_CONDUIT_SVC_A0", text)
        self.assertIn("+                                                  : QEMU_PSCI_CONDUIT_HVC,", text)
        self.assertIn("default off", text)

    def test_svc_a0_psci_patch_filters_by_exception_immediate_and_function_id(self) -> None:
        text = SVC_A0_PSCI_PATCH.read_text(encoding="utf-8")
        self.assertIn("+    QEMU_PSCI_CONDUIT_SVC_A0 = 3,", text)
        self.assertIn("+    case EXCP_SWI:", text)
        self.assertIn("+           syn_get_ec(env->exception.syndrome) == EC_AA64_SVC &&", text)
        self.assertIn("+           FIELD_EX32(env->exception.syndrome, ISS_IMM16, IMM16) == 0xa0 &&", text)
        self.assertIn("+           arm_is_implemented_psci_function(env->xregs[0]);", text)
        self.assertIn("+    case QEMU_PSCI_0_2_FN_PSCI_VERSION:", text)
        self.assertIn("+    case QEMU_PSCI_0_2_FN_SYSTEM_RESET:", text)
        self.assertIn("+    case QEMU_PSCI_0_2_FN_SYSTEM_OFF:", text)

    def test_svc_a0_psci_patch_matches_patch_series_or_is_already_applied(self) -> None:
        qemu_vmapple = (QEMU / "hw" / "vmapple" / "vmapple.c").read_text(
            encoding="utf-8"
        )
        qemu_cpu_h = (QEMU / "target" / "arm" / "cpu.h").read_text(encoding="utf-8")
        qemu_psci = (QEMU / "target" / "arm" / "tcg" / "psci.c").read_text(
            encoding="utf-8"
        )
        already_applied_under_later_patches = (
            "bool svc_a0_psci;" in qemu_vmapple
            and 'object_property_add_bool(obj, "svc-a0-psci"' in qemu_vmapple
            and "QEMU_PSCI_CONDUIT_SVC_A0 = 3," in qemu_cpu_h
            and "arm_is_iboot_svc_a0_psci_call" in qemu_psci
        )
        reverse_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--reverse",
                "--check",
                str(SVC_A0_PSCI_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        current_forward_check = subprocess.run(
            ("git", "-C", str(QEMU), "apply", "--check", str(SVC_A0_PSCI_PATCH)),
            check=False,
            capture_output=True,
            text=True,
        )
        series_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--check",
                str(PATCH),
                str(AES_PATCH),
                str(BDIF_TRACE_PATCH),
                str(RESTORE_RND_PATCH),
                str(USB_BDIF_PATCH),
                str(SVC_A0_PSCI_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertTrue(
            reverse_check.returncode == 0
            or current_forward_check.returncode == 0
            or series_check.returncode == 0
            or already_applied_under_later_patches,
            "reverse: "
            f"{reverse_check.stderr}\ncurrent forward: {current_forward_check.stderr}\n"
            f"series: {series_check.stderr}",
        )

    def test_iboot_low_scratch_patch_is_opt_in_and_maps_exact_window(self) -> None:
        text = IBOOT_LOW_SCRATCH_PATCH.read_text(encoding="utf-8")
        changed = [
            line.removeprefix("diff --git a/").split(" b/", 1)[0]
            for line in text.splitlines()
            if line.startswith("diff --git a/")
        ]
        self.assertEqual(changed, ["hw/vmapple/vmapple.c"])
        self.assertIn("+    bool iboot_low_scratch;", text)
        self.assertIn("+    MemoryRegion iboot_low_scratch_mr;", text)
        self.assertIn("+    [VMAPPLE_IBOOT_LOW_SCRATCH] =  { 0x004fc000, 0x00004000 },", text)
        self.assertIn("+    if (!vms->iboot_low_scratch) {", text)
        self.assertIn(
            '+    memory_region_init_ram(&vms->iboot_low_scratch_mr, NULL,',
            text,
        )
        self.assertIn(
            '+                           "vmapple.iboot-low-scratch", size, &error_fatal);',
            text,
        )
        self.assertIn("+    memory_region_add_subregion(sysmem, base, &vms->iboot_low_scratch_mr);", text)
        self.assertIn("+    create_iboot_low_scratch(vms, sysmem);", text)
        self.assertIn('+    object_property_add_bool(obj, "iboot-low-scratch"', text)
        self.assertIn("Default false keeps the upstream vmapple memory map unchanged", text)

    def test_iboot_low_scratch_patch_matches_patch_series_or_is_already_applied(self) -> None:
        qemu_vmapple = (QEMU / "hw" / "vmapple" / "vmapple.c").read_text(
            encoding="utf-8"
        )
        already_applied = (
            "VMAPPLE_IBOOT_LOW_SCRATCH" in qemu_vmapple
            and '"vmapple.iboot-low-scratch"' in qemu_vmapple
            and "create_iboot_low_scratch(vms, sysmem);" in qemu_vmapple
            and 'object_property_add_bool(obj, "iboot-low-scratch"' in qemu_vmapple
        )
        reverse_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--reverse",
                "--check",
                str(IBOOT_LOW_SCRATCH_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        current_forward_check = subprocess.run(
            ("git", "-C", str(QEMU), "apply", "--check", str(IBOOT_LOW_SCRATCH_PATCH)),
            check=False,
            capture_output=True,
            text=True,
        )
        series_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--check",
                str(PATCH),
                str(AES_PATCH),
                str(BDIF_TRACE_PATCH),
                str(RESTORE_RND_PATCH),
                str(USB_BDIF_PATCH),
                str(SVC_A0_PSCI_PATCH),
                str(IBOOT_LOW_SCRATCH_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertTrue(
            reverse_check.returncode == 0
            or current_forward_check.returncode == 0
            or series_check.returncode == 0
            or already_applied,
            "reverse: "
            f"{reverse_check.stderr}\ncurrent forward: {current_forward_check.stderr}\n"
            f"series: {series_check.stderr}",
        )

    def test_bdif_access_trace_patch_is_diagnostic_only(self) -> None:
        text = BDIF_ACCESS_TRACE_PATCH.read_text(encoding="utf-8")
        changed = [
            line.removeprefix("diff --git a/").split(" b/", 1)[0]
            for line in text.splitlines()
            if line.startswith("diff --git a/")
        ]
        self.assertEqual(changed, ["hw/vmapple/bdif.c", "hw/vmapple/trace-events"])
        self.assertIn("+static const char *bdif_devid_name(uint64_t devid)", text)
        self.assertIn('+        return "usb";', text)
        self.assertIn("+static const char *bdif_reg_name(hwaddr offset)", text)
        self.assertIn('+        return "cmd";', text)
        self.assertIn('+    bdif_trace_access("read", devid, offset, size, ret);', text)
        self.assertIn('+    bdif_trace_access("write", devid, offset, size, value);', text)
        self.assertIn("+        trace_bdif_vblk_read(bdif_devid_name(devid),", text)
        self.assertIn("+bdif_access(", text)
        self.assertNotIn("blk_pwrite", text)
        self.assertNotIn("+        ret =", text)
        self.assertNotIn("+        vblk_cmd", text)

    def test_bdif_access_trace_patch_matches_patch_series_or_is_already_applied(self) -> None:
        qemu_bdif = (QEMU / "hw" / "vmapple" / "bdif.c").read_text(
            encoding="utf-8"
        )
        qemu_trace_events = (QEMU / "hw" / "vmapple" / "trace-events").read_text(
            encoding="utf-8"
        )
        already_applied_under_later_patches = (
            "bdif_devid_name" in qemu_bdif
            and "bdif_reg_name" in qemu_bdif
            and 'bdif_trace_access("read", devid, offset, size, ret);' in qemu_bdif
            and 'bdif_trace_access("write", devid, offset, size, value);' in qemu_bdif
            and "bdif_access(const char *op, const char *dev, const char *reg"
            in qemu_trace_events
        )
        reverse_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--reverse",
                "--check",
                str(BDIF_ACCESS_TRACE_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        current_forward_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--check",
                str(BDIF_ACCESS_TRACE_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        series_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--check",
                str(PATCH),
                str(AES_PATCH),
                str(BDIF_TRACE_PATCH),
                str(RESTORE_RND_PATCH),
                str(USB_BDIF_PATCH),
                str(SVC_A0_PSCI_PATCH),
                str(IBOOT_LOW_SCRATCH_PATCH),
                str(BDIF_ACCESS_TRACE_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertTrue(
            reverse_check.returncode == 0
            or current_forward_check.returncode == 0
            or series_check.returncode == 0
            or already_applied_under_later_patches,
            "reverse: "
            f"{reverse_check.stderr}\ncurrent forward: {current_forward_check.stderr}\n"
            f"series: {series_check.stderr}",
        )

    def test_usb_restore_cfg_patch_is_scoped_to_usb_bdif(self) -> None:
        text = USB_RESTORE_CFG_PATCH.read_text(encoding="utf-8")
        changed = [
            line.removeprefix("diff --git a/").split(" b/", 1)[0]
            for line in text.splitlines()
            if line.startswith("diff --git a/")
        ]
        self.assertEqual(changed, ["hw/vmapple/bdif.c"])
        self.assertIn("+#define REG_CFG_USB_RESTORE   0x1a01", text)
        self.assertIn("+static uint64_t bdif_cfg_for_devid", text)
        self.assertIn("+    if (!bdif_backend_for_devid(s, devid)) {", text)
        self.assertIn("+        return 0;", text)
        self.assertIn("+    case DEVID_USB:", text)
        self.assertIn("+        return REG_CFG_USB_RESTORE;", text)
        self.assertIn("+        return REG_CFG_ACTIVE;", text)
        self.assertIn("+        ret = bdif_cfg_for_devid(s, devid);", text)
        self.assertNotIn("+        return 0x1a01;", text)
        self.assertNotIn("DEVID_AUX:\n+        return REG_CFG_USB_RESTORE", text)
        self.assertNotIn("DEVID_ROOT:\n+        return REG_CFG_USB_RESTORE", text)

    def test_usb_restore_cfg_patch_matches_patch_series_or_is_already_applied(self) -> None:
        reverse_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--reverse",
                "--check",
                str(USB_RESTORE_CFG_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        current_forward_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--check",
                str(USB_RESTORE_CFG_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        series_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--check",
                str(PATCH),
                str(AES_PATCH),
                str(BDIF_TRACE_PATCH),
                str(RESTORE_RND_PATCH),
                str(USB_BDIF_PATCH),
                str(SVC_A0_PSCI_PATCH),
                str(IBOOT_LOW_SCRATCH_PATCH),
                str(BDIF_ACCESS_TRACE_PATCH),
                str(USB_RESTORE_CFG_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertTrue(
            reverse_check.returncode == 0
            or current_forward_check.returncode == 0
            or series_check.returncode == 0,
            "reverse: "
            f"{reverse_check.stderr}\ncurrent forward: {current_forward_check.stderr}\n"
            f"series: {series_check.stderr}",
        )

    def test_bdif_vblk_failure_trace_patch_is_diagnostic_and_safe(self) -> None:
        text = BDIF_VBLK_FAILURE_TRACE_PATCH.read_text(encoding="utf-8")
        changed = [
            line.removeprefix("diff --git a/").split(" b/", 1)[0]
            for line in text.splitlines()
            if line.startswith("diff --git a/")
        ]
        self.assertEqual(changed, ["hw/vmapple/bdif.c", "hw/vmapple/trace-events"])
        self.assertIn("+    uint64_t guest_pc = bdif_guest_pc();", text)
        self.assertIn('+        trace_bdif_vblk_error(bdif_devid_name(devid), "req-dma"', text)
        self.assertIn("+        return;", text)
        self.assertIn(
            "+    trace_bdif_vblk_cmd(bdif_devid_name(devid), gp_addr, guest_pc);",
            text,
        )
        self.assertIn('+    trace_bdif_vblk_desc(bdif_devid_name(devid), "sector"', text)
        self.assertIn('+    trace_bdif_vblk_desc(bdif_devid_name(devid), "data"', text)
        self.assertIn('+    trace_bdif_vblk_desc(bdif_devid_name(devid), "retval"', text)
        self.assertIn('+        trace_bdif_vblk_error(bdif_devid_name(devid), "sector-len"', text)
        self.assertIn('+        trace_bdif_vblk_error(bdif_devid_name(devid), "sector-dma"', text)
        self.assertIn("+    trace_bdif_vblk_sector(bdif_devid_name(devid), sector.sector, off,", text)
        self.assertIn('+        trace_bdif_vblk_error(bdif_devid_name(devid), "data-len"', text)
        self.assertIn('+            trace_bdif_vblk_error(bdif_devid_name(devid), "read-failed"', text)
        self.assertIn('+            trace_bdif_vblk_error(bdif_devid_name(devid), "data-dma"', text)
        self.assertIn('+        trace_bdif_vblk_error(bdif_devid_name(devid), "write-unsupported"', text)
        self.assertIn('+        trace_bdif_vblk_error(bdif_devid_name(devid), "data-flags"', text)
        self.assertIn("+bdif_vblk_cmd(", text)
        self.assertIn("+bdif_vblk_desc(", text)
        self.assertIn("+bdif_vblk_sector(", text)
        self.assertIn("+bdif_vblk_error(", text)
        self.assertNotIn("blk_pwrite", text)

    def test_bdif_vblk_failure_trace_events_respect_qemu_arg_limit(self) -> None:
        text = BDIF_VBLK_FAILURE_TRACE_PATCH.read_text(encoding="utf-8")
        for line in text.splitlines():
            if not line.startswith("+bdif_vblk_"):
                continue
            args = line.split("(", 1)[1].split(")", 1)[0].strip()
            argc = 0 if args in {"", "void"} else args.count(",") + 1
            self.assertLessEqual(argc, 10, line)

    def test_bdif_vblk_failure_trace_patch_matches_patch_series_or_is_already_applied(self) -> None:
        qemu_bdif = (QEMU / "hw" / "vmapple" / "bdif.c").read_text(
            encoding="utf-8"
        )
        qemu_trace_events = (QEMU / "hw" / "vmapple" / "trace-events").read_text(
            encoding="utf-8"
        )
        already_applied_under_later_patches = (
            "trace_bdif_vblk_cmd" in qemu_bdif
            and "trace_bdif_vblk_desc" in qemu_bdif
            and "trace_bdif_vblk_error" in qemu_bdif
            and "trace_bdif_vblk_sector" in qemu_bdif
            and "bdif_vblk_cmd(const char *dev" in qemu_trace_events
            and "bdif_vblk_desc(const char *dev" in qemu_trace_events
            and "bdif_vblk_error(const char *dev" in qemu_trace_events
        )
        reverse_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--reverse",
                "--check",
                str(BDIF_VBLK_FAILURE_TRACE_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        current_forward_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--check",
                str(BDIF_VBLK_FAILURE_TRACE_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        series_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--check",
                str(PATCH),
                str(AES_PATCH),
                str(BDIF_TRACE_PATCH),
                str(RESTORE_RND_PATCH),
                str(USB_BDIF_PATCH),
                str(SVC_A0_PSCI_PATCH),
                str(IBOOT_LOW_SCRATCH_PATCH),
                str(BDIF_ACCESS_TRACE_PATCH),
                str(USB_RESTORE_CFG_PATCH),
                str(BDIF_VBLK_FAILURE_TRACE_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertTrue(
            reverse_check.returncode == 0
            or current_forward_check.returncode == 0
            or series_check.returncode == 0
            or already_applied_under_later_patches,
            "reverse: "
            f"{reverse_check.stderr}\ncurrent forward: {current_forward_check.stderr}\n"
            f"series: {series_check.stderr}",
        )

    def test_usb_restore_pending_patch_is_scoped_to_usb_restore(self) -> None:
        text = USB_RESTORE_PENDING_PATCH.read_text(encoding="utf-8")
        changed = [
            line.removeprefix("diff --git a/").split(" b/", 1)[0]
            for line in text.splitlines()
            if line.startswith("diff --git a/")
        ]
        self.assertEqual(changed, ["hw/vmapple/bdif.c"])
        self.assertIn("+    bool usb_restore_pending;", text)
        self.assertIn("+#define VBLK_USB_RESTORE_FLAGS 0x00020001", text)
        self.assertIn("+static bool bdif_is_usb_restore_transfer", text)
        self.assertIn("+    if (devid != DEVID_USB) {", text)
        self.assertIn("+           req->sector.len > sizeof(VblkSector) &&", text)
        self.assertIn("+           req->data.addr == 0 && req->data.len == 0 &&", text)
        self.assertIn("+           req->retval.addr == 0 && req->retval.len == 0 &&", text)
        self.assertIn("+        if (devid == DEVID_USB && s->usb_restore_pending) {", text)
        self.assertIn("+            ret = 0;", text)
        self.assertIn("+        s->usb_restore_pending = true;", text)
        self.assertIn('+        trace_bdif_vblk_error(bdif_devid_name(devid), "usb-restore-pending"', text)
        self.assertIn("+        return;", text)
        self.assertIn("-static void vblk_cmd(uint64_t devid, BlockBackend *blk, uint64_t gp_addr,", text)
        self.assertIn("+static void vblk_cmd(VMAppleBdifState *s, uint64_t devid, BlockBackend *blk,", text)
        self.assertIn("+            vblk_cmd(s, devid, blk, value, 0x0);", text)
        self.assertNotIn("blk_pwrite", text)

    def test_usb_restore_pending_patch_matches_patch_series_or_is_already_applied(self) -> None:
        qemu_bdif = (QEMU / "hw" / "vmapple" / "bdif.c").read_text(
            encoding="utf-8"
        )
        already_applied_under_later_patches = (
            "bool usb_restore_pending;" in qemu_bdif
            and "bdif_is_usb_restore_transfer" in qemu_bdif
            and "VBLK_USB_RESTORE_FLAGS" in qemu_bdif
            and "s->usb_restore_pending = true;" in qemu_bdif
            and "usb-restore-pending" in qemu_bdif
        )
        reverse_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--reverse",
                "--check",
                str(USB_RESTORE_PENDING_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        current_forward_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--check",
                str(USB_RESTORE_PENDING_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        series_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--check",
                str(PATCH),
                str(AES_PATCH),
                str(BDIF_TRACE_PATCH),
                str(RESTORE_RND_PATCH),
                str(USB_BDIF_PATCH),
                str(SVC_A0_PSCI_PATCH),
                str(IBOOT_LOW_SCRATCH_PATCH),
                str(BDIF_ACCESS_TRACE_PATCH),
                str(USB_RESTORE_CFG_PATCH),
                str(BDIF_VBLK_FAILURE_TRACE_PATCH),
                str(USB_RESTORE_PENDING_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertTrue(
            reverse_check.returncode == 0
            or current_forward_check.returncode == 0
            or series_check.returncode == 0
            or already_applied_under_later_patches,
            "reverse: "
            f"{reverse_check.stderr}\ncurrent forward: {current_forward_check.stderr}\n"
            f"series: {series_check.stderr}",
        )

    def test_usb_restore_first_packet_patch_is_opt_in_and_scoped(self) -> None:
        text = USB_RESTORE_FIRST_PACKET_PATCH.read_text(encoding="utf-8")
        changed = [
            line.removeprefix("diff --git a/").split(" b/", 1)[0]
            for line in text.splitlines()
            if line.startswith("diff --git a/")
        ]
        self.assertEqual(changed, ["hw/vmapple/bdif.c", "hw/vmapple/trace-events"])
        self.assertIn("+    bool usb_restore_first_packet_used;", text)
        self.assertIn("+    char *usb_restore_first_packet;", text)
        self.assertIn("+#define VBLK_USB_RESTORE_MAX_PACKET (16 * MiB)", text)
        self.assertIn("+static int bdif_hex_value(char ch)", text)
        self.assertIn("+static int bdif_decode_hex_packet", text)
        self.assertIn("+static bool bdif_usb_restore_deliver_first_packet", text)
        self.assertIn("+    if (!s->usb_restore_first_packet || s->usb_restore_first_packet_used) {", text)
        self.assertIn("+    s->usb_restore_first_packet_used = true;", text)
        self.assertIn("+    dma_result = dma_memory_write(&address_space_memory, req->sector.addr,", text)
        self.assertIn('+    trace_bdif_usb_restore_packet("inject-first"', text)
        self.assertIn('+    DEFINE_PROP_STRING("usb-restore-first-packet"', text)
        self.assertIn("+bdif_usb_restore_packet(const char *action", text)
        self.assertNotIn("blk_pwrite", text)
        self.assertNotIn("qemu_get_chardev", text)

    def test_usb_restore_first_packet_patch_matches_patch_series_or_is_already_applied(self) -> None:
        qemu_bdif = (QEMU / "hw" / "vmapple" / "bdif.c").read_text(
            encoding="utf-8"
        )
        qemu_trace_events = (QEMU / "hw" / "vmapple" / "trace-events").read_text(
            encoding="utf-8"
        )
        already_applied_under_later_patches = (
            "usb_restore_first_packet" in qemu_bdif
            and "bdif_decode_hex_packet" in qemu_bdif
            and "bdif_usb_restore_deliver_first_packet" in qemu_bdif
            and 'DEFINE_PROP_STRING("usb-restore-first-packet"' in qemu_bdif
            and "trace_bdif_usb_restore_packet" in qemu_bdif
            and "bdif_usb_restore_packet(const char *action" in qemu_trace_events
        )
        reverse_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--reverse",
                "--check",
                str(USB_RESTORE_FIRST_PACKET_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        current_forward_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--check",
                str(USB_RESTORE_FIRST_PACKET_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        series_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--check",
                str(PATCH),
                str(AES_PATCH),
                str(BDIF_TRACE_PATCH),
                str(RESTORE_RND_PATCH),
                str(USB_BDIF_PATCH),
                str(SVC_A0_PSCI_PATCH),
                str(IBOOT_LOW_SCRATCH_PATCH),
                str(BDIF_ACCESS_TRACE_PATCH),
                str(USB_RESTORE_CFG_PATCH),
                str(BDIF_VBLK_FAILURE_TRACE_PATCH),
                str(USB_RESTORE_PENDING_PATCH),
                str(USB_RESTORE_FIRST_PACKET_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertTrue(
            reverse_check.returncode == 0
            or current_forward_check.returncode == 0
            or series_check.returncode == 0
            or already_applied_under_later_patches,
            "reverse: "
            f"{reverse_check.stderr}\ncurrent forward: {current_forward_check.stderr}\n"
            f"series: {series_check.stderr}",
        )

    def test_usb_restore_queue_selector_patch_only_blocks_input_queue(self) -> None:
        text = USB_RESTORE_QUEUE_SELECTOR_PATCH.read_text(encoding="utf-8")
        changed = [
            line.removeprefix("diff --git a/").split(" b/", 1)[0]
            for line in text.splitlines()
            if line.startswith("diff --git a/")
        ]
        self.assertEqual(changed, ["hw/vmapple/bdif.c"])
        self.assertIn("+    uint32_t usb_restore_selected_queue;", text)
        self.assertIn("+#define REG_QUEUE_NOTIFY    0x404", text)
        self.assertIn("+#define REG_QUEUE_SELECT    0x410", text)
        self.assertIn('+        return "queue-notify";', text)
        self.assertIn('+        return "queue-select";', text)
        self.assertIn("+            s->usb_restore_selected_queue == 0) {", text)
        self.assertIn("+            ret = 0;", text)
        self.assertIn("+        } else {", text)
        self.assertIn("ret = present ? REG_BUSY_READY : 0;", text)
        self.assertIn("+    case REG_QUEUE_SELECT:", text)
        self.assertIn("+        s->usb_restore_selected_queue = devid == DEVID_USB ? value : 0;", text)
        self.assertNotIn("blk_pwrite", text)
        self.assertNotIn("REG_BUSY_READY |", text)

    def test_usb_restore_queue_selector_patch_matches_patch_series_or_is_already_applied(self) -> None:
        qemu_bdif = (QEMU / "hw" / "vmapple" / "bdif.c").read_text(
            encoding="utf-8"
        )
        already_applied_under_later_patches = (
            "usb_restore_selected_queue" in qemu_bdif
            and "REG_QUEUE_SELECT" in qemu_bdif
            and "queue-select" in qemu_bdif
            and "REG_QUEUE_NOTIFY" in qemu_bdif
            and "queue-notify" in qemu_bdif
            and "s->usb_restore_selected_queue == 0" in qemu_bdif
        )
        reverse_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--reverse",
                "--check",
                str(USB_RESTORE_QUEUE_SELECTOR_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        current_forward_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--check",
                str(USB_RESTORE_QUEUE_SELECTOR_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        series_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--check",
                str(PATCH),
                str(AES_PATCH),
                str(BDIF_TRACE_PATCH),
                str(RESTORE_RND_PATCH),
                str(USB_BDIF_PATCH),
                str(SVC_A0_PSCI_PATCH),
                str(IBOOT_LOW_SCRATCH_PATCH),
                str(BDIF_ACCESS_TRACE_PATCH),
                str(USB_RESTORE_CFG_PATCH),
                str(BDIF_VBLK_FAILURE_TRACE_PATCH),
                str(USB_RESTORE_PENDING_PATCH),
                str(USB_RESTORE_FIRST_PACKET_PATCH),
                str(USB_RESTORE_QUEUE_SELECTOR_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertTrue(
            reverse_check.returncode == 0
            or current_forward_check.returncode == 0
            or series_check.returncode == 0
            or already_applied_under_later_patches,
            "reverse: "
            f"{reverse_check.stderr}\ncurrent forward: {current_forward_check.stderr}\n"
            f"series: {series_check.stderr}",
        )

    def test_usb_restore_out_packet_patch_consumes_guest_out_packets(self) -> None:
        text = USB_RESTORE_OUT_PACKET_PATCH.read_text(encoding="utf-8")
        changed = [
            line.removeprefix("diff --git a/").split(" b/", 1)[0]
            for line in text.splitlines()
            if line.startswith("diff --git a/")
        ]
        self.assertEqual(changed, ["hw/vmapple/bdif.c"])
        self.assertIn("+#define VBLK_USB_RESTORE_OUT_FLAGS 0x00000001", text)
        self.assertIn("+static bool bdif_is_usb_restore_out_packet", text)
        self.assertIn("+           req->sector.flags == VBLK_USB_RESTORE_OUT_FLAGS &&", text)
        self.assertIn("+static void bdif_usb_restore_handle_out_packet", text)
        self.assertIn('+        trace_bdif_vblk_error("usb", "usb-restore-out-capacity"', text)
        self.assertIn("+    dma_result = dma_memory_read(&address_space_memory, req->sector.addr,", text)
        self.assertIn('+        trace_bdif_vblk_error("usb", "usb-restore-out-dma"', text)
        self.assertIn('+    trace_bdif_usb_restore_packet("guest-out"', text)
        self.assertIn("+    if (bdif_is_usb_restore_out_packet(devid, &req)) {", text)
        self.assertIn("+        bdif_usb_restore_handle_out_packet(&req, gp_addr, guest_pc);", text)
        self.assertNotIn("s->usb_restore_pending = false", text)
        self.assertNotIn("blk_pwrite", text)

    def test_usb_restore_out_packet_patch_matches_patch_series_or_is_already_applied(self) -> None:
        qemu_bdif = (QEMU / "hw" / "vmapple" / "bdif.c").read_text(
            encoding="utf-8"
        )
        already_applied_under_later_patches = (
            "VBLK_USB_RESTORE_OUT_FLAGS" in qemu_bdif
            and "bdif_is_usb_restore_out_packet" in qemu_bdif
            and "bdif_usb_restore_handle_out_packet" in qemu_bdif
            and '"usb-restore-out-capacity"' in qemu_bdif
            and '"usb-restore-out-dma"' in qemu_bdif
            and '"guest-out"' in qemu_bdif
        )
        reverse_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--reverse",
                "--check",
                str(USB_RESTORE_OUT_PACKET_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        current_forward_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--check",
                str(USB_RESTORE_OUT_PACKET_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        series_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--check",
                str(PATCH),
                str(AES_PATCH),
                str(BDIF_TRACE_PATCH),
                str(RESTORE_RND_PATCH),
                str(USB_BDIF_PATCH),
                str(SVC_A0_PSCI_PATCH),
                str(IBOOT_LOW_SCRATCH_PATCH),
                str(BDIF_ACCESS_TRACE_PATCH),
                str(USB_RESTORE_CFG_PATCH),
                str(BDIF_VBLK_FAILURE_TRACE_PATCH),
                str(USB_RESTORE_PENDING_PATCH),
                str(USB_RESTORE_FIRST_PACKET_PATCH),
                str(USB_RESTORE_QUEUE_SELECTOR_PATCH),
                str(USB_RESTORE_OUT_PACKET_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertTrue(
            reverse_check.returncode == 0
            or current_forward_check.returncode == 0
            or series_check.returncode == 0
            or already_applied_under_later_patches,
            "reverse: "
            f"{reverse_check.stderr}\ncurrent forward: {current_forward_check.stderr}\n"
            f"series: {series_check.stderr}",
        )

    def test_usb_restore_chardev_patch_exposes_bidirectional_transport(self) -> None:
        text = USB_RESTORE_CHARDEV_PATCH.read_text(encoding="utf-8")
        changed = [
            line.removeprefix("diff --git a/").split(" b/", 1)[0]
            for line in text.splitlines()
            if line.startswith("diff --git a/")
        ]
        self.assertEqual(changed, ["hw/vmapple/bdif.c"])
        self.assertIn('+#include "chardev/char-fe.h"', text)
        self.assertIn("+    GByteArray *usb_restore_rx;", text)
        self.assertIn("+    CharFrontend usb_restore_chr;", text)
        self.assertIn("+#define VBLK_USB_RESTORE_HEADER_LEN 6", text)
        self.assertIn("+static bool bdif_usb_restore_try_deliver_rx", text)
        self.assertIn("+    payload_len = ldl_le_p(s->usb_restore_rx->data);", text)
        self.assertIn('+        trace_bdif_vblk_error("usb", "usb-restore-chardev-len"', text)
        self.assertIn('+        trace_bdif_vblk_error("usb", "usb-restore-chardev-capacity"', text)
        self.assertIn('+        trace_bdif_vblk_error("usb", "usb-restore-chardev-dma"', text)
        self.assertIn('+    trace_bdif_usb_restore_packet("chardev-in"', text)
        self.assertIn("+static void bdif_usb_restore_chr_read", text)
        self.assertIn("+    g_byte_array_append(s->usb_restore_rx, buf, size);", text)
        self.assertIn("+        qemu_chr_fe_accept_input(&s->usb_restore_chr);", text)
        self.assertIn('+    DEFINE_PROP_CHR("usb-restore-chardev", VMAppleBdifState, usb_restore_chr),', text)
        self.assertIn("+        qemu_chr_fe_set_handlers(&s->usb_restore_chr,", text)
        self.assertIn("+            bdif_usb_restore_try_deliver_rx(s, guest_pc)) {", text)
        self.assertIn("+        bdif_usb_restore_handle_out_packet(s, &req, gp_addr, guest_pc);", text)
        self.assertIn("+        int written = qemu_chr_fe_write(&s->usb_restore_chr, packet,", text)
        self.assertIn('+            trace_bdif_usb_restore_packet("chardev-out"', text)
        self.assertIn('+            trace_bdif_vblk_error("usb", "usb-restore-chardev-write"', text)
        self.assertNotIn("blk_pwrite", text)

    def test_usb_restore_chardev_patch_matches_patch_series_or_is_already_applied(self) -> None:
        qemu_bdif = (QEMU / "hw" / "vmapple" / "bdif.c").read_text(
            encoding="utf-8"
        )
        already_applied_under_later_patches = (
            "CharFrontend usb_restore_chr;" in qemu_bdif
            and "GByteArray *usb_restore_rx;" in qemu_bdif
            and "bdif_usb_restore_try_deliver_rx" in qemu_bdif
            and 'DEFINE_PROP_CHR("usb-restore-chardev"' in qemu_bdif
            and "qemu_chr_fe_write(&s->usb_restore_chr" in qemu_bdif
            and '"chardev-in"' in qemu_bdif
            and '"chardev-out"' in qemu_bdif
        )
        reverse_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--reverse",
                "--check",
                str(USB_RESTORE_CHARDEV_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        current_forward_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--check",
                str(USB_RESTORE_CHARDEV_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        series_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--check",
                str(PATCH),
                str(AES_PATCH),
                str(BDIF_TRACE_PATCH),
                str(RESTORE_RND_PATCH),
                str(USB_BDIF_PATCH),
                str(SVC_A0_PSCI_PATCH),
                str(IBOOT_LOW_SCRATCH_PATCH),
                str(BDIF_ACCESS_TRACE_PATCH),
                str(USB_RESTORE_CFG_PATCH),
                str(BDIF_VBLK_FAILURE_TRACE_PATCH),
                str(USB_RESTORE_PENDING_PATCH),
                str(USB_RESTORE_FIRST_PACKET_PATCH),
                str(USB_RESTORE_QUEUE_SELECTOR_PATCH),
                str(USB_RESTORE_OUT_PACKET_PATCH),
                str(USB_RESTORE_CHARDEV_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertTrue(
            reverse_check.returncode == 0
            or current_forward_check.returncode == 0
            or series_check.returncode == 0
            or already_applied_under_later_patches,
            "reverse: "
            f"{reverse_check.stderr}\ncurrent forward: {current_forward_check.stderr}\n"
            f"series: {series_check.stderr}",
        )

    def test_usb_restore_chardev_prime_patch_traces_buffered_host_input(self) -> None:
        text = USB_RESTORE_CHARDEV_PRIME_PATCH.read_text(encoding="utf-8")
        changed = [
            line.removeprefix("diff --git a/").split(" b/", 1)[0]
            for line in text.splitlines()
            if line.startswith("diff --git a/")
        ]
        self.assertEqual(changed, ["hw/vmapple/bdif.c"])
        self.assertIn("+    uint64_t header = 0;", text)
        self.assertIn("+    memcpy(&header, buf, MIN((size_t)size, sizeof(header)));", text)
        self.assertIn('+    trace_bdif_usb_restore_packet("chardev-buffered", 0,', text)
        self.assertIn("+                                  (uint32_t)size, header, guest_pc);", text)
        self.assertIn("+        qemu_chr_fe_accept_input(&s->usb_restore_chr);", text)
        self.assertNotIn("blk_pwrite", text)

    def test_usb_restore_chardev_prime_patch_matches_patch_series_or_is_already_applied(self) -> None:
        qemu_bdif = (QEMU / "hw" / "vmapple" / "bdif.c").read_text(
            encoding="utf-8"
        )
        already_applied_under_later_patches = (
            '"chardev-buffered"' in qemu_bdif
            and "memcpy(&header, buf, MIN((size_t)size, sizeof(header)));" in qemu_bdif
            and "(uint32_t)size, header, guest_pc" in qemu_bdif
            and "qemu_chr_fe_accept_input(&s->usb_restore_chr);" in qemu_bdif
        )
        reverse_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--reverse",
                "--check",
                str(USB_RESTORE_CHARDEV_PRIME_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        current_forward_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--check",
                str(USB_RESTORE_CHARDEV_PRIME_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        series_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--check",
                str(PATCH),
                str(AES_PATCH),
                str(BDIF_TRACE_PATCH),
                str(RESTORE_RND_PATCH),
                str(USB_BDIF_PATCH),
                str(SVC_A0_PSCI_PATCH),
                str(IBOOT_LOW_SCRATCH_PATCH),
                str(BDIF_ACCESS_TRACE_PATCH),
                str(USB_RESTORE_CFG_PATCH),
                str(BDIF_VBLK_FAILURE_TRACE_PATCH),
                str(USB_RESTORE_PENDING_PATCH),
                str(USB_RESTORE_FIRST_PACKET_PATCH),
                str(USB_RESTORE_QUEUE_SELECTOR_PATCH),
                str(USB_RESTORE_OUT_PACKET_PATCH),
                str(USB_RESTORE_CHARDEV_PATCH),
                str(USB_RESTORE_CHARDEV_PRIME_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertTrue(
            reverse_check.returncode == 0
            or current_forward_check.returncode == 0
            or series_check.returncode == 0
            or already_applied_under_later_patches,
            "reverse: "
            f"{reverse_check.stderr}\ncurrent forward: {current_forward_check.stderr}\n"
            f"series: {series_check.stderr}",
        )

    def test_bdif_block_write_patch_implements_real_block_writes(self) -> None:
        text = BDIF_BLOCK_WRITE_PATCH.read_text(encoding="utf-8")
        changed = [
            line.removeprefix("diff --git a/").split(" b/", 1)[0]
            for line in text.splitlines()
            if line.startswith("diff --git a/")
        ]
        self.assertEqual(changed, ["hw/vmapple/bdif.c", "hw/vmapple/trace-events"])
        self.assertIn("+    bool block_writes;", text)
        self.assertIn('+    DEFINE_PROP_BOOL("block-writes", VMAppleBdifState, block_writes, false),', text)
        self.assertIn("+static bool bdif_set_block_write_perm(BlockBackend *blk, const char *name,", text)
        self.assertIn("+    r = blk_set_perm(blk, BLK_PERM_CONSISTENT_READ | BLK_PERM_WRITE,", text)
        self.assertIn('+        error_prepend(errp, "vmapple-bdif %s backing: ", name);', text)
        self.assertIn("+        if (!s->block_writes) {", text)
        self.assertIn('+            trace_bdif_vblk_error(bdif_devid_name(devid), "write-disabled"', text)
        self.assertIn("+        dma_result = dma_memory_read(&address_space_memory, req.data.addr, buf,", text)
        self.assertIn('+            trace_bdif_vblk_error(bdif_devid_name(devid), "write-data-dma"', text)
        self.assertIn("+        header = req.data.len >= sizeof(header) ? ldq_le_p(buf) : 0;", text)
        self.assertIn("+        r = blk_pwrite(blk, off, req.data.len, buf, 0);", text)
        self.assertIn("+        trace_bdif_vblk_write(bdif_devid_name(devid),", text)
        self.assertIn('+            trace_bdif_vblk_error(bdif_devid_name(devid), "write-failed"', text)
        self.assertIn("+        ret = VBLK_RET_SUCCESS;", text)
        self.assertIn("+bdif_vblk_write(const char *dev", text)
        self.assertNotIn("+        /* Not needed, iBoot only reads */", text)
        self.assertNotIn("+        trace_bdif_vblk_error(bdif_devid_name(devid), \"write-unsupported\"", text)
        self.assertNotIn("ninja install", text)
        self.assertNotIn("/usr", text)

    def test_bdif_block_write_trace_event_respects_qemu_arg_limit(self) -> None:
        text = BDIF_BLOCK_WRITE_PATCH.read_text(encoding="utf-8")
        for line in text.splitlines():
            if not line.startswith("+bdif_vblk_write"):
                continue
            args = line.split("(", 1)[1].split(")", 1)[0].strip()
            argc = 0 if args in {"", "void"} else args.count(",") + 1
            self.assertLessEqual(argc, 10, line)

    def test_bdif_block_write_patch_matches_patch_series_or_is_already_applied(self) -> None:
        qemu_bdif = (QEMU / "hw" / "vmapple" / "bdif.c").read_text(
            encoding="utf-8"
        )
        qemu_trace_events = (QEMU / "hw" / "vmapple" / "trace-events").read_text(
            encoding="utf-8"
        )
        already_applied_under_later_patches = (
            "blk_pwrite(blk, off, req.data.len, buf, 0)" in qemu_bdif
            and 'DEFINE_PROP_BOOL("block-writes", VMAppleBdifState, block_writes, false),' in qemu_bdif
            and "bdif_set_block_write_perm" in qemu_bdif
            and "BLK_PERM_CONSISTENT_READ | BLK_PERM_WRITE" in qemu_bdif
            and '"write-disabled"' in qemu_bdif
            and '"write-data-dma"' in qemu_bdif
            and '"write-failed"' in qemu_bdif
            and "trace_bdif_vblk_write" in qemu_bdif
            and "bdif_vblk_write(const char *dev" in qemu_trace_events
        )
        reverse_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--reverse",
                "--check",
                str(BDIF_BLOCK_WRITE_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        current_forward_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--check",
                str(BDIF_BLOCK_WRITE_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        series_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--check",
                str(PATCH),
                str(AES_PATCH),
                str(BDIF_TRACE_PATCH),
                str(RESTORE_RND_PATCH),
                str(USB_BDIF_PATCH),
                str(SVC_A0_PSCI_PATCH),
                str(IBOOT_LOW_SCRATCH_PATCH),
                str(BDIF_ACCESS_TRACE_PATCH),
                str(USB_RESTORE_CFG_PATCH),
                str(BDIF_VBLK_FAILURE_TRACE_PATCH),
                str(USB_RESTORE_PENDING_PATCH),
                str(USB_RESTORE_FIRST_PACKET_PATCH),
                str(USB_RESTORE_QUEUE_SELECTOR_PATCH),
                str(USB_RESTORE_OUT_PACKET_PATCH),
                str(USB_RESTORE_CHARDEV_PATCH),
                str(USB_RESTORE_CHARDEV_PRIME_PATCH),
                str(BDIF_BLOCK_WRITE_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertTrue(
            reverse_check.returncode == 0
            or current_forward_check.returncode == 0
            or series_check.returncode == 0
            or already_applied_under_later_patches,
            "reverse: "
            f"{reverse_check.stderr}\ncurrent forward: {current_forward_check.stderr}\n"
            f"series: {series_check.stderr}",
        )

    def test_boot_prep_mmio_patch_is_tcg_only_and_maps_exact_fault_window(self) -> None:
        text = BOOT_PREP_MMIO_PATCH.read_text(encoding="utf-8")
        changed = [
            line.removeprefix("diff --git a/").split(" b/", 1)[0]
            for line in text.splitlines()
            if line.startswith("diff --git a/")
        ]
        self.assertEqual(changed, ["hw/vmapple/vmapple.c"])
        self.assertIn("+    VMAPPLE_BOOT_PREP_MMIO,", text)
        self.assertIn(
            "+    [VMAPPLE_BOOT_PREP_MMIO] =     { 0x30240000, 0x00010000 },",
            text,
        )
        self.assertIn("+static void create_boot_prep_mmio(VMAppleMachineState *vms)", text)
        self.assertIn("+#ifndef CONFIG_MAC_PVG_MMIO", text)
        self.assertIn(
            "+     * 0x30240040 after accepting the LocalPolicy-bound RestoreKernelCache.",
            text,
        )
        self.assertIn(
            '+    create_unimplemented_device("vmapple-boot-prep-mmio",',
            text,
        )
        self.assertIn("+    create_boot_prep_mmio(vms);", text)
        self.assertNotIn("ninja install", text)
        self.assertNotIn("/usr", text)

    def test_boot_prep_mmio_patch_matches_patch_series_or_is_already_applied(self) -> None:
        qemu_vmapple = (QEMU / "hw" / "vmapple" / "vmapple.c").read_text(
            encoding="utf-8"
        )
        already_applied_under_later_patches = (
            "VMAPPLE_BOOT_PREP_MMIO" in qemu_vmapple
            and "{ 0x30240000, 0x00010000 }" in qemu_vmapple
            and "0x30240040" in qemu_vmapple
            and 'create_unimplemented_device("vmapple-boot-prep-mmio"' in qemu_vmapple
            and "create_boot_prep_mmio(vms);" in qemu_vmapple
        )
        reverse_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--reverse",
                "--check",
                str(BOOT_PREP_MMIO_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        current_forward_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--check",
                str(BOOT_PREP_MMIO_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        series_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--check",
                str(PATCH),
                str(AES_PATCH),
                str(BDIF_TRACE_PATCH),
                str(RESTORE_RND_PATCH),
                str(USB_BDIF_PATCH),
                str(SVC_A0_PSCI_PATCH),
                str(IBOOT_LOW_SCRATCH_PATCH),
                str(BDIF_ACCESS_TRACE_PATCH),
                str(USB_RESTORE_CFG_PATCH),
                str(BDIF_VBLK_FAILURE_TRACE_PATCH),
                str(USB_RESTORE_PENDING_PATCH),
                str(USB_RESTORE_FIRST_PACKET_PATCH),
                str(USB_RESTORE_QUEUE_SELECTOR_PATCH),
                str(USB_RESTORE_OUT_PACKET_PATCH),
                str(USB_RESTORE_CHARDEV_PATCH),
                str(USB_RESTORE_CHARDEV_PRIME_PATCH),
                str(BDIF_BLOCK_WRITE_PATCH),
                str(BOOT_PREP_MMIO_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertTrue(
            reverse_check.returncode == 0
            or current_forward_check.returncode == 0
            or series_check.returncode == 0
            or already_applied_under_later_patches,
            "reverse: "
            f"{reverse_check.stderr}\ncurrent forward: {current_forward_check.stderr}\n"
            f"series: {series_check.stderr}",
        )

    def test_ctrr_mmio_patch_is_tcg_only_and_maps_exact_fault_window(self) -> None:
        text = CTRR_MMIO_PATCH.read_text(encoding="utf-8")
        changed = [
            line.removeprefix("diff --git a/").split(" b/", 1)[0]
            for line in text.splitlines()
            if line.startswith("diff --git a/")
        ]
        self.assertEqual(changed, ["hw/vmapple/vmapple.c"])
        self.assertIn("+    VMAPPLE_CTRR_MMIO,", text)
        self.assertIn(
            "+    [VMAPPLE_CTRR_MMIO] =          { 0x30260000, 0x00010000 },",
            text,
        )
        self.assertIn("+static void create_ctrr_mmio(VMAppleMachineState *vms)", text)
        self.assertIn("+#ifndef CONFIG_MAC_PVG_MMIO", text)
        self.assertIn(
            '+     * 0x30260000 and comparing it with the 0x63747272 "ctrr" FourCC.',
            text,
        )
        self.assertIn(
            '+    create_unimplemented_device("vmapple-ctrr-mmio",',
            text,
        )
        self.assertIn("+    create_ctrr_mmio(vms);", text)
        self.assertNotIn("ninja install", text)
        self.assertNotIn("/usr", text)

    def test_ctrr_mmio_patch_matches_patch_series_or_is_already_applied(self) -> None:
        qemu_vmapple = (QEMU / "hw" / "vmapple" / "vmapple.c").read_text(
            encoding="utf-8"
        )
        already_applied_under_later_patches = (
            "VMAPPLE_CTRR_MMIO" in qemu_vmapple
            and "{ 0x30260000, 0x00010000 }" in qemu_vmapple
            and "0x63747272" in qemu_vmapple
            and 'create_unimplemented_device("vmapple-ctrr-mmio"' in qemu_vmapple
            and "create_ctrr_mmio(vms);" in qemu_vmapple
        )
        reverse_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--reverse",
                "--check",
                str(CTRR_MMIO_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        current_forward_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--check",
                str(CTRR_MMIO_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        series_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--check",
                str(PATCH),
                str(AES_PATCH),
                str(BDIF_TRACE_PATCH),
                str(RESTORE_RND_PATCH),
                str(USB_BDIF_PATCH),
                str(SVC_A0_PSCI_PATCH),
                str(IBOOT_LOW_SCRATCH_PATCH),
                str(BDIF_ACCESS_TRACE_PATCH),
                str(USB_RESTORE_CFG_PATCH),
                str(BDIF_VBLK_FAILURE_TRACE_PATCH),
                str(USB_RESTORE_PENDING_PATCH),
                str(USB_RESTORE_FIRST_PACKET_PATCH),
                str(USB_RESTORE_QUEUE_SELECTOR_PATCH),
                str(USB_RESTORE_OUT_PACKET_PATCH),
                str(USB_RESTORE_CHARDEV_PATCH),
                str(USB_RESTORE_CHARDEV_PRIME_PATCH),
                str(BDIF_BLOCK_WRITE_PATCH),
                str(BOOT_PREP_MMIO_PATCH),
                str(CTRR_MMIO_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertTrue(
            reverse_check.returncode == 0
            or current_forward_check.returncode == 0
            or series_check.returncode == 0
            or already_applied_under_later_patches,
            "reverse: "
            f"{reverse_check.stderr}\ncurrent forward: {current_forward_check.stderr}\n"
            f"series: {series_check.stderr}",
        )

    def test_bdif_queue_notify_patch_models_status_as_stateful_mmio(self) -> None:
        text = BDIF_QUEUE_NOTIFY_PATCH.read_text(encoding="utf-8")
        changed = [
            line.removeprefix("diff --git a/").split(" b/", 1)[0]
            for line in text.splitlines()
            if line.startswith("diff --git a/")
        ]
        self.assertEqual(changed, ["hw/vmapple/bdif.c"])
        self.assertIn("0x30100404", text)
        self.assertIn("REG_QUEUE_NOTIFY", text)
        self.assertIn("+    uint32_t root_queue_notify;", text)
        self.assertIn("+    uint32_t aux_queue_notify;", text)
        self.assertIn("+    uint32_t usb_queue_notify;", text)
        self.assertIn(
            "+static uint32_t *bdif_queue_notify_for_devid(VMAppleBdifState *s,",
            text,
        )
        self.assertIn("+        return &s->usb_queue_notify;", text)
        self.assertIn("+            ret = present && queue_notify ? *queue_notify : 0;", text)
        self.assertIn("+                *queue_notify = (uint32_t)value;", text)
        self.assertNotIn("ninja install", text)
        self.assertNotIn("/usr", text)

    def test_bdif_queue_notify_patch_matches_patch_series_or_is_already_applied(self) -> None:
        qemu_bdif = (QEMU / "hw" / "vmapple" / "bdif.c").read_text(
            encoding="utf-8"
        )
        already_applied_under_later_patches = (
            "uint32_t usb_queue_notify;" in qemu_bdif
            and "bdif_queue_notify_for_devid" in qemu_bdif
            and "return &s->usb_queue_notify;" in qemu_bdif
            and "ret = present && queue_notify ? *queue_notify : 0;" in qemu_bdif
            and "*queue_notify = (uint32_t)value;" in qemu_bdif
        )
        reverse_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--reverse",
                "--check",
                str(BDIF_QUEUE_NOTIFY_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        current_forward_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--check",
                str(BDIF_QUEUE_NOTIFY_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        series_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--check",
                str(PATCH),
                str(AES_PATCH),
                str(BDIF_TRACE_PATCH),
                str(RESTORE_RND_PATCH),
                str(USB_BDIF_PATCH),
                str(SVC_A0_PSCI_PATCH),
                str(IBOOT_LOW_SCRATCH_PATCH),
                str(BDIF_ACCESS_TRACE_PATCH),
                str(USB_RESTORE_CFG_PATCH),
                str(BDIF_VBLK_FAILURE_TRACE_PATCH),
                str(USB_RESTORE_PENDING_PATCH),
                str(USB_RESTORE_FIRST_PACKET_PATCH),
                str(USB_RESTORE_QUEUE_SELECTOR_PATCH),
                str(USB_RESTORE_OUT_PACKET_PATCH),
                str(USB_RESTORE_CHARDEV_PATCH),
                str(USB_RESTORE_CHARDEV_PRIME_PATCH),
                str(BDIF_BLOCK_WRITE_PATCH),
                str(BOOT_PREP_MMIO_PATCH),
                str(CTRR_MMIO_PATCH),
                str(BDIF_QUEUE_NOTIFY_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertTrue(
            reverse_check.returncode == 0
            or current_forward_check.returncode == 0
            or series_check.returncode == 0
            or already_applied_under_later_patches,
            "reverse: "
            f"{reverse_check.stderr}\ncurrent forward: {current_forward_check.stderr}\n"
            f"series: {series_check.stderr}",
        )

    def test_xnu_early_hvc_patch_handles_bootstrap_call_only_in_restore_mode(self) -> None:
        text = XNU_EARLY_HVC_PATCH.read_text(encoding="utf-8")
        changed = [
            line.removeprefix("diff --git a/").split(" b/", 1)[0]
            for line in text.splitlines()
            if line.startswith("diff --git a/")
        ]
        self.assertEqual(changed, ["target/arm/tcg/psci.c"])
        self.assertIn("0xc1000000", text)
        self.assertIn("QEMU_APPLE_XNU_BOOT_HVC 0xc1000000ULL", text)
        self.assertIn("arm_is_vmapple_svc_a0_hvc_call", text)
        self.assertIn("case EXCP_HVC:", text)
        self.assertIn("cpu->psci_conduit == QEMU_PSCI_CONDUIT_SVC_A0", text)
        self.assertIn("arm_is_implemented_psci_function(env->xregs[0])", text)
        self.assertIn("arm_is_vmapple_xnu_boot_hvc_function(env->xregs[0])", text)
        self.assertIn("syn_get_ec(env->exception.syndrome) == EC_AA64_HVC", text)
        self.assertIn("FIELD_EX32(env->exception.syndrome, ISS_IMM16, IMM16) == 0", text)
        self.assertIn("ret = QEMU_PSCI_RET_SUCCESS;", text)
        self.assertNotIn("ninja install", text)
        self.assertNotIn("/usr", text)

    def test_xnu_early_hvc_patch_matches_patch_series_or_is_already_applied(self) -> None:
        qemu_psci = (QEMU / "target" / "arm" / "tcg" / "psci.c").read_text(
            encoding="utf-8"
        )
        already_applied_under_later_patches = (
            (
                "QEMU_APPLE_XNU_BOOT_HVC 0xc1000000ULL" in qemu_psci
                and "arm_is_vmapple_svc_a0_hvc_call" in qemu_psci
                and "arm_is_vmapple_xnu_boot_hvc_function(param[0])" in qemu_psci
                and "ret = QEMU_PSCI_RET_SUCCESS;" in qemu_psci
            )
            or (
                "QEMU_APPLE_PAC_SET_INITIAL_STATE 0xc1000000ULL" in qemu_psci
                and (
                    "arm_is_vmapple_pac_hvc_function(param[0])" in qemu_psci
                    or "arm_is_vmapple_hvc_function(param[0])" in qemu_psci
                )
                and (
                    "arm_handle_vmapple_pac_hvc_call(env, param[0])" in qemu_psci
                    or "arm_handle_vmapple_hvc_call(env, param[0])" in qemu_psci
                )
            )
        )
        reverse_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--reverse",
                "--check",
                str(XNU_EARLY_HVC_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        current_forward_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--check",
                str(XNU_EARLY_HVC_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        series_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--check",
                str(PATCH),
                str(AES_PATCH),
                str(BDIF_TRACE_PATCH),
                str(RESTORE_RND_PATCH),
                str(USB_BDIF_PATCH),
                str(SVC_A0_PSCI_PATCH),
                str(IBOOT_LOW_SCRATCH_PATCH),
                str(BDIF_ACCESS_TRACE_PATCH),
                str(USB_RESTORE_CFG_PATCH),
                str(BDIF_VBLK_FAILURE_TRACE_PATCH),
                str(USB_RESTORE_PENDING_PATCH),
                str(USB_RESTORE_FIRST_PACKET_PATCH),
                str(USB_RESTORE_QUEUE_SELECTOR_PATCH),
                str(USB_RESTORE_OUT_PACKET_PATCH),
                str(USB_RESTORE_CHARDEV_PATCH),
                str(USB_RESTORE_CHARDEV_PRIME_PATCH),
                str(BDIF_BLOCK_WRITE_PATCH),
                str(BOOT_PREP_MMIO_PATCH),
                str(CTRR_MMIO_PATCH),
                str(BDIF_QUEUE_NOTIFY_PATCH),
                str(XNU_EARLY_HVC_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertTrue(
            reverse_check.returncode == 0
            or current_forward_check.returncode == 0
            or series_check.returncode == 0
            or already_applied_under_later_patches,
            "reverse: "
            f"{reverse_check.stderr}\ncurrent forward: {current_forward_check.stderr}\n"
            f"series: {series_check.stderr}",
        )

    def test_xnu_pac_hvc_patch_models_documented_vmapple_pac_hvc_family(self) -> None:
        text = XNU_PAC_HVC_PATCH.read_text(encoding="utf-8")
        changed = [
            line.removeprefix("diff --git a/").split(" b/", 1)[0]
            for line in text.splitlines()
            if line.startswith("diff --git a/")
        ]
        self.assertEqual(changed, ["target/arm/tcg/psci.c"])

        for symbol, value in (
            ("QEMU_APPLE_PAC_SET_INITIAL_STATE", "0xc1000000ULL"),
            ("QEMU_APPLE_PAC_GET_DEFAULT_KEYS", "0xc1000001ULL"),
            ("QEMU_APPLE_PAC_SET_A_KEYS", "0xc1000002ULL"),
            ("QEMU_APPLE_PAC_SET_B_KEYS", "0xc1000003ULL"),
            ("QEMU_APPLE_PAC_SET_EL0_DIVERSIFIER", "0xc1000004ULL"),
            ("QEMU_APPLE_PAC_SET_EL0_DIVERSIFIER_AT_EL1", "0xc1000005ULL"),
            ("QEMU_APPLE_PAC_SET_G_KEY", "0xc1000006ULL"),
        ):
            with self.subTest(symbol=symbol):
                self.assertIn(f"{symbol} {value}", text)

        self.assertIn("arm_is_vmapple_pac_hvc_function", text)
        self.assertIn("function_id >= QEMU_APPLE_PAC_SET_INITIAL_STATE", text)
        self.assertIn("function_id <= QEMU_APPLE_PAC_SET_G_KEY", text)
        self.assertIn("arm_handle_vmapple_pac_hvc_call", text)
        self.assertIn("env->xregs[1] = QEMU_APPLE_PAC_DEFAULT_A_KEY;", text)
        self.assertIn("env->xregs[2] = QEMU_APPLE_PAC_DEFAULT_B_KEY;", text)
        self.assertIn("env->xregs[3] = QEMU_APPLE_PAC_DEFAULT_EL0_DIVERSIFIER;", text)
        self.assertIn("env->xregs[4] = QEMU_APPLE_PAC_DEFAULT_G_KEY;", text)
        self.assertIn("env->keys.apia", text)
        self.assertIn("env->keys.apda", text)
        self.assertIn("env->keys.apib", text)
        self.assertIn("env->keys.apdb", text)
        self.assertIn("env->keys.apga", text)
        self.assertIn("syn_get_ec(env->exception.syndrome) == EC_AA64_HVC", text)
        self.assertIn("FIELD_EX32(env->exception.syndrome, ISS_IMM16, IMM16) == 0", text)
        self.assertIn("Unknown HVC calls remain", text)
        self.assertIn("return false;", text)
        self.assertNotIn("ninja install", text)
        self.assertNotIn("/usr", text)

    def test_xnu_pac_hvc_patch_matches_patch_series_or_is_already_applied(self) -> None:
        qemu_psci = (QEMU / "target" / "arm" / "tcg" / "psci.c").read_text(
            encoding="utf-8"
        )
        already_applied_under_later_patches = (
            "QEMU_APPLE_PAC_GET_DEFAULT_KEYS 0xc1000001ULL" in qemu_psci
            and (
                "arm_handle_vmapple_pac_hvc_call(env, param[0])" in qemu_psci
                or "arm_handle_vmapple_pac_hvc_call(env, function_id)" in qemu_psci
            )
            and "env->xregs[4] = QEMU_APPLE_PAC_DEFAULT_G_KEY;" in qemu_psci
            and "env->keys.apga" in qemu_psci
        )
        reverse_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--reverse",
                "--check",
                str(XNU_PAC_HVC_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        current_forward_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--check",
                str(XNU_PAC_HVC_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        series_check = subprocess.run(
            (
                "git",
                "-C",
                str(QEMU),
                "apply",
                "--check",
                str(PATCH),
                str(AES_PATCH),
                str(BDIF_TRACE_PATCH),
                str(RESTORE_RND_PATCH),
                str(USB_BDIF_PATCH),
                str(SVC_A0_PSCI_PATCH),
                str(IBOOT_LOW_SCRATCH_PATCH),
                str(BDIF_ACCESS_TRACE_PATCH),
                str(USB_RESTORE_CFG_PATCH),
                str(BDIF_VBLK_FAILURE_TRACE_PATCH),
                str(USB_RESTORE_PENDING_PATCH),
                str(USB_RESTORE_FIRST_PACKET_PATCH),
                str(USB_RESTORE_QUEUE_SELECTOR_PATCH),
                str(USB_RESTORE_OUT_PACKET_PATCH),
                str(USB_RESTORE_CHARDEV_PATCH),
                str(USB_RESTORE_CHARDEV_PRIME_PATCH),
                str(BDIF_BLOCK_WRITE_PATCH),
                str(BOOT_PREP_MMIO_PATCH),
                str(CTRR_MMIO_PATCH),
                str(BDIF_QUEUE_NOTIFY_PATCH),
                str(XNU_EARLY_HVC_PATCH),
                str(XNU_PAC_HVC_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertTrue(
            reverse_check.returncode == 0
            or current_forward_check.returncode == 0
            or series_check.returncode == 0
            or already_applied_under_later_patches,
            "reverse: "
            f"{reverse_check.stderr}\ncurrent forward: {current_forward_check.stderr}\n"
            f"series: {series_check.stderr}",
        )

    def test_vmapple_el0_pac_patch_models_key_domains_without_bypass(self) -> None:
        text = VMAPPLE_EL0_PAC_PATCH.read_text(encoding="utf-8")
        changed = [
            line.removeprefix("diff --git a/").split(" b/", 1)[0]
            for line in text.splitlines()
            if line.startswith("diff --git a/")
        ]
        self.assertEqual(
            changed,
            [
                "target/arm/cpu.h",
                "target/arm/tcg/pauth_helper.c",
                "target/arm/tcg/psci.c",
                "target/arm/trace-events",
            ],
        )

        for marker in (
            "bool active;",
            "bool use_el0_keys_at_el1;",
            "uint64_t el0_diversifier;",
            "uint64_t el1_user_diversifier;",
            "ARMPACKey el0_apda;",
            "ARMPACKey el1_user_apda;",
            "QEMU_APPLE_PAC_DEFAULT_EL0_DIVERSIFIER 0x564d4150504c454aULL",
            "pauth_vmapple_key",
            "el == 0",
            "el == 1 && env->vmapple_pac.use_el0_keys_at_el1",
            "arm_vmapple_pac_effective_seed",
            "arm_vmapple_pac_program_el0_diversifier",
            "arm_vmapple_pac_program_el1_user_diversifier",
            "env->xregs[1] > 1",
            "QEMU_PSCI_RET_INVALID_PARAMS",
            "env->vmapple_pac.use_el0_keys_at_el1 = true;",
            "env->vmapple_pac.use_el0_keys_at_el1 = false;",
            "env->vmapple_pac.active = true;",
            "trace_vmapple_pauth_failure",
            "vmapple_pauth_failure(uint64_t ptr",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

        # Signing and authentication must use the same selected key for all
        # four architectural A/B instruction and data key classes.
        self.assertGreaterEqual(text.count("pauth_vmapple_key"), 9)
        self.assertIn("return pauth_addpac(env, x, y, key, false);", text)
        self.assertIn("return pauth_addpac(env, x, y, key, true);", text)
        self.assertIn("return pauth_auth(env, x, y, key, false, 0", text)
        self.assertIn("return pauth_auth(env, x, y, key, true, 0", text)
        self.assertIn("return pauth_auth(env, x, y, key, false, 1", text)
        self.assertIn("return pauth_auth(env, x, y, key, true, 1", text)
        self.assertIn(
            "arm_vmapple_pac_program_b_keys(env, env->xregs[1]);", text
        )
        self.assertIn(
            "arm_vmapple_pac_program_el1_user_diversifier(\n"
            "+                env, env->xregs[2]);",
            text,
        )
        self.assertNotIn(
            "arm_vmapple_pac_program_el0_diversifier(env, env->xregs[2]);",
            text,
        )
        self.assertNotIn(
            "+#define QEMU_APPLE_PAC_DEFAULT_EL0_DIVERSIFIER "
            "0x0000000000000000ULL",
            text,
        )
        self.assertIn("does not bypass PAC instructions", text)
        self.assertNotIn("pauth_key_enabled(env, el, SCTLR_EnDA)) {\n+        return 0;", text)
        self.assertNotIn("ninja install", text)

    def test_vmapple_el0_pac_patch_applies_or_is_already_applied(self) -> None:
        checks = []
        for reverse in (False, True):
            args = ["git", "-C", str(QEMU), "apply"]
            if reverse:
                args.append("--reverse")
            args.extend(("--check", str(VMAPPLE_EL0_PAC_PATCH)))
            checks.append(
                subprocess.run(
                    args,
                    check=False,
                    capture_output=True,
                    text=True,
                )
            )
        self.assertTrue(
            any(item.returncode == 0 for item in checks),
            "forward: " + checks[0].stderr + "\nreverse: " + checks[1].stderr,
        )

    def test_xnu_hvc_discovery_patch_models_pac_nop_and_bounded_oem_probe(self) -> None:
        text = XNU_HVC_DISCOVERY_PATCH.read_text(encoding="utf-8")
        changed = [
            line.removeprefix("diff --git a/").split(" b/", 1)[0]
            for line in text.splitlines()
            if line.startswith("diff --git a/")
        ]
        self.assertEqual(changed, ["target/arm/tcg/psci.c"])

        for symbol, value in (
            ("QEMU_APPLE_PAC_NOP", "0xc10000f0ULL"),
            ("QEMU_APPLE_OEM_UID", "0x8300ff01ULL"),
            ("QEMU_APPLE_OEM_REVISION", "0x8300ff03ULL"),
            ("QEMU_APPLE_OEM_FEATURES", "0x8300feffULL"),
        ):
            with self.subTest(symbol=symbol):
                self.assertIn(f"{symbol} {value}", text)

        self.assertIn("arm_is_vmapple_hvc_function", text)
        self.assertIn("arm_handle_vmapple_hvc_call", text)
        self.assertIn("0x9cbb6ebbULL", text)
        self.assertIn("0x9dc9d679ULL", text)
        self.assertIn("0xaa624e1fULL", text)
        self.assertIn("0x3b878185ULL", text)
        self.assertIn("QEMU_APPLE_OEM_FEATURE_UNSUPPORTED", text)
        self.assertIn("Do not advertise WFK/KICK", text)
        self.assertIn("Unknown HVC calls remain", text)
        self.assertNotIn("QEMU_APPLE_OEM_VCPU_WFK", text)
        self.assertNotIn("QEMU_APPLE_OEM_VCPU_KICK", text)
        self.assertNotIn("ninja install", text)
        self.assertNotIn("/usr", text)

    def test_xnu_hvc_discovery_patch_matches_patch_series_or_is_already_applied(self) -> None:
        qemu_psci = (QEMU / "target" / "arm" / "tcg" / "psci.c").read_text(
            encoding="utf-8"
        )
        already_applied = (
            "QEMU_APPLE_PAC_NOP 0xc10000f0ULL" in qemu_psci
            and "QEMU_APPLE_OEM_UID 0x8300ff01ULL" in qemu_psci
            and "arm_handle_vmapple_hvc_call(env, param[0])" in qemu_psci
            and "QEMU_APPLE_OEM_FEATURE_UNSUPPORTED" in qemu_psci
        )
        current_forward_check = subprocess.run(
            ("git", "-C", str(QEMU), "apply", "--check", str(XNU_HVC_DISCOVERY_PATCH)),
            check=False,
            capture_output=True,
            text=True,
        )
        reverse_check = subprocess.run(
            (
                "git", "-C", str(QEMU), "apply", "--reverse", "--check",
                str(XNU_HVC_DISCOVERY_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        series_check = subprocess.run(
            (
                "git", "-C", str(QEMU), "apply", "--check",
                str(XNU_EARLY_HVC_PATCH), str(XNU_PAC_HVC_PATCH),
                str(XNU_HVC_DISCOVERY_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertTrue(
            current_forward_check.returncode == 0
            or reverse_check.returncode == 0
            or series_check.returncode == 0
            or already_applied,
            "forward: "
            f"{current_forward_check.stderr}\nreverse: {reverse_check.stderr}\n"
            f"series: {series_check.stderr}",
        )

    def test_psci_pc_trace_patch_is_diagnostic_only_and_scoped(self) -> None:
        text = PSCI_PC_TRACE_PATCH.read_text(encoding="utf-8")
        changed = [
            line.removeprefix("diff --git a/").split(" b/", 1)[0]
            for line in text.splitlines()
            if line.startswith("diff --git a/")
        ]
        self.assertEqual(
            changed,
            ["target/arm/tcg/psci.c", "target/arm/trace-events"],
        )
        self.assertIn("arm_cpu_mp_affinity(cpu), env->pc", text)
        self.assertIn("uint32_t cpuid, uint64_t pc", text)
        self.assertIn('cpuid=0x%x pc=0x%016', text)
        self.assertNotIn("env->pc =", text)
        self.assertNotIn("+        env->xregs[", text)
        self.assertNotIn("ninja install", text)
        self.assertNotIn("/usr", text)

    def test_psci_pc_trace_patch_matches_patch_series_or_is_already_applied(self) -> None:
        qemu_psci = (QEMU / "target" / "arm" / "tcg" / "psci.c").read_text(
            encoding="utf-8"
        )
        qemu_trace = (QEMU / "target" / "arm" / "trace-events").read_text(
            encoding="utf-8"
        )
        already_applied = (
            "arm_cpu_mp_affinity(cpu), env->pc" in qemu_psci
            and "uint32_t cpuid, uint64_t pc" in qemu_trace
        )
        current_forward_check = subprocess.run(
            ("git", "-C", str(QEMU), "apply", "--check", str(PSCI_PC_TRACE_PATCH)),
            check=False,
            capture_output=True,
            text=True,
        )
        reverse_check = subprocess.run(
            (
                "git", "-C", str(QEMU), "apply", "--reverse", "--check",
                str(PSCI_PC_TRACE_PATCH),
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertTrue(
            current_forward_check.returncode == 0
            or reverse_check.returncode == 0
            or already_applied,
            "forward: "
            f"{current_forward_check.stderr}\nreverse: {reverse_check.stderr}",
        )

    def test_patch_apply_script_handles_later_context_drift_with_markers(self) -> None:
        text = (ROOT / "scripts" / "apply-qemu-patches.sh").read_text(encoding="utf-8")

        self.assertIn("patch_is_semantically_applied", text)
        self.assertIn("0001-vmapple-enable-linux-tcg-machine-init.patch", text)
        self.assertIn("depends on TCG || HVF", text)
        self.assertIn('create_unimplemented_device("vmapple-pvg"', text)
        self.assertIn(".interfaces    = aarch64_machine_interfaces,", text)
        self.assertIn("0003-vmapple-bdif-trace-read-context.patch", text)
        self.assertIn("bdif_vblk_read(const char *dev, uint64_t addr", text)
        self.assertIn("0005-vmapple-bdif-add-optional-usb-backend.patch", text)
        self.assertIn("DriveInfo *di_usb = drive_get(IF_PFLASH, 0, 2);", text)
        self.assertIn("0006-vmapple-route-iboot-svc-a0-psci.patch", text)
        self.assertIn("arm_is_iboot_svc_a0_psci_call", text)
        self.assertIn("QEMU_PSCI_CONDUIT_SVC_A0 = 3,", text)
        self.assertIn("0007-vmapple-map-iboot-low-scratch.patch", text)
        self.assertIn("vmapple.iboot-low-scratch", text)
        self.assertIn("0008-vmapple-trace-bdif-device-registers.patch", text)
        self.assertIn("bdif_access(const char *op, const char *dev, const char *reg", text)
        self.assertIn("0009-vmapple-report-usb-restore-bdif-cfg.patch", text)
        self.assertIn("REG_CFG_USB_RESTORE", text)
        self.assertIn("0010-vmapple-trace-bdif-vblk-command-failures.patch", text)
        self.assertIn("trace_bdif_vblk_cmd", text)
        self.assertIn("0011-vmapple-keep-usb-restore-bdif-transfers-pending.patch", text)
        self.assertIn("usb-restore-pending", text)
        self.assertIn("0012-vmapple-add-debug-usb-restore-first-packet.patch", text)
        self.assertIn("bdif_usb_restore_deliver_first_packet", text)
        self.assertIn("bdif_usb_restore_packet(const char *action", text)
        self.assertIn("0013-vmapple-track-usb-restore-queue-selector.patch", text)
        self.assertIn("usb_restore_selected_queue", text)
        self.assertIn("queue-select", text)
        self.assertIn("0014-vmapple-handle-usb-restore-out-packets.patch", text)
        self.assertIn("bdif_usb_restore_handle_out_packet", text)
        self.assertIn('"guest-out"', text)
        self.assertIn("0015-vmapple-add-usb-restore-chardev.patch", text)
        self.assertIn("bdif_usb_restore_try_deliver_rx", text)
        self.assertIn('DEFINE_PROP_CHR("usb-restore-chardev"', text)
        self.assertIn("qemu_chr_fe_write(&s->usb_restore_chr", text)
        self.assertIn('"chardev-in"', text)
        self.assertIn('"chardev-out"', text)
        self.assertIn("0016-vmapple-prime-usb-restore-chardev-input.patch", text)
        self.assertIn('"chardev-buffered"', text)
        self.assertIn("memcpy(&header, buf, MIN((size_t)size, sizeof(header)));", text)
        self.assertIn("0017-vmapple-implement-bdif-block-writes.patch", text)
        self.assertIn("blk_pwrite(blk, off, req.data.len, buf, 0)", text)
        self.assertIn('DEFINE_PROP_BOOL("block-writes", VMAppleBdifState, block_writes, false)', text)
        self.assertIn("bdif_vblk_write(const char *dev", text)
        self.assertIn("0018-vmapple-map-boot-prep-mmio.patch", text)
        self.assertIn("VMAPPLE_BOOT_PREP_MMIO", text)
        self.assertIn("0x30240040", text)
        self.assertIn('create_unimplemented_device("vmapple-boot-prep-mmio"', text)
        self.assertIn("0019-vmapple-map-ctrr-mmio.patch", text)
        self.assertIn("VMAPPLE_CTRR_MMIO", text)
        self.assertIn("0x63747272", text)
        self.assertIn('create_unimplemented_device("vmapple-ctrr-mmio"', text)
        self.assertIn("0020-vmapple-model-bdif-queue-notify-status.patch", text)
        self.assertIn("uint32_t usb_queue_notify;", text)
        self.assertIn("bdif_queue_notify_for_devid", text)
        self.assertIn("ret = present && queue_notify ? *queue_notify : 0;", text)
        self.assertIn("*queue_notify = (uint32_t)value;", text)
        self.assertIn("0021-vmapple-handle-xnu-early-hvc-bootstrap.patch", text)
        self.assertIn("QEMU_APPLE_XNU_BOOT_HVC 0xc1000000ULL", text)
        self.assertIn("arm_is_vmapple_svc_a0_hvc_call", text)
        self.assertIn("arm_is_vmapple_xnu_boot_hvc_function(param[0])", text)
        self.assertIn("ret = QEMU_PSCI_RET_SUCCESS;", text)
        self.assertIn("0022-vmapple-handle-xnu-pac-hvc-family.patch", text)
        self.assertIn("QEMU_APPLE_PAC_GET_DEFAULT_KEYS 0xc1000001ULL", text)
        self.assertIn("arm_handle_vmapple_pac_hvc_call(env, param[0])", text)
        self.assertIn("env->xregs[4] = QEMU_APPLE_PAC_DEFAULT_G_KEY;", text)
        self.assertIn("env->keys.apga", text)
        self.assertIn("0023-vmapple-handle-pac-nop-oem-discovery.patch", text)
        self.assertIn("QEMU_APPLE_PAC_NOP 0xc10000f0ULL", text)
        self.assertIn("QEMU_APPLE_OEM_UID 0x8300ff01ULL", text)
        self.assertIn("QEMU_APPLE_OEM_FEATURE_UNSUPPORTED", text)
        self.assertIn("0024-arm-trace-psci-guest-pc.patch", text)
        self.assertIn("arm_cpu_mp_affinity(cpu), env->pc", text)
        self.assertIn("uint32_t cpuid, uint64_t pc", text)
        self.assertIn(
            "0025-vmapple-model-apple-error-status-sysregs.patch", text
        )
        self.assertIn("vmapple_tcg_error_status_regs", text)
        self.assertIn("VMAPPLE_MMU_ERR_STS", text)
        self.assertIn("VMAPPLE_LLC_ERR_INF", text)
        self.assertIn("VMAPPLE_FED_ERR_STS", text)
        self.assertIn(
            "0026-arm-cpreg-allow-opt-in-impldef-el1-access.patch", text
        )
        self.assertIn("ARM_CP_IMPLDEF_EL1           = 1 << 24", text)
        self.assertIn("ARM_CP_CONST | ARM_CP_IMPLDEF_EL1", text)
        self.assertIn(
            "0028-vmapple-connect-linux-reims-vgpu-mmio.patch", text
        )
        self.assertIn("macvm-reims-vgpu-mmio-source", text)
        self.assertIn('qdev_new("reims-vgpu-mmio")', text)
        self.assertIn("0029-display-keep-macvm-kconfig-minimal.patch", text)
        self.assertIn("Linux host implementation of the VMApple PVG", text)
        self.assertIn("0030-vmapple-include-target-device-config.patch", text)
        self.assertIn("#include CONFIG_DEVICES", text)
        self.assertIn("0031-vmapple-model-el0-pac-key-domains.patch", text)
        self.assertIn("bool use_el0_keys_at_el1;", text)
        self.assertIn("uint64_t el0_diversifier;", text)
        self.assertIn("uint64_t el1_user_diversifier;", text)
        self.assertIn(
            "QEMU_APPLE_PAC_DEFAULT_EL0_DIVERSIFIER 0x564d4150504c454aULL",
            text,
        )
        self.assertIn("pauth_vmapple_key", text)
        self.assertIn("trace_vmapple_pauth_failure", text)
        self.assertIn("arm_vmapple_pac_program_el0_diversifier", text)
        self.assertIn("arm_vmapple_pac_program_el1_user_diversifier", text)
        self.assertIn("vmapple_pauth_failure(uint64_t ptr", text)
        self.assertIn(
            "0032-reims-mmio-generator-track-transform-script.patch", text
        )
        self.assertIn(
            "input: [reims_vgpu_mmio_source, reims_vgpu_prepare]", text
        )
        self.assertIn("semantic marker check", text)

    def test_reims_generator_patch_tracks_code_and_transform(self) -> None:
        text = REIMS_GENERATOR_DEP_PATCH.read_text(encoding="utf-8")
        changed = [
            line.removeprefix("diff --git a/").split(" b/", 1)[0]
            for line in text.splitlines()
            if line.startswith("diff --git a/")
        ]
        self.assertEqual(changed, ["hw/display/meson.build"])
        self.assertIn(
            "+    input: [reims_vgpu_mmio_source, reims_vgpu_prepare]", text
        )
        self.assertIn(
            "+    command: [python, '@INPUT1@', '@INPUT0@', '@OUTPUT@'])", text
        )
        self.assertNotIn("build_always_stale", text)


if __name__ == "__main__":
    unittest.main()
