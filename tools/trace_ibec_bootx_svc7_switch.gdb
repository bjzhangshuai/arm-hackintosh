set pagination off
set confirm off
set architecture aarch64

# Attach after iBEC has entered the Stage2 recovery prompt.  This traces the
# SVC #7 dispatch and the final stage-switch callback selection without
# modifying guest registers or memory.

set $svc7_seen = 0
set $svc7_case_seen = 0
set $svc7_switch_seen = 0
set $svc7_stage_callback = 0

target remote 127.0.0.1:12345

break *0x70087db8
commands
  silent
  set $svc7_seen = 1
  printf "IBEC_BOOTX_SVC7_SWITCH_SVC7 pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx sp=0x%lx x30=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $sp, $x30, $cpsr
  continue
end

break *0x700d4484
condition $bpnum $svc7_seen
commands
  silent
  set $svc7_case_seen = 1
  printf "IBEC_BOOTX_SVC7_SWITCH_CASE7_DISPATCH pc=0x%lx payload=0x%lx aux=0x%lx kind=0x%lx has_arg3=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x20, $x21, $x23, $x26, $sp, $x30
  continue
end

break *0x700d6298
condition $bpnum $svc7_case_seen
commands
  silent
  printf "IBEC_BOOTX_SVC7_SWITCH_CASE7_ENTER pc=0x%lx payload=0x%lx aux=0x%lx kind=0x%lx has_arg3=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $sp, $x30
  continue
end

break *0x700d6300
condition $bpnum $svc7_case_seen
commands
  silent
  printf "IBEC_BOOTX_SVC7_SWITCH_KIND_COMPARE pc=0x%lx kind=0x%lx expected=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x20, $x8, $sp, $x30
  continue
end

break *0x700d6324
condition $bpnum $svc7_case_seen
commands
  silent
  printf "IBEC_BOOTX_SVC7_SWITCH_ACCEPTED pc=0x%lx flag=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x8, $sp, $x30
  continue
end

break *0x700d6674
condition $bpnum $svc7_case_seen
commands
  silent
  printf "IBEC_BOOTX_SVC7_SWITCH_STAGE_SWITCH_CALL pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $sp, $x30
  continue
end

break *0x70087bd4
condition $bpnum $svc7_case_seen
commands
  silent
  set $svc7_switch_seen = 1
  printf "IBEC_BOOTX_SVC7_SWITCH_STAGE_SWITCH_ENTER pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $sp, $x30
  continue
end

break *0x70087c10
condition $bpnum $svc7_switch_seen
commands
  silent
  printf "IBEC_BOOTX_SVC7_SWITCH_READY_CHECK_RETURN pc=0x%lx w0=0x%x sp=0x%lx x30=0x%lx\n", $pc, $w0, $sp, $x30
  continue
end

break *0x70087c54
condition $bpnum $svc7_switch_seen
commands
  silent
  printf "IBEC_BOOTX_SVC7_SWITCH_STATE_SET_RETURN pc=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $sp, $x30
  continue
end

break *0x70087c70
condition $bpnum $svc7_switch_seen
commands
  silent
  printf "IBEC_BOOTX_SVC7_SWITCH_CALLBACK_READY pc=0x%lx callback=0x%lx kind=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x24, $x23, $sp, $x30
  continue
end

break *0x70087c8c
condition $bpnum $svc7_switch_seen
commands
  silent
  set $svc7_stage_callback = $x24
  printf "IBEC_BOOTX_SVC7_SWITCH_CALLBACK_CALL pc=0x%lx callback=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $svc7_stage_callback, $x0, $x1, $x2, $x3, $x4, $sp, $x30
  if $svc7_stage_callback >= 0x70000000 && $svc7_stage_callback < 0xa0000000
    x/24i $svc7_stage_callback
  end
  continue
end

break *0x70087c90
condition $bpnum $svc7_switch_seen
commands
  silent
  printf "IBEC_BOOTX_SVC7_SWITCH_CALLBACK_RETURNED pc=0x%lx callback=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $svc7_stage_callback, $sp, $x30
  continue
end

break *0x70087c94
condition $bpnum $svc7_switch_seen
commands
  silent
  printf "IBEC_BOOTX_SVC7_SWITCH_BOUNDS_FAIL pc=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $sp, $x30
  continue
end

break *0x70087c98
condition $bpnum $svc7_switch_seen
commands
  silent
  printf "IBEC_BOOTX_SVC7_SWITCH_READY_FAIL pc=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $sp, $x30
  continue
end

break *0x70087cb0
condition $bpnum $svc7_switch_seen
commands
  silent
  printf "IBEC_BOOTX_SVC7_SWITCH_NO_CALLBACK pc=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $sp, $x30
  continue
end

break *0x7006c438
condition $bpnum $svc7_switch_seen
commands
  silent
  printf "IBEC_BOOTX_SVC7_SWITCH_PANIC_HALT pc=0x%lx callback=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $svc7_stage_callback, $sp, $x30
  continue
end

break *0x700cc818
commands
  silent
  set $svc7_esr = $x8
  set $svc7_far = $x9
  set $svc7_elr = *(unsigned long long *)($x19 + 240)
  set $svc7_ec = ($svc7_esr >> 26) & 0x3f
  set $svc7_iss = $svc7_esr & 0x1ffffff
  printf "IBEC_BOOTX_SVC7_SWITCH_EXCEPTION pc=0x%lx frame=0x%lx esr=0x%lx ec=0x%lx iss=0x%lx far=0x%lx saved_elr=0x%lx sp=0x%lx x30=0x%lx cpsr=0x%lx\n", $pc, $x19, $svc7_esr, $svc7_ec, $svc7_iss, $svc7_far, $svc7_elr, $sp, $x30, $cpsr
  continue
end

continue
