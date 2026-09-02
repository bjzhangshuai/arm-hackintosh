set pagination off
set confirm off
set architecture aarch64

# Attach after iBEC has entered the Stage2 recovery prompt.  Follow the final
# SVC #7 handoff into MMU-enabled XNU, stop immediately before the branch into
# the early Mach-O/kernel-collection parser, and dump both the input header and
# the complete parser window.  Diagnostic only: no registers or guest memory
# are modified.

set $kernel_macho_trampoline = 0
set $kernel_macho_entry = 0
set $kernel_macho_boot_args = 0
set $kernel_macho_ret = 0
set $kernel_macho_slide = 0
set $kernel_macho_low_pc = 0

target remote 127.0.0.1:12345

break *0x70087c8c
commands
  silent
  set $kernel_macho_trampoline = $x24
  set $kernel_macho_entry = $x0
  set $kernel_macho_boot_args = $x1
  printf "IBEC_BOOTX_KERNEL_MACHO_CALLBACK_CALL pc=0x%lx trampoline=0x%lx entry=0x%lx boot_args=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx sp=0x%lx x30=0x%lx cpsr=0x%lx\n", $pc, $kernel_macho_trampoline, $kernel_macho_entry, $kernel_macho_boot_args, $x2, $x3, $x4, $sp, $x30, $cpsr
  if $kernel_macho_trampoline >= 0x70000000 && $kernel_macho_trampoline < 0xd0000000
    set $kernel_macho_ret = $kernel_macho_trampoline + 0x2b8
    advance *$kernel_macho_ret
    si
    si
    advance *0x76f5c104
    advance *0x76f5c13c
    advance *0x76f5c1f4
    advance *0x76f5c33c
    printf "IBEC_BOOTX_KERNEL_MACHO_BOOTSTRAP_HVC_BEFORE pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x30=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x30, $sp, $cpsr
    si
    printf "IBEC_BOOTX_KERNEL_MACHO_BOOTSTRAP_HVC_AFTER pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x30=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x30, $sp, $cpsr
    si
    advance *0x76f5c384
    si
    set $kernel_macho_slide = $x22 - $x23
    set $kernel_macho_low_pc = $pc - $kernel_macho_slide
    printf "IBEC_BOOTX_KERNEL_MACHO_HIGH_ENTRY pc=0x%lx low_pc=0x%lx slide=0x%lx x0=0x%lx x1=0x%lx x20=0x%lx x21=0x%lx x22=0x%lx x23=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $kernel_macho_low_pc, $kernel_macho_slide, $x0, $x1, $x20, $x21, $x22, $x23, $sp, $cpsr
    advance *0xfffffe0023888364
    printf "IBEC_BOOTX_KERNEL_MACHO_BRANCH pc=0x%lx x8=0x%lx x9=0x%lx x13=0x%lx x14=0x%lx x20=0x%lx x21=0x%lx x22=0x%lx x23=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x8, $x9, $x13, $x14, $x20, $x21, $x22, $x23, $sp, $cpsr
    printf "IBEC_BOOTX_KERNEL_MACHO_HEADER_64\n"
    x/16gx $x21
    printf "IBEC_BOOTX_KERNEL_MACHO_HEADER_32\n"
    x/32wx $x21
    si
    printf "IBEC_BOOTX_KERNEL_MACHO_LOOP_ENTRY pc=0x%lx x8=0x%lx x9=0x%lx x13=0x%lx x14=0x%lx x20=0x%lx x21=0x%lx x22=0x%lx x23=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x8, $x9, $x13, $x14, $x20, $x21, $x22, $x23, $sp, $cpsr
    printf "IBEC_BOOTX_KERNEL_MACHO_LOOP_DISASM\n"
    x/512i 0xfffffe0023888a80
  end
  detach
  quit
end

continue
