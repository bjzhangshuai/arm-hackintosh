set pagination off
set confirm off
set architecture aarch64

# Attach after iBEC has entered the Stage2 recovery prompt.  This follows the
# SVC #7 trampoline into the macOS kernel, verifies the early HVC return path,
# advances to the boot stub RET after SCTLR_EL1 is enabled, and single-steps a
# small bounded window after that RET.  It is diagnostic-only: no registers or
# guest memory are patched.

set $kernel_mmu_trampoline = 0
set $kernel_mmu_entry = 0
set $kernel_mmu_boot_args = 0
set $kernel_mmu_ret = 0
set $kernel_mmu_step_count = 0
set $kernel_mmu_step_limit = 96

target remote 127.0.0.1:12345

break *0x70087c8c
commands
  silent
  set $kernel_mmu_trampoline = $x24
  set $kernel_mmu_entry = $x0
  set $kernel_mmu_boot_args = $x1
  printf "IBEC_BOOTX_KERNEL_MMU_CALLBACK_CALL pc=0x%lx trampoline=0x%lx entry=0x%lx boot_args=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx sp=0x%lx x30=0x%lx cpsr=0x%lx\n", $pc, $kernel_mmu_trampoline, $kernel_mmu_entry, $kernel_mmu_boot_args, $x2, $x3, $x4, $sp, $x30, $cpsr
  if $kernel_mmu_trampoline >= 0x70000000 && $kernel_mmu_trampoline < 0xd0000000
    set $kernel_mmu_ret = $kernel_mmu_trampoline + 0x2b8
    advance *$kernel_mmu_ret
    si
    si
    printf "IBEC_BOOTX_KERNEL_MMU_BRANCH_TARGET pc=0x%lx entry=0x%lx boot_args=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx sp=0x%lx x30=0x%lx cpsr=0x%lx\n", $pc, $kernel_mmu_entry, $kernel_mmu_boot_args, $x0, $x1, $x2, $sp, $x30, $cpsr
    advance *0x76f5c104
    advance *0x76f5c13c
    advance *0x76f5c1f4
    advance *0x76f5c33c
    printf "IBEC_BOOTX_KERNEL_MMU_HVC_BEFORE pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x30=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x30, $sp, $cpsr
    si
    printf "IBEC_BOOTX_KERNEL_MMU_HVC_AFTER pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x30=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x30, $sp, $cpsr
    si
    printf "IBEC_BOOTX_KERNEL_MMU_AFTER_CBNZ pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x30=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x30, $sp, $cpsr
    advance *0x76f5c384
    printf "IBEC_BOOTX_KERNEL_MMU_BOOT_STUB_RET pc=0x%lx x0=0x%lx x20=0x%lx x22=0x%lx x23=0x%lx x30=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x20, $x22, $x23, $x30, $sp, $cpsr
    si
    printf "IBEC_BOOTX_KERNEL_MMU_AFTER_BOOT_STUB_RET pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x30=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x30, $sp, $cpsr
    set $kernel_mmu_step_count = 0
    while $kernel_mmu_step_count < $kernel_mmu_step_limit
      si
      set $kernel_mmu_step_count = $kernel_mmu_step_count + 1
      printf "IBEC_BOOTX_KERNEL_MMU_STEP index=%u pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x30=0x%lx sp=0x%lx cpsr=0x%lx\n", $kernel_mmu_step_count, $pc, $x0, $x1, $x2, $x3, $x4, $x30, $sp, $cpsr
    end
  end
  detach
  quit
end

continue
