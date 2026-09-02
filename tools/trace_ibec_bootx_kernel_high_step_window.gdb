set pagination off
set confirm off
set architecture aarch64

# Attach after iBEC has entered the Stage2 recovery prompt.  This follows the
# SVC #7 trampoline into MMU-enabled XNU and records a bounded high-address
# instruction window.  Unlike the milestone breakpoint trace, this follows the
# actual dynamic control flow through calls and loops.  It is diagnostic-only:
# no registers or guest memory are patched.

set $kernel_high_step_trampoline = 0
set $kernel_high_step_entry = 0
set $kernel_high_step_boot_args = 0
set $kernel_high_step_ret = 0
set $kernel_high_step_slide = 0
set $kernel_high_step_low_pc = 0
set $kernel_high_step_count = 0
set $kernel_high_step_limit = 1024

target remote 127.0.0.1:12345

break *0x70087c8c
commands
  silent
  set $kernel_high_step_trampoline = $x24
  set $kernel_high_step_entry = $x0
  set $kernel_high_step_boot_args = $x1
  printf "IBEC_BOOTX_KERNEL_HIGH_STEP_CALLBACK_CALL pc=0x%lx trampoline=0x%lx entry=0x%lx boot_args=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx sp=0x%lx x30=0x%lx cpsr=0x%lx\n", $pc, $kernel_high_step_trampoline, $kernel_high_step_entry, $kernel_high_step_boot_args, $x2, $x3, $x4, $sp, $x30, $cpsr
  if $kernel_high_step_trampoline >= 0x70000000 && $kernel_high_step_trampoline < 0xd0000000
    set $kernel_high_step_ret = $kernel_high_step_trampoline + 0x2b8
    advance *$kernel_high_step_ret
    si
    si
    advance *0x76f5c104
    advance *0x76f5c13c
    advance *0x76f5c1f4
    advance *0x76f5c33c
    printf "IBEC_BOOTX_KERNEL_HIGH_STEP_BOOTSTRAP_HVC_BEFORE pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x30=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x30, $sp, $cpsr
    si
    printf "IBEC_BOOTX_KERNEL_HIGH_STEP_BOOTSTRAP_HVC_AFTER pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x30=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x30, $sp, $cpsr
    si
    printf "IBEC_BOOTX_KERNEL_HIGH_STEP_BOOTSTRAP_AFTER_CBNZ pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x30=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x30, $sp, $cpsr
    advance *0x76f5c384
    si
    set $kernel_high_step_slide = $x22 - $x23
    printf "IBEC_BOOTX_KERNEL_HIGH_STEP_ENTRY pc=0x%lx slide=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x19=0x%lx x20=0x%lx x22=0x%lx x23=0x%lx x30=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $kernel_high_step_slide, $x0, $x1, $x2, $x3, $x4, $x19, $x20, $x22, $x23, $x30, $sp, $cpsr
    set $kernel_high_step_count = 0
    while $kernel_high_step_count < $kernel_high_step_limit
      set $kernel_high_step_low_pc = $pc - $kernel_high_step_slide
      if $kernel_high_step_count < 128 || $kernel_high_step_count % 32 == 0 || $pc == 0xfffffe00238884c0 || $pc == 0xfffffe0023888504
        printf "IBEC_BOOTX_KERNEL_HIGH_STEP index=%u pc=0x%lx low_pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x8=0x%lx x17=0x%lx x30=0x%lx sp=0x%lx cpsr=0x%lx\n", $kernel_high_step_count, $pc, $kernel_high_step_low_pc, $x0, $x1, $x2, $x3, $x4, $x8, $x17, $x30, $sp, $cpsr
      end
      if $pc == 0xfffffe00238884c0
        printf "IBEC_BOOTX_KERNEL_HIGH_STEP_PAC_GET_DEFAULT_1_BEFORE pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $sp, $cpsr
      end
      if $pc == 0xfffffe0023888504
        printf "IBEC_BOOTX_KERNEL_HIGH_STEP_PAC_GET_DEFAULT_2_BEFORE pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $sp, $cpsr
      end
      si
      if $pc == 0xfffffe00238884c4
        printf "IBEC_BOOTX_KERNEL_HIGH_STEP_PAC_GET_DEFAULT_1_AFTER pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $sp, $cpsr
      end
      if $pc == 0xfffffe0023888508
        printf "IBEC_BOOTX_KERNEL_HIGH_STEP_PAC_GET_DEFAULT_2_AFTER pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $sp, $cpsr
      end
      set $kernel_high_step_count = $kernel_high_step_count + 1
    end
    printf "IBEC_BOOTX_KERNEL_HIGH_STEP_LIMIT_REACHED count=%u pc=0x%lx low_pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x8=0x%lx x17=0x%lx x30=0x%lx sp=0x%lx cpsr=0x%lx\n", $kernel_high_step_count, $pc, $kernel_high_step_low_pc, $x0, $x1, $x2, $x3, $x4, $x8, $x17, $x30, $sp, $cpsr
  end
  detach
  quit
end

continue
