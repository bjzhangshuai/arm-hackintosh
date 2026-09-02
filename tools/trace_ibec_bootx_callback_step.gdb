set pagination off
set confirm off
set architecture aarch64

# Attach after iBEC has entered the Stage2 recovery prompt.  This waits until
# the SVC #7 stage-switch path has selected its final callback, dumps the
# callback/trampoline at x24, and single-steps a bounded number of instructions
# starting at the authenticated branch.  It is diagnostic-only: no registers or
# guest memory are patched.

set $callback_step_seen = 0
set $callback_step_count = 0
set $callback_step_limit = 160
set $callback_step_target = 0

target remote 127.0.0.1:12345

break *0x70087c8c
commands
  silent
  set $callback_step_seen = 1
  set $callback_step_target = $x24
  printf "IBEC_BOOTX_CALLBACK_STEP_CALL pc=0x%lx callback=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx sp=0x%lx x30=0x%lx cpsr=0x%lx\n", $pc, $callback_step_target, $x0, $x1, $x2, $x3, $x4, $sp, $x30, $cpsr
  if $callback_step_target >= 0x70000000 && $callback_step_target < 0xd0000000
    x/48i $callback_step_target
  end
  set $callback_step_count = 0
  while $callback_step_count < $callback_step_limit
    si
    set $callback_step_count = $callback_step_count + 1
    printf "IBEC_BOOTX_CALLBACK_STEP index=%u pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx sp=0x%lx x30=0x%lx cpsr=0x%lx\n", $callback_step_count, $pc, $x0, $x1, $x2, $x3, $x4, $sp, $x30, $cpsr
    if $pc >= 0x70000000 && $pc < 0xd0000000
      x/i $pc
    end
  end
  detach
  quit
end

continue
