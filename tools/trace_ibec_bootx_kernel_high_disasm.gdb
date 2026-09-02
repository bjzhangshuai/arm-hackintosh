set pagination off
set confirm off
set architecture aarch64

# Attach after iBEC has entered the Stage2 recovery prompt.  This follows the
# SVC #7 trampoline into the macOS kernel, advances through the early HVC and
# boot-stub RET, then dumps the high-address XNU code now executing with MMU
# enabled.  It is diagnostic-only: no registers or guest memory are patched.

set $kernel_high_trampoline = 0
set $kernel_high_entry = 0
set $kernel_high_boot_args = 0
set $kernel_high_ret = 0
set $kernel_high_slide = 0
set $kernel_high_low_pc = 0

target remote 127.0.0.1:12345

break *0x70087c8c
commands
  silent
  set $kernel_high_trampoline = $x24
  set $kernel_high_entry = $x0
  set $kernel_high_boot_args = $x1
  printf "IBEC_BOOTX_KERNEL_HIGH_DISASM_CALLBACK_CALL pc=0x%lx trampoline=0x%lx entry=0x%lx boot_args=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx sp=0x%lx x30=0x%lx cpsr=0x%lx\n", $pc, $kernel_high_trampoline, $kernel_high_entry, $kernel_high_boot_args, $x2, $x3, $x4, $sp, $x30, $cpsr
  if $kernel_high_trampoline >= 0x70000000 && $kernel_high_trampoline < 0xd0000000
    set $kernel_high_ret = $kernel_high_trampoline + 0x2b8
    advance *$kernel_high_ret
    si
    si
    advance *0x76f5c104
    advance *0x76f5c13c
    advance *0x76f5c1f4
    advance *0x76f5c33c
    si
    si
    advance *0x76f5c384
    printf "IBEC_BOOTX_KERNEL_HIGH_DISASM_BOOT_STUB_RET pc=0x%lx x0=0x%lx x20=0x%lx x22=0x%lx x23=0x%lx x30=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x20, $x22, $x23, $x30, $sp, $cpsr
    si
    set $kernel_high_slide = $x22 - $x23
    set $kernel_high_low_pc = $pc - $kernel_high_slide
    printf "IBEC_BOOTX_KERNEL_HIGH_DISASM_AFTER_BOOT_STUB_RET pc=0x%lx low_pc=0x%lx slide=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x30=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $kernel_high_low_pc, $kernel_high_slide, $x0, $x1, $x2, $x3, $x4, $x30, $sp, $cpsr
    x/256i $pc
  end
  detach
  quit
end

continue
