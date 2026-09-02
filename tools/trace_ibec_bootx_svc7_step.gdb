set pagination off
set confirm off
set architecture aarch64

# Attach after iBEC has already entered the Stage2 recovery prompt.  The
# restore helper uploads TrustCache/RamDisk/DeviceTree/KernelCache and issues
# bootx while this breakpoint waits for the final handoff SVC.  The script then
# single-steps a bounded number of guest instructions to classify where SVC #7
# goes next without leaving an interactive debugger attached.

set $svc7_step_count = 0
set $svc7_step_limit = 96

target remote 127.0.0.1:12345

break *0x70087db8
commands
  silent
  printf "IBEC_BOOTX_SVC7_STEP_ENTER pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx sp=0x%lx x30=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $sp, $x30, $cpsr
  x/8i $pc
  set $svc7_step_count = 0
  while $svc7_step_count < $svc7_step_limit
    si
    set $svc7_step_count = $svc7_step_count + 1
    printf "IBEC_BOOTX_SVC7_STEP index=%u pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx sp=0x%lx x30=0x%lx cpsr=0x%lx\n", $svc7_step_count, $pc, $x0, $x1, $x2, $x3, $sp, $x30, $cpsr
    x/i $pc
  end
  detach
  quit
end

continue
