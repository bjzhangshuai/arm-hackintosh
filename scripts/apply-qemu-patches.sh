#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
QEMU_ROOT="$REPO_ROOT/third_party/qemu"
PATCH_DIR="$REPO_ROOT/patches/qemu"

if [[ ! -e "$QEMU_ROOT/.git" ]]; then
  echo "macvm: QEMU submodule is missing; run git submodule update --init first." >&2
  exit 69
fi

patch_is_semantically_applied() {
  local patch_name

  patch_name="$(basename "$1")"
  case "$patch_name" in
    0001-vmapple-enable-linux-tcg-machine-init.patch)
      grep -Fq "CONFIG_VMAPPLE=y" "$QEMU_ROOT/configs/devices/aarch64-softmmu/default.mak" &&
        grep -Fq "depends on TCG || HVF" "$QEMU_ROOT/hw/vmapple/Kconfig" &&
        grep -Fq "select MAC_PVG_MMIO if HVF" "$QEMU_ROOT/hw/vmapple/Kconfig" &&
        grep -Fq "select UNIMP if !MAC_PVG_MMIO" "$QEMU_ROOT/hw/vmapple/Kconfig" &&
        grep -Fq '#include "hw/arm/machines-qom.h"' "$QEMU_ROOT/hw/vmapple/vmapple.c" &&
        grep -Fq '#include "hw/misc/unimp.h"' "$QEMU_ROOT/hw/vmapple/vmapple.c" &&
        grep -Fq 'create_unimplemented_device("vmapple-pvg"' "$QEMU_ROOT/hw/vmapple/vmapple.c" &&
        grep -Fq 'create_unimplemented_device("vmapple-iosfc"' "$QEMU_ROOT/hw/vmapple/vmapple.c" &&
        grep -Fq 'mc->default_cpu_type = ARM_CPU_TYPE_NAME("max");' "$QEMU_ROOT/hw/vmapple/vmapple.c" &&
        grep -Fq ".interfaces    = aarch64_machine_interfaces," "$QEMU_ROOT/hw/vmapple/vmapple.c"
      ;;
    0003-vmapple-bdif-trace-read-context.patch)
      grep -Fq '#include "hw/core/cpu.h"' "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "current_cpu ? current_cpu->cc->get_pc(current_cpu) : 0" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "ldq_le_p(buf)" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "bdif_vblk_read(const char *dev, uint64_t addr, uint64_t offset, uint32_t len, int r, uint64_t pc, uint64_t header)" "$QEMU_ROOT/hw/vmapple/trace-events"
      ;;
    0005-vmapple-bdif-add-optional-usb-backend.patch)
      grep -Fq "BlockBackend *usb;" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "case DEVID_USB:" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq 'DEFINE_PROP_DRIVE("usb", VMAppleBdifState, usb),' "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "DriveInfo *di_usb = drive_get(IF_PFLASH, 0, 2);" "$QEMU_ROOT/hw/vmapple/vmapple.c" &&
        grep -Fq 'qdev_prop_set_drive(DEVICE(bdif), "usb"' "$QEMU_ROOT/hw/vmapple/vmapple.c"
      ;;
    0006-vmapple-route-iboot-svc-a0-psci.patch)
      grep -Fq "bool svc_a0_psci;" "$QEMU_ROOT/hw/vmapple/vmapple.c" &&
        grep -Fq "object_property_add_bool(obj, \"svc-a0-psci\"" "$QEMU_ROOT/hw/vmapple/vmapple.c" &&
        grep -Fq "QEMU_PSCI_CONDUIT_SVC_A0 = 3," "$QEMU_ROOT/target/arm/cpu.h" &&
        grep -Fq "arm_is_iboot_svc_a0_psci_call" "$QEMU_ROOT/target/arm/tcg/psci.c"
      ;;
    0007-vmapple-map-iboot-low-scratch.patch)
      grep -Fq "bool iboot_low_scratch;" "$QEMU_ROOT/hw/vmapple/vmapple.c" &&
        grep -Fq "VMAPPLE_IBOOT_LOW_SCRATCH" "$QEMU_ROOT/hw/vmapple/vmapple.c" &&
        grep -Fq "vmapple.iboot-low-scratch" "$QEMU_ROOT/hw/vmapple/vmapple.c" &&
        grep -Fq "object_property_add_bool(obj, \"iboot-low-scratch\"" "$QEMU_ROOT/hw/vmapple/vmapple.c"
      ;;
    0008-vmapple-trace-bdif-device-registers.patch)
      grep -Fq "bdif_devid_name" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "bdif_reg_name" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq 'bdif_trace_access("read", devid, offset, size, ret);' "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq 'bdif_trace_access("write", devid, offset, size, value);' "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "bdif_access(const char *op, const char *dev, const char *reg" "$QEMU_ROOT/hw/vmapple/trace-events"
      ;;
    0009-vmapple-report-usb-restore-bdif-cfg.patch)
      grep -Fq "REG_CFG_USB_RESTORE" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "bdif_cfg_for_devid" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "return REG_CFG_USB_RESTORE;" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "ret = bdif_cfg_for_devid(s, devid);" "$QEMU_ROOT/hw/vmapple/bdif.c"
      ;;
    0010-vmapple-trace-bdif-vblk-command-failures.patch)
      grep -Fq "trace_bdif_vblk_cmd" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "trace_bdif_vblk_desc" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "trace_bdif_vblk_error" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "trace_bdif_vblk_sector" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "bdif_vblk_cmd(const char *dev" "$QEMU_ROOT/hw/vmapple/trace-events" &&
        grep -Fq "bdif_vblk_desc(const char *dev" "$QEMU_ROOT/hw/vmapple/trace-events" &&
        grep -Fq "bdif_vblk_error(const char *dev" "$QEMU_ROOT/hw/vmapple/trace-events"
      ;;
    0011-vmapple-keep-usb-restore-bdif-transfers-pending.patch)
      grep -Fq "bool usb_restore_pending;" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "bdif_is_usb_restore_transfer" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "VBLK_USB_RESTORE_FLAGS" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "s->usb_restore_pending = true;" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "usb-restore-pending" "$QEMU_ROOT/hw/vmapple/bdif.c"
      ;;
    0012-vmapple-add-debug-usb-restore-first-packet.patch)
      grep -Fq "usb_restore_first_packet" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "bdif_decode_hex_packet" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "bdif_usb_restore_deliver_first_packet" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq 'DEFINE_PROP_STRING("usb-restore-first-packet"' "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "trace_bdif_usb_restore_packet" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "bdif_usb_restore_packet(const char *action" "$QEMU_ROOT/hw/vmapple/trace-events"
      ;;
    0013-vmapple-track-usb-restore-queue-selector.patch)
      grep -Fq "usb_restore_selected_queue" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "REG_QUEUE_SELECT" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "queue-select" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "REG_QUEUE_NOTIFY" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "queue-notify" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "s->usb_restore_selected_queue == 0" "$QEMU_ROOT/hw/vmapple/bdif.c"
      ;;
    0014-vmapple-handle-usb-restore-out-packets.patch)
      grep -Fq "VBLK_USB_RESTORE_OUT_FLAGS" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "bdif_is_usb_restore_out_packet" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "bdif_usb_restore_handle_out_packet" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq '"usb-restore-out-capacity"' "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq '"usb-restore-out-dma"' "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq '"guest-out"' "$QEMU_ROOT/hw/vmapple/bdif.c"
      ;;
    0015-vmapple-add-usb-restore-chardev.patch)
      grep -Fq "CharFrontend usb_restore_chr;" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "GByteArray *usb_restore_rx;" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "VBLK_USB_RESTORE_HEADER_LEN" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "bdif_usb_restore_try_deliver_rx" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "bdif_usb_restore_chr_read" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq 'DEFINE_PROP_CHR("usb-restore-chardev"' "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "qemu_chr_fe_write(&s->usb_restore_chr" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq '"chardev-in"' "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq '"chardev-out"' "$QEMU_ROOT/hw/vmapple/bdif.c"
      ;;
    0016-vmapple-prime-usb-restore-chardev-input.patch)
      grep -Fq '"chardev-buffered"' "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "memcpy(&header, buf, MIN((size_t)size, sizeof(header)));" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "(uint32_t)size, header, guest_pc" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "qemu_chr_fe_accept_input(&s->usb_restore_chr);" "$QEMU_ROOT/hw/vmapple/bdif.c"
      ;;
    0017-vmapple-implement-bdif-block-writes.patch)
      grep -Fq "blk_pwrite(blk, off, req.data.len, buf, 0)" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq 'DEFINE_PROP_BOOL("block-writes", VMAppleBdifState, block_writes, false),' "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "bdif_set_block_write_perm" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "BLK_PERM_CONSISTENT_READ | BLK_PERM_WRITE" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq '"write-disabled"' "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq '"write-data-dma"' "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq '"write-failed"' "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "trace_bdif_vblk_write" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "bdif_vblk_write(const char *dev" "$QEMU_ROOT/hw/vmapple/trace-events"
      ;;
    0018-vmapple-map-boot-prep-mmio.patch)
      grep -Fq "VMAPPLE_BOOT_PREP_MMIO" "$QEMU_ROOT/hw/vmapple/vmapple.c" &&
        grep -Fq "{ 0x30240000, 0x00010000 }" "$QEMU_ROOT/hw/vmapple/vmapple.c" &&
        grep -Fq "0x30240040" "$QEMU_ROOT/hw/vmapple/vmapple.c" &&
        grep -Fq 'create_unimplemented_device("vmapple-boot-prep-mmio"' "$QEMU_ROOT/hw/vmapple/vmapple.c" &&
        grep -Fq "create_boot_prep_mmio(vms);" "$QEMU_ROOT/hw/vmapple/vmapple.c"
      ;;
    0019-vmapple-map-ctrr-mmio.patch)
      grep -Fq "VMAPPLE_CTRR_MMIO" "$QEMU_ROOT/hw/vmapple/vmapple.c" &&
        grep -Fq "{ 0x30260000, 0x00010000 }" "$QEMU_ROOT/hw/vmapple/vmapple.c" &&
        grep -Fq "0x63747272" "$QEMU_ROOT/hw/vmapple/vmapple.c" &&
        grep -Fq 'create_unimplemented_device("vmapple-ctrr-mmio"' "$QEMU_ROOT/hw/vmapple/vmapple.c" &&
        grep -Fq "create_ctrr_mmio(vms);" "$QEMU_ROOT/hw/vmapple/vmapple.c"
      ;;
    0020-vmapple-model-bdif-queue-notify-status.patch)
      grep -Fq "uint32_t usb_queue_notify;" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "bdif_queue_notify_for_devid" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "return &s->usb_queue_notify;" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "ret = present && queue_notify ? *queue_notify : 0;" "$QEMU_ROOT/hw/vmapple/bdif.c" &&
        grep -Fq "*queue_notify = (uint32_t)value;" "$QEMU_ROOT/hw/vmapple/bdif.c"
      ;;
    0021-vmapple-handle-xnu-early-hvc-bootstrap.patch)
      (
        grep -Fq "QEMU_APPLE_XNU_BOOT_HVC 0xc1000000ULL" "$QEMU_ROOT/target/arm/tcg/psci.c" &&
          grep -Fq "arm_is_vmapple_svc_a0_hvc_call" "$QEMU_ROOT/target/arm/tcg/psci.c" &&
          grep -Fq "arm_is_vmapple_xnu_boot_hvc_function(param[0])" "$QEMU_ROOT/target/arm/tcg/psci.c" &&
          grep -Fq "ret = QEMU_PSCI_RET_SUCCESS;" "$QEMU_ROOT/target/arm/tcg/psci.c"
      ) || (
        grep -Fq "QEMU_APPLE_PAC_SET_INITIAL_STATE 0xc1000000ULL" "$QEMU_ROOT/target/arm/tcg/psci.c" &&
          (
            grep -Fq "arm_is_vmapple_pac_hvc_function(param[0])" "$QEMU_ROOT/target/arm/tcg/psci.c" ||
              grep -Fq "arm_is_vmapple_hvc_function(param[0])" "$QEMU_ROOT/target/arm/tcg/psci.c"
          ) &&
          (
            grep -Fq "arm_handle_vmapple_pac_hvc_call(env, param[0])" "$QEMU_ROOT/target/arm/tcg/psci.c" ||
              grep -Fq "arm_handle_vmapple_hvc_call(env, param[0])" "$QEMU_ROOT/target/arm/tcg/psci.c"
          )
      )
      ;;
    0022-vmapple-handle-xnu-pac-hvc-family.patch)
      grep -Fq "QEMU_APPLE_PAC_GET_DEFAULT_KEYS 0xc1000001ULL" "$QEMU_ROOT/target/arm/tcg/psci.c" &&
        grep -Fq "env->xregs[4] = QEMU_APPLE_PAC_DEFAULT_G_KEY;" "$QEMU_ROOT/target/arm/tcg/psci.c" &&
        grep -Fq "env->keys.apga" "$QEMU_ROOT/target/arm/tcg/psci.c" &&
        (
          grep -Fq "arm_handle_vmapple_pac_hvc_call(env, param[0])" "$QEMU_ROOT/target/arm/tcg/psci.c" ||
            grep -Fq "arm_handle_vmapple_pac_hvc_call(env, function_id)" "$QEMU_ROOT/target/arm/tcg/psci.c"
        )
      ;;
    0023-vmapple-handle-pac-nop-oem-discovery.patch)
      grep -Fq "QEMU_APPLE_PAC_NOP 0xc10000f0ULL" "$QEMU_ROOT/target/arm/tcg/psci.c" &&
        grep -Fq "QEMU_APPLE_OEM_UID 0x8300ff01ULL" "$QEMU_ROOT/target/arm/tcg/psci.c" &&
        grep -Fq "arm_handle_vmapple_hvc_call(env, param[0])" "$QEMU_ROOT/target/arm/tcg/psci.c" &&
        grep -Fq "QEMU_APPLE_OEM_FEATURE_UNSUPPORTED" "$QEMU_ROOT/target/arm/tcg/psci.c"
      ;;
    0024-arm-trace-psci-guest-pc.patch)
      grep -Fq "arm_cpu_mp_affinity(cpu), env->pc" "$QEMU_ROOT/target/arm/tcg/psci.c" &&
        grep -Fq "uint32_t cpuid, uint64_t pc" "$QEMU_ROOT/target/arm/trace-events" &&
        grep -Fq 'cpuid=0x%x pc=0x%016' "$QEMU_ROOT/target/arm/trace-events"
      ;;
    0025-vmapple-model-apple-error-status-sysregs.patch)
      grep -Fq '#include "target/arm/cpregs.h"' "$QEMU_ROOT/hw/vmapple/vmapple.c" &&
        grep -Fq "vmapple_tcg_error_status_regs" "$QEMU_ROOT/hw/vmapple/vmapple.c" &&
        grep -Fq 'VMAPPLE_MMU_ERR_STS' "$QEMU_ROOT/hw/vmapple/vmapple.c" &&
        grep -Fq 'VMAPPLE_LLC_ERR_STS' "$QEMU_ROOT/hw/vmapple/vmapple.c" &&
        grep -Fq 'VMAPPLE_LLC_ERR_ADR' "$QEMU_ROOT/hw/vmapple/vmapple.c" &&
        grep -Fq 'VMAPPLE_LLC_ERR_INF' "$QEMU_ROOT/hw/vmapple/vmapple.c" &&
        grep -Fq 'VMAPPLE_LSU_ERR_STS' "$QEMU_ROOT/hw/vmapple/vmapple.c" &&
        grep -Fq 'VMAPPLE_FED_ERR_STS' "$QEMU_ROOT/hw/vmapple/vmapple.c" &&
        grep -Fq 'if (tcg_enabled())' "$QEMU_ROOT/hw/vmapple/vmapple.c" &&
        grep -Fq 'vmapple_register_tcg_error_status_regs(ARM_CPU(cpu));' "$QEMU_ROOT/hw/vmapple/vmapple.c"
      ;;
    0026-arm-cpreg-allow-opt-in-impldef-el1-access.patch)
      grep -Fq 'ARM_CP_IMPLDEF_EL1           = 1 << 24' "$QEMU_ROOT/target/arm/cpregs.h" &&
        grep -Fq '!(r->type & ARM_CP_IMPLDEF_EL1)' "$QEMU_ROOT/target/arm/helper.c" &&
        test "$(grep -Fc 'ARM_CP_CONST | ARM_CP_IMPLDEF_EL1' "$QEMU_ROOT/hw/vmapple/vmapple.c")" -eq 6
      ;;
    0027-vmapple-model-pcie-msi-frame.patch)
      grep -Fq 'bool msi_typer_valid;' "$QEMU_ROOT/hw/intc/arm_gicv2m.c" &&
        grep -Fq 'DEFINE_PROP_BOOL("msi-typer-valid"' "$QEMU_ROOT/hw/intc/arm_gicv2m.c" &&
        grep -Fq 'val |= 1U << 31;' "$QEMU_ROOT/hw/intc/arm_gicv2m.c" &&
        grep -Fq '[VMAPPLE_GIC_MSI] =            { 0x1fff0000, 0x00010000 }' "$QEMU_ROOT/hw/vmapple/vmapple.c" &&
        grep -Fq 'qdev_new("arm-gicv2m")' "$QEMU_ROOT/hw/vmapple/vmapple.c" &&
        grep -Fq 'qdev_prop_set_bit(dev, "msi-typer-valid", true);' "$QEMU_ROOT/hw/vmapple/vmapple.c" &&
        grep -Fq 'create_msi(vms);' "$QEMU_ROOT/hw/vmapple/vmapple.c"
      ;;
    0028-vmapple-connect-linux-reims-vgpu-mmio.patch)
      grep -Fq 'config MACVM_REIMS_VGPU' "$QEMU_ROOT/hw/display/Kconfig" &&
        grep -Fq "macvm-reims-vgpu-mmio-source" "$QEMU_ROOT/hw/display/meson.build" &&
        grep -Fq -- "--features backend-vulkan" "$QEMU_ROOT/hw/display/meson.build" &&
        grep -Fq 'select MACVM_REIMS_VGPU if TCG' "$QEMU_ROOT/hw/vmapple/Kconfig" &&
        grep -Fq '#elif defined(CONFIG_MACVM_REIMS_VGPU)' "$QEMU_ROOT/hw/vmapple/vmapple.c" &&
        grep -Fq 'qdev_new("reims-vgpu-mmio")' "$QEMU_ROOT/hw/vmapple/vmapple.c" &&
        grep -Fq 'reims_vgpu_mmio_realize' "$QEMU_ROOT/hw/display/trace-events"
      ;;
    0029-display-keep-macvm-kconfig-minimal.patch)
      grep -Fq 'config MACVM_REIMS_VGPU' "$QEMU_ROOT/hw/display/Kconfig" &&
        ! grep -Fq 'Linux host implementation of the VMApple PVG' "$QEMU_ROOT/hw/display/Kconfig"
      ;;
    0030-vmapple-include-target-device-config.patch)
      grep -Fq '#include CONFIG_DEVICES' "$QEMU_ROOT/hw/vmapple/vmapple.c"
      ;;
    0031-vmapple-model-el0-pac-key-domains.patch)
      grep -Fq 'bool use_el0_keys_at_el1;' "$QEMU_ROOT/target/arm/cpu.h" &&
        grep -Fq 'uint64_t el0_diversifier;' "$QEMU_ROOT/target/arm/cpu.h" &&
        grep -Fq 'uint64_t el1_user_diversifier;' "$QEMU_ROOT/target/arm/cpu.h" &&
        grep -Fq 'QEMU_APPLE_PAC_DEFAULT_EL0_DIVERSIFIER 0x564d4150504c454aULL' "$QEMU_ROOT/target/arm/tcg/psci.c" &&
        grep -Fq 'pauth_vmapple_key' "$QEMU_ROOT/target/arm/tcg/pauth_helper.c" &&
        grep -Fq 'trace_vmapple_pauth_failure' "$QEMU_ROOT/target/arm/tcg/pauth_helper.c" &&
        grep -Fq 'arm_vmapple_pac_program_el0_diversifier' "$QEMU_ROOT/target/arm/tcg/psci.c" &&
        grep -Fq 'arm_vmapple_pac_program_el1_user_diversifier' "$QEMU_ROOT/target/arm/tcg/psci.c" &&
        grep -Fq 'env->vmapple_pac.use_el0_keys_at_el1 = true;' "$QEMU_ROOT/target/arm/tcg/psci.c" &&
        grep -Fq 'vmapple_pauth_failure(uint64_t ptr' "$QEMU_ROOT/target/arm/trace-events"
      ;;
    0032-reims-mmio-generator-track-transform-script.patch)
      grep -Fq "input: [reims_vgpu_mmio_source, reims_vgpu_prepare]" "$QEMU_ROOT/hw/display/meson.build" &&
        grep -Fq "command: [python, '@INPUT1@', '@INPUT0@', '@OUTPUT@']" "$QEMU_ROOT/hw/display/meson.build"
      ;;
    *)
      return 1
      ;;
  esac
}

while IFS= read -r patch_path; do
  apply_check_log="$(mktemp)"
  if git -C "$QEMU_ROOT" apply --reverse --check "$patch_path" >/dev/null 2>&1; then
    echo "already applied: ${patch_path#$REPO_ROOT/}"
  elif git -C "$QEMU_ROOT" apply --check "$patch_path" 2>"$apply_check_log"; then
    git -C "$QEMU_ROOT" apply "$patch_path"
    echo "applied: ${patch_path#$REPO_ROOT/}"
  elif patch_is_semantically_applied "$patch_path"; then
    echo "already applied: ${patch_path#$REPO_ROOT/} (semantic marker check)"
  else
    cat "$apply_check_log" >&2
    echo "macvm: patch cannot be applied cleanly: $patch_path" >&2
    echo "macvm: refusing to reset or overwrite the QEMU worktree." >&2
    rm -f "$apply_check_log"
    exit 65
  fi
  rm -f "$apply_check_log"
done < <(find "$PATCH_DIR" -maxdepth 1 -type f -name '*.patch' -print | LC_ALL=C sort)
