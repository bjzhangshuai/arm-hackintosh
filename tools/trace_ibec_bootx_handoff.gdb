set pagination off
set confirm off
set architecture aarch64

# Attach after the bootstrap GDB has loaded iBSS/LocalPolicy/iBEC and Stage2
# has reached the recovery prompt.  The restore helper then uploads
# TrustCache/RamDisk/DeviceTree/KernelCache and sends bootx.  This script traces
# the final bootx handoff point without changing registers or memory.
set $bootx_handoff_seen = 0

target remote 127.0.0.1:12345

# Kernelcache load/validate success returns to the post-boot preparation path,
# which eventually calls this tiny wrapper.
break *0x70087da8
commands
  silent
  set $bootx_handoff_seen = 1
  printf "IBEC_BOOTX_HANDOFF_WRAPPER_ENTER pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $sp, $x30
  x/16i $pc
  continue
end

# The wrapper invokes iBoot's SVC #7 path.  If this returns, it has not
# transferred control to a visible XNU boot path.
break *0x70087db8
commands
  silent
  printf "IBEC_BOOTX_HANDOFF_SVC7 pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $sp, $x30
  x/i $pc
  continue
end

break *0x70087dbc
commands
  silent
  printf "IBEC_BOOTX_HANDOFF_SVC7_RETURNED pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $sp, $x30
  x/24i $pc
  continue
end

# These are the same SVC7-side landmarks used by the bootstrap trace, reused
# here to distinguish "SVC accepted and switching" from "SVC returned to iBEC".
break *0x700be548
condition $bpnum $bootx_handoff_seen
commands
  silent
  printf "IBEC_BOOTX_SVC7_HANDLER_ENTER pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $sp, $x30
  continue
end

break *0x700c035c
condition $bpnum $bootx_handoff_seen
commands
  silent
  printf "IBEC_BOOTX_STAGE_SWITCH_ENTER pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $sp, $x30
  continue
end

break *0x700c0384
condition $bpnum $bootx_handoff_seen
commands
  silent
  printf "IBEC_BOOTX_STAGE_SWITCH_FAIL_NO_READY_FRAME pc=0x%lx x22=0x%lx x23=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x22, $x23, $sp, $x30
  continue
end

break *0x7007b898
condition $bpnum $bootx_handoff_seen
commands
  silent
  printf "IBEC_BOOTX_STAGE_SWITCH_FAIL_NO_CALLBACK pc=0x%lx x22=0x%lx x23=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x22, $x23, $sp, $x30
  continue
end

# Preserve exception evidence if the handoff hits a new fault.
break *0x700cc818
commands
  silent
  set $bootx_handoff_esr = $x8
  set $bootx_handoff_far = $x9
  set $bootx_handoff_elr = *(unsigned long long *)($x19 + 240)
  set $bootx_handoff_ec = ($bootx_handoff_esr >> 26) & 0x3f
  set $bootx_handoff_il = ($bootx_handoff_esr >> 25) & 0x1
  set $bootx_handoff_iss = $bootx_handoff_esr & 0x1ffffff
  printf "IBEC_BOOTX_HANDOFF_EXCEPTION_ESR_FAR pc=0x%lx frame=0x%lx esr=0x%lx ec=0x%lx il=%lu iss=0x%lx far=0x%lx saved_elr=0x%lx sp=0x%lx x30=0x%lx cpsr=0x%lx\n", $pc, $x19, $bootx_handoff_esr, $bootx_handoff_ec, $bootx_handoff_il, $bootx_handoff_iss, $bootx_handoff_far, $bootx_handoff_elr, $sp, $x30, $cpsr
  if $bootx_handoff_elr >= 0x7006c000 && $bootx_handoff_elr < 0x70130000
    x/32i $bootx_handoff_elr
  end
  continue
end

continue
