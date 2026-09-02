set pagination off
set confirm off
set architecture aarch64

# Attach after iBEC has entered the Stage2 recovery prompt.  This follows the
# SVC #7 trampoline into the kernel entry, executes the entry branch, dumps the
# early kernel code, and single-steps a bounded window.  It is diagnostic-only:
# no registers or guest memory are patched.

set $kernel_early_trampoline = 0
set $kernel_early_entry = 0
set $kernel_early_boot_args = 0
set $kernel_early_ret = 0
set $kernel_early_step_count = 0
set $kernel_early_step_limit = 512

target remote 127.0.0.1:12345

break *0x70087c8c
commands
  silent
  set $kernel_early_trampoline = $x24
  set $kernel_early_entry = $x0
  set $kernel_early_boot_args = $x1
  printf "IBEC_BOOTX_KERNEL_EARLY_CALLBACK_CALL pc=0x%lx trampoline=0x%lx entry=0x%lx boot_args=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx sp=0x%lx x30=0x%lx cpsr=0x%lx\n", $pc, $kernel_early_trampoline, $kernel_early_entry, $kernel_early_boot_args, $x2, $x3, $x4, $sp, $x30, $cpsr
  if $kernel_early_trampoline >= 0x70000000 && $kernel_early_trampoline < 0xd0000000
    set $kernel_early_ret = $kernel_early_trampoline + 0x2b8
    advance *$kernel_early_ret
    printf "IBEC_BOOTX_KERNEL_EARLY_TRAMPOLINE_RET pc=0x%lx entry=0x%lx boot_args=0x%lx x0=0x%lx x1=0x%lx x29=0x%lx x30=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $kernel_early_entry, $kernel_early_boot_args, $x0, $x1, $x29, $x30, $sp, $cpsr
    si
    printf "IBEC_BOOTX_KERNEL_EARLY_ENTRY pc=0x%lx entry=0x%lx boot_args=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx sp=0x%lx x30=0x%lx cpsr=0x%lx\n", $pc, $kernel_early_entry, $kernel_early_boot_args, $x0, $x1, $x2, $sp, $x30, $cpsr
    x/i $pc
    si
    printf "IBEC_BOOTX_KERNEL_EARLY_BRANCH_TARGET pc=0x%lx entry=0x%lx boot_args=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx sp=0x%lx x30=0x%lx cpsr=0x%lx\n", $pc, $kernel_early_entry, $kernel_early_boot_args, $x0, $x1, $x2, $sp, $x30, $cpsr
    if $pc >= 0x70000000 && $pc < 0xd0000000
      x/128i $pc
    end
    set $kernel_early_step_count = 0
    while $kernel_early_step_count < $kernel_early_step_limit
      si
      set $kernel_early_step_count = $kernel_early_step_count + 1
      printf "IBEC_BOOTX_KERNEL_EARLY_STEP index=%u pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx sp=0x%lx x30=0x%lx cpsr=0x%lx\n", $kernel_early_step_count, $pc, $x0, $x1, $x2, $x3, $x4, $sp, $x30, $cpsr
      if $pc >= 0x70000000 && $pc < 0xd0000000
        x/i $pc
      end
    end
  end
  detach
  quit
end

continue
