set pagination off
set confirm off
set architecture aarch64

# Attach after iBEC has entered the Stage2 recovery prompt.  This follows the
# SVC #7 trampoline into MMU-enabled XNU, then records the first high-address
# initialization milestones before the vmapple PAC HVC calls.  It uses hardcoded
# high addresses from the fixed restore-random seed and is diagnostic-only: no
# registers or guest memory are patched.

set $kernel_high_ms_trampoline = 0
set $kernel_high_ms_entry = 0
set $kernel_high_ms_boot_args = 0
set $kernel_high_ms_ret = 0
set $kernel_high_ms_slide = 0

target remote 127.0.0.1:12345

break *0x70087c8c
commands
  silent
  set $kernel_high_ms_trampoline = $x24
  set $kernel_high_ms_entry = $x0
  set $kernel_high_ms_boot_args = $x1
  printf "IBEC_BOOTX_KERNEL_HIGH_MS_CALLBACK_CALL pc=0x%lx trampoline=0x%lx entry=0x%lx boot_args=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx sp=0x%lx x30=0x%lx cpsr=0x%lx\n", $pc, $kernel_high_ms_trampoline, $kernel_high_ms_entry, $kernel_high_ms_boot_args, $x2, $x3, $x4, $sp, $x30, $cpsr
  if $kernel_high_ms_trampoline >= 0x70000000 && $kernel_high_ms_trampoline < 0xd0000000
    set $kernel_high_ms_ret = $kernel_high_ms_trampoline + 0x2b8
    advance *$kernel_high_ms_ret
    si
    si
    advance *0x76f5c104
    advance *0x76f5c13c
    advance *0x76f5c1f4
    advance *0x76f5c33c
    printf "IBEC_BOOTX_KERNEL_HIGH_MS_BOOTSTRAP_HVC_BEFORE pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x30=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x30, $sp, $cpsr
    si
    printf "IBEC_BOOTX_KERNEL_HIGH_MS_BOOTSTRAP_HVC_AFTER pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x30=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x30, $sp, $cpsr
    si
    printf "IBEC_BOOTX_KERNEL_HIGH_MS_BOOTSTRAP_AFTER_CBNZ pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x30=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x30, $sp, $cpsr
    advance *0x76f5c384
    si
    set $kernel_high_ms_slide = $x22 - $x23
    printf "IBEC_BOOTX_KERNEL_HIGH_MS_ENTRY pc=0x%lx slide=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x19=0x%lx x20=0x%lx x22=0x%lx x23=0x%lx x30=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $kernel_high_ms_slide, $x0, $x1, $x2, $x3, $x4, $x19, $x20, $x22, $x23, $x30, $sp, $cpsr
  end
  continue
end

break *0xfffffe00238881f4
commands
  silent
  printf "IBEC_BOOTX_KERNEL_HIGH_MS_REBASE_BRANCH pc=0x%lx w8=0x%x x8=0x%lx x22=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $w8, $x8, $x22, $sp, $cpsr
  continue
end

break *0xfffffe00238882ec
commands
  silent
  printf "IBEC_BOOTX_KERNEL_HIGH_MS_REBASE_DONE pc=0x%lx x0=0x%lx x8=0x%lx x9=0x%lx x20=0x%lx x22=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x8, $x9, $x20, $x22, $sp, $cpsr
  continue
end

break *0xfffffe0023888304
commands
  silent
  printf "IBEC_BOOTX_KERNEL_HIGH_MS_STATIC_BRANCH pc=0x%lx x8=0x%lx x13=0x%lx x20=0x%lx x22=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x8, $x13, $x20, $x22, $sp, $cpsr
  continue
end

break *0xfffffe00238883b8
commands
  silent
  printf "IBEC_BOOTX_KERNEL_HIGH_MS_PLATFORM_RANGE_DONE pc=0x%lx x0=0x%lx x19=0x%lx x20=0x%lx x21=0x%lx x22=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x19, $x20, $x21, $x22, $sp, $cpsr
  continue
end

break *0xfffffe002388842c
commands
  silent
  printf "IBEC_BOOTX_KERNEL_HIGH_MS_INITCALL_LOOP pc=0x%lx x8=0x%lx x17=0x%lx x19=0x%lx x20=0x%lx x21=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x8, $x17, $x19, $x20, $x21, $sp, $cpsr
  continue
end

break *0xfffffe0023888444
commands
  silent
  printf "IBEC_BOOTX_KERNEL_HIGH_MS_INITCALL_DONE pc=0x%lx x8=0x%lx x19=0x%lx x20=0x%lx x21=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x8, $x19, $x20, $x21, $sp, $cpsr
  continue
end

break *0xfffffe0023888468
commands
  silent
  printf "IBEC_BOOTX_KERNEL_HIGH_MS_BOOTARGS_COPY_DONE pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x19=0x%lx x20=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x19, $x20, $sp, $cpsr
  continue
end

break *0xfffffe0023888490
commands
  silent
  printf "IBEC_BOOTX_KERNEL_HIGH_MS_PRE_PAC_DEFAULTS pc=0x%lx x0=0x%lx x8=0x%lx x19=0x%lx x20=0x%lx x30=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x8, $x19, $x20, $x30, $sp, $cpsr
  continue
end

break *0xfffffe00238884c0
commands
  silent
  printf "IBEC_BOOTX_KERNEL_HIGH_MS_PAC_GET_DEFAULT_1_BEFORE pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x10=0x%lx x11=0x%lx x12=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x10, $x11, $x12, $sp, $cpsr
  si
  printf "IBEC_BOOTX_KERNEL_HIGH_MS_PAC_GET_DEFAULT_1_AFTER pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x10=0x%lx x11=0x%lx x12=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x10, $x11, $x12, $sp, $cpsr
  si
  printf "IBEC_BOOTX_KERNEL_HIGH_MS_PAC_GET_DEFAULT_1_AFTER_CBNZ pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x10=0x%lx x11=0x%lx x12=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x10, $x11, $x12, $sp, $cpsr
  continue
end

break *0xfffffe0023888504
commands
  silent
  printf "IBEC_BOOTX_KERNEL_HIGH_MS_PAC_GET_DEFAULT_2_BEFORE pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x8=0x%lx x9=0x%lx x10=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x8, $x9, $x10, $sp, $cpsr
  si
  printf "IBEC_BOOTX_KERNEL_HIGH_MS_PAC_GET_DEFAULT_2_AFTER pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x8=0x%lx x9=0x%lx x10=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x8, $x9, $x10, $sp, $cpsr
  si
  printf "IBEC_BOOTX_KERNEL_HIGH_MS_PAC_GET_DEFAULT_2_AFTER_CBNZ pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x8=0x%lx x9=0x%lx x10=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x8, $x9, $x10, $sp, $cpsr
  continue
end

break *0xfffffe0023888514
commands
  silent
  printf "IBEC_BOOTX_KERNEL_HIGH_MS_PAC_DEFAULTS_DONE pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $sp, $cpsr
  detach
  quit
end

continue
