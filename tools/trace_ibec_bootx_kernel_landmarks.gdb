set pagination off
set confirm off
set architecture aarch64

# Attach after iBEC has entered the Stage2 recovery prompt.  This follows the
# SVC #7 trampoline into the macOS kernel entry, dumps the early kernel body,
# then advances over known long initialization loops so the next real blocker
# can be located without spending minutes single-stepping memset/page-table
# loops.  It is diagnostic-only: no registers or guest memory are patched.

set $kernel_landmarks_trampoline = 0
set $kernel_landmarks_entry = 0
set $kernel_landmarks_boot_args = 0
set $kernel_landmarks_ret = 0
set $kernel_landmarks_guard = 0

target remote 127.0.0.1:12345

break *0x70087c8c
commands
  silent
  set $kernel_landmarks_trampoline = $x24
  set $kernel_landmarks_entry = $x0
  set $kernel_landmarks_boot_args = $x1
  printf "IBEC_BOOTX_KERNEL_LANDMARKS_CALLBACK_CALL pc=0x%lx trampoline=0x%lx entry=0x%lx boot_args=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx sp=0x%lx x30=0x%lx cpsr=0x%lx\n", $pc, $kernel_landmarks_trampoline, $kernel_landmarks_entry, $kernel_landmarks_boot_args, $x2, $x3, $x4, $sp, $x30, $cpsr
  if $kernel_landmarks_boot_args >= 0x70000000 && $kernel_landmarks_boot_args < 0xd0000000
    x/32gx $kernel_landmarks_boot_args
  end
  if $kernel_landmarks_trampoline >= 0x70000000 && $kernel_landmarks_trampoline < 0xd0000000
    set $kernel_landmarks_ret = $kernel_landmarks_trampoline + 0x2b8
    advance *$kernel_landmarks_ret
    printf "IBEC_BOOTX_KERNEL_LANDMARKS_TRAMPOLINE_RET pc=0x%lx entry=0x%lx boot_args=0x%lx x0=0x%lx x1=0x%lx x29=0x%lx x30=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $kernel_landmarks_entry, $kernel_landmarks_boot_args, $x0, $x1, $x29, $x30, $sp, $cpsr
    si
    printf "IBEC_BOOTX_KERNEL_LANDMARKS_ENTRY pc=0x%lx entry=0x%lx boot_args=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx sp=0x%lx x30=0x%lx cpsr=0x%lx\n", $pc, $kernel_landmarks_entry, $kernel_landmarks_boot_args, $x0, $x1, $x2, $sp, $x30, $cpsr
    si
    printf "IBEC_BOOTX_KERNEL_LANDMARKS_BRANCH_TARGET pc=0x%lx entry=0x%lx boot_args=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx sp=0x%lx x30=0x%lx cpsr=0x%lx\n", $pc, $kernel_landmarks_entry, $kernel_landmarks_boot_args, $x0, $x1, $x2, $sp, $x30, $cpsr
    if $pc >= 0x70000000 && $pc < 0xd0000000
      x/384i $pc
    end
    advance *0x76f5c104
    printf "IBEC_BOOTX_KERNEL_LANDMARKS_ZERO_TABLE_DONE pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x20=0x%lx x22=0x%lx x23=0x%lx x24=0x%lx x25=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x20, $x22, $x23, $x24, $x25, $sp, $cpsr
    set $kernel_landmarks_guard = 0
    while $pc != 0x76f5c13c && $kernel_landmarks_guard < 48
      si
      set $kernel_landmarks_guard = $kernel_landmarks_guard + 1
      printf "IBEC_BOOTX_KERNEL_LANDMARKS_ASLR_STEP index=%u pc=0x%lx x0=0x%lx x1=0x%lx x18=0x%lx x22=0x%lx x23=0x%lx x24=0x%lx sp=0x%lx cpsr=0x%lx\n", $kernel_landmarks_guard, $pc, $x0, $x1, $x18, $x22, $x23, $x24, $sp, $cpsr
    end
    if $pc == 0x76f5c11c
      printf "IBEC_BOOTX_KERNEL_LANDMARKS_STATIC_REGION_SPIN pc=0x%lx w1=0x%x x0=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $w1, $x0, $sp, $cpsr
      detach
      quit
    end
    if $pc == 0x76f5c13c
      printf "IBEC_BOOTX_KERNEL_LANDMARKS_ASLR_DONE pc=0x%lx x0=0x%lx x18=0x%lx x22=0x%lx x23=0x%lx x24=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x18, $x22, $x23, $x24, $sp, $cpsr
      advance *0x76f5c1f4
      printf "IBEC_BOOTX_KERNEL_LANDMARKS_MAP1_DONE pc=0x%lx x0=0x%lx x2=0x%lx x4=0x%lx x5=0x%lx x6=0x%lx x10=0x%lx x14=0x%lx x15=0x%lx x24=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x2, $x4, $x5, $x6, $x10, $x14, $x15, $x24, $sp, $cpsr
      x/96i $pc
    end
  end
  detach
  quit
end

continue
