set pagination off
set confirm off
set architecture aarch64

# Attach after iBEC has entered the Stage2 recovery prompt.  This follows the
# SVC #7 trampoline into the macOS kernel, reaches the high-address MMU-enabled
# XNU entry, and executes the first two observed vmapple PAC HVC calls.  It is
# diagnostic-only: no registers or guest memory are patched.

set $kernel_pac_trampoline = 0
set $kernel_pac_entry = 0
set $kernel_pac_boot_args = 0
set $kernel_pac_ret = 0
set $kernel_pac_slide = 0
set $kernel_pac_hvc_get_default_1 = 0
set $kernel_pac_hvc_get_default_2 = 0
set $kernel_pac_after_hvc_window = 0

target remote 127.0.0.1:12345

break *0x70087c8c
commands
  silent
  set $kernel_pac_trampoline = $x24
  set $kernel_pac_entry = $x0
  set $kernel_pac_boot_args = $x1
  printf "IBEC_BOOTX_KERNEL_PAC_HVC_CALLBACK_CALL pc=0x%lx trampoline=0x%lx entry=0x%lx boot_args=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx sp=0x%lx x30=0x%lx cpsr=0x%lx\n", $pc, $kernel_pac_trampoline, $kernel_pac_entry, $kernel_pac_boot_args, $x2, $x3, $x4, $sp, $x30, $cpsr
  if $kernel_pac_trampoline >= 0x70000000 && $kernel_pac_trampoline < 0xd0000000
    set $kernel_pac_ret = $kernel_pac_trampoline + 0x2b8
    advance *$kernel_pac_ret
    si
    si
    advance *0x76f5c104
    advance *0x76f5c13c
    advance *0x76f5c1f4
    advance *0x76f5c33c
    printf "IBEC_BOOTX_KERNEL_PAC_HVC_BOOTSTRAP_BEFORE pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x30=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x30, $sp, $cpsr
    si
    printf "IBEC_BOOTX_KERNEL_PAC_HVC_BOOTSTRAP_AFTER pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x30=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x30, $sp, $cpsr
    si
    printf "IBEC_BOOTX_KERNEL_PAC_HVC_BOOTSTRAP_AFTER_CBNZ pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x30=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x30, $sp, $cpsr
    advance *0x76f5c384
    si
    set $kernel_pac_slide = $x22 - $x23
    set $kernel_pac_hvc_get_default_1 = $kernel_pac_slide + 0x778884c0
    set $kernel_pac_hvc_get_default_2 = $kernel_pac_slide + 0x77888504
    set $kernel_pac_after_hvc_window = $kernel_pac_slide + 0x77888514
    printf "IBEC_BOOTX_KERNEL_PAC_HVC_HIGH_ENTRY pc=0x%lx slide=0x%lx get_default_1=0x%lx get_default_2=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x30=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $kernel_pac_slide, $kernel_pac_hvc_get_default_1, $kernel_pac_hvc_get_default_2, $x0, $x1, $x2, $x3, $x4, $x30, $sp, $cpsr
    advance *$kernel_pac_hvc_get_default_1
    printf "IBEC_BOOTX_KERNEL_PAC_HVC_GET_DEFAULT_1_BEFORE pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x11=0x%lx x12=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x11, $x12, $sp, $cpsr
    si
    printf "IBEC_BOOTX_KERNEL_PAC_HVC_GET_DEFAULT_1_AFTER pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x11=0x%lx x12=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x11, $x12, $sp, $cpsr
    si
    printf "IBEC_BOOTX_KERNEL_PAC_HVC_GET_DEFAULT_1_AFTER_CBNZ pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x11=0x%lx x12=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x11, $x12, $sp, $cpsr
    if $pc == $kernel_pac_hvc_get_default_1 + 4
      printf "IBEC_BOOTX_KERNEL_PAC_HVC_GET_DEFAULT_1_NONZERO_RETURN_SPIN pc=0x%lx x0=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $sp, $cpsr
    end
    advance *$kernel_pac_hvc_get_default_2
    printf "IBEC_BOOTX_KERNEL_PAC_HVC_GET_DEFAULT_2_BEFORE pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x8=0x%lx x9=0x%lx x10=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x8, $x9, $x10, $sp, $cpsr
    si
    printf "IBEC_BOOTX_KERNEL_PAC_HVC_GET_DEFAULT_2_AFTER pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x8=0x%lx x9=0x%lx x10=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x8, $x9, $x10, $sp, $cpsr
    si
    printf "IBEC_BOOTX_KERNEL_PAC_HVC_GET_DEFAULT_2_AFTER_CBNZ pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x8=0x%lx x9=0x%lx x10=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x8, $x9, $x10, $sp, $cpsr
    if $pc == $kernel_pac_hvc_get_default_2 + 4
      printf "IBEC_BOOTX_KERNEL_PAC_HVC_GET_DEFAULT_2_NONZERO_RETURN_SPIN pc=0x%lx x0=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $sp, $cpsr
    end
    advance *$kernel_pac_after_hvc_window
    printf "IBEC_BOOTX_KERNEL_PAC_HVC_AFTER_WINDOW pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x30=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x30, $sp, $cpsr
  end
  detach
  quit
end

continue
