set pagination off
set confirm off
set architecture aarch64

# Attach after iBEC has entered the Stage2 recovery prompt.  This follows the
# final SVC #7 stage-switch trampoline to its RET and single-steps exactly one
# instruction into the kernel entry address selected by iBEC.  It is
# diagnostic-only: no registers or guest memory are patched.

set $kernel_entry_trace_trampoline = 0
set $kernel_entry_trace_entry = 0
set $kernel_entry_trace_boot_args = 0
set $kernel_entry_trace_ret = 0

target remote 127.0.0.1:12345

break *0x70087c8c
commands
  silent
  set $kernel_entry_trace_trampoline = $x24
  set $kernel_entry_trace_entry = $x0
  set $kernel_entry_trace_boot_args = $x1
  printf "IBEC_BOOTX_KERNEL_ENTRY_CALLBACK_CALL pc=0x%lx trampoline=0x%lx entry=0x%lx boot_args=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx sp=0x%lx x30=0x%lx cpsr=0x%lx\n", $pc, $kernel_entry_trace_trampoline, $kernel_entry_trace_entry, $kernel_entry_trace_boot_args, $x2, $x3, $x4, $sp, $x30, $cpsr
  if $kernel_entry_trace_entry >= 0x70000000 && $kernel_entry_trace_entry < 0xd0000000
    x/64i $kernel_entry_trace_entry
  end
  if $kernel_entry_trace_trampoline >= 0x70000000 && $kernel_entry_trace_trampoline < 0xd0000000
    set $kernel_entry_trace_ret = $kernel_entry_trace_trampoline + 0x2b8
    printf "IBEC_BOOTX_KERNEL_ENTRY_ADVANCE_TO_TRAMPOLINE_RET trampoline_ret=0x%lx\n", $kernel_entry_trace_ret
    advance *$kernel_entry_trace_ret
    printf "IBEC_BOOTX_KERNEL_ENTRY_TRAMPOLINE_RET pc=0x%lx entry=0x%lx boot_args=0x%lx x0=0x%lx x1=0x%lx x29=0x%lx x30=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $kernel_entry_trace_entry, $kernel_entry_trace_boot_args, $x0, $x1, $x29, $x30, $sp, $cpsr
    x/i $pc
    si
    printf "IBEC_BOOTX_KERNEL_ENTRY_AFTER_RET pc=0x%lx entry=0x%lx boot_args=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx sp=0x%lx x30=0x%lx cpsr=0x%lx\n", $pc, $kernel_entry_trace_entry, $kernel_entry_trace_boot_args, $x0, $x1, $x2, $sp, $x30, $cpsr
    if $pc >= 0x70000000 && $pc < 0xd0000000
      x/64i $pc
    end
  end
  detach
  quit
end

continue
