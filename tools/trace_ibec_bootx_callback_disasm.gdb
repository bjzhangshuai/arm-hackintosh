set pagination off
set confirm off
set architecture aarch64

# Attach after iBEC has entered the Stage2 recovery prompt.  This stops at the
# final SVC #7 stage-switch callback call and dumps the generated
# trampoline/callback body plus its nearby literal table.  It is
# diagnostic-only: no registers or guest memory are patched, and execution is
# not single-stepped.

set $callback_disasm_target = 0
set $callback_disasm_literal_base = 0

target remote 127.0.0.1:12345

break *0x70087c8c
commands
  silent
  set $callback_disasm_target = $x24
  printf "IBEC_BOOTX_CALLBACK_DISASM_CALL pc=0x%lx callback=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx sp=0x%lx x30=0x%lx cpsr=0x%lx\n", $pc, $callback_disasm_target, $x0, $x1, $x2, $x3, $x4, $sp, $x30, $cpsr
  if $callback_disasm_target >= 0x70000000 && $callback_disasm_target < 0xd0000000
    x/192i $callback_disasm_target
    set $callback_disasm_literal_base = $callback_disasm_target + 0x240
    x/32gx $callback_disasm_literal_base
  end
  detach
  quit
end

continue
