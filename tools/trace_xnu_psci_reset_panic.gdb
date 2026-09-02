set pagination off
set confirm off
set architecture aarch64

# Follow the restore handoff into high-address XNU, then stop only when the
# shared PSCI HVC veneer is invoked with SYSTEM_RESET.  This captures the panic
# or reboot call chain before QEMU resets the machine.  Read-only: the script
# never changes guest registers or memory.

set $xnu_reset_trampoline = 0
set $xnu_reset_ret = 0
set $xnu_reset_frame_index = 0
set $xnu_reset_fp = 0
set $xnu_reset_next_fp = 0
set $xnu_reset_saved_lr = 0
set $xnu_reset_canonical_lr = 0

target remote 127.0.0.1:12345

hbreak *0xfffffe0021bef310
set $xnu_reset_bp = $bpnum
condition $xnu_reset_bp $x0 == 0x84000009
disable $xnu_reset_bp
commands $xnu_reset_bp
  silent
  printf "XNU_PSCI_SYSTEM_RESET_BEFORE pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x5=0x%lx x6=0x%lx x7=0x%lx x8=0x%lx x16=0x%lx x17=0x%lx x29=0x%lx x30=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x5, $x6, $x7, $x8, $x16, $x17, $x29, $x30, $sp, $cpsr
  printf "XNU_PSCI_SYSTEM_RESET_THREADS\n"
  info threads
  thread apply all p/x $pc
  printf "XNU_PSCI_SYSTEM_RESET_DISASM\n"
  x/160i $pc-0x180
  printf "XNU_PSCI_SYSTEM_RESET_BACKTRACE\n"
  bt
  printf "XNU_PSCI_SYSTEM_RESET_STACK_WORDS\n"
  x/192gx $sp
  printf "XNU_PSCI_SYSTEM_RESET_STACK_CHARS\n"
  x/768cb $sp
  printf "XNU_PSCI_SYSTEM_RESET_FRAME_POINTERS\n"
  set $xnu_reset_fp = $x29
  set $xnu_reset_frame_index = 0
  while $xnu_reset_frame_index < 12 && $xnu_reset_fp >= 0xffff000000000000
    set $xnu_reset_next_fp = *(unsigned long long *)$xnu_reset_fp
    set $xnu_reset_saved_lr = *(unsigned long long *)($xnu_reset_fp + 8)
    set $xnu_reset_canonical_lr = 0xffff000000000000 | ($xnu_reset_saved_lr & 0x0000ffffffffffff)
    printf "XNU_PSCI_SYSTEM_RESET_FRAME index=%u fp=0x%lx next_fp=0x%lx saved_lr=0x%lx canonical_lr=0x%lx\n", $xnu_reset_frame_index, $xnu_reset_fp, $xnu_reset_next_fp, $xnu_reset_saved_lr, $xnu_reset_canonical_lr
    set $xnu_reset_fp = $xnu_reset_next_fp
    set $xnu_reset_frame_index = $xnu_reset_frame_index + 1
  end
  detach
  quit
end

break *0x70087c8c
commands
  silent
  set $xnu_reset_trampoline = $x24
  printf "XNU_PSCI_SYSTEM_RESET_CALLBACK pc=0x%lx trampoline=0x%lx entry=0x%lx boot_args=0x%lx sp=0x%lx x30=0x%lx cpsr=0x%lx\n", $pc, $xnu_reset_trampoline, $x0, $x1, $sp, $x30, $cpsr
  if $xnu_reset_trampoline >= 0x70000000 && $xnu_reset_trampoline < 0xd0000000
    set $xnu_reset_ret = $xnu_reset_trampoline + 0x2b8
    advance *$xnu_reset_ret
    si
    si
    advance *0x76f5c104
    advance *0x76f5c13c
    advance *0x76f5c1f4
    advance *0x76f5c33c
    si
    si
    advance *0x76f5c384
    si
    printf "XNU_PSCI_SYSTEM_RESET_HIGH_ENTRY pc=0x%lx x0=0x%lx x1=0x%lx x22=0x%lx x23=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x22, $x23, $sp, $cpsr
    enable $xnu_reset_bp
    printf "XNU_PSCI_SYSTEM_RESET_ARMED breakpoint=%u pc=0x%lx\n", $xnu_reset_bp, $pc
  end
  continue
end

continue
