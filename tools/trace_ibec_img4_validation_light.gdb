# Fast relocated iBEC IMG4 validation probe.
#
# Use this for recovery-side RestoreRamDisk/RestoreDeviceTree failures after
# the USB transport is already known to work.  It keeps the same signed
# iBSS -> LocalPolicy -> iBEC path as the USB restore light probe, but adds
# targeted breakpoints in iBEC's common IMG4 validation entry:
#
#   0x7008af74  common validation entry
#   0x7008afec  IMG4 parse return
#   0x7008b060  deeper validation/load return
#   0x7008b090  failure cleanup path
#   0x7008b098  final return point
#
# Addresses are for macOS 26.6 (25G72) VirtualMac2,1 iBEC.runtime-last.bin at
# relocation base 0x7006c000.
set $phase = 0
set $in_relocated_ibec = 0
set $img4_validate_count = 0
set $img4_validate_caller = 0
set $img4_parse_ptr = 0
set $img4_parse_end = 0
set $img4_parse_aux0 = 0
set $img4_parse_aux1 = 0

break *0x7008af74
condition $bpnum $phase == 1
commands
  silent
  set $img4_validate_count = $img4_validate_count + 1
  set $img4_validate_caller = $x30
  printf "IBEC_IMG4_VALIDATE_ENTER index=%u caller=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x5=0x%lx x6=0x%lx x7=0x%lx sp=0x%lx\n", $img4_validate_count, $x30, $x0, $x1, $x2, $x3, $x4, $x5, $x6, $x7, $sp
  continue
end

break *0x7008afec
condition $bpnum $phase == 1
commands
  silent
  set $img4_parse_ptr = $x0
  set $img4_parse_end = $x1
  set $img4_parse_aux0 = $x2
  set $img4_parse_aux1 = $x3
  printf "IBEC_IMG4_PARSE_RETURN index=%u caller=0x%lx ptr=0x%lx end=0x%lx aux0=0x%lx aux1=0x%lx w0=0x%x\n", $img4_validate_count, $img4_validate_caller, $x0, $x1, $x2, $x3, $w0
  if $x0 != 0
    x/8wx $x0
  end
  continue
end

break *0x7008b060
condition $bpnum $phase == 1
commands
  silent
  printf "IBEC_IMG4_DEEP_RETURN index=%u caller=0x%lx result=0x%lx w0=0x%x parsed=0x%lx parsed_end=0x%lx aux0=0x%lx aux1=0x%lx\n", $img4_validate_count, $img4_validate_caller, $x0, $w0, $img4_parse_ptr, $img4_parse_end, $img4_parse_aux0, $img4_parse_aux1
  continue
end

break *0x7008b090
condition $bpnum $phase == 1
commands
  silent
  printf "IBEC_IMG4_FAILURE_PATH index=%u caller=0x%lx parsed=0x%lx deep_result=0x%lx w0=0x%x\n", $img4_validate_count, $img4_validate_caller, $img4_parse_ptr, $x19, $w0
  continue
end

break *0x7008b098
condition $bpnum $phase == 1
commands
  silent
  printf "IBEC_IMG4_VALIDATE_RETURN index=%u caller=0x%lx final=0x%lx w0=0x%x parsed=0x%lx deep_result=0x%lx\n", $img4_validate_count, $img4_validate_caller, $x0, $w0, $img4_parse_ptr, $x19
  continue
end

set $relocate_ibec_for_final_callback = 1
set $trace_relocated_ibec_halt = 1
set $trace_relocated_ibec_exceptions = 1
set $trace_relocated_ibec_init_failure = 1
set $trace_relocated_ibec_context_return = 0
set $trace_relocated_ibec_descriptor_table = 0
set $restore_relocated_ibec_descriptor_table = 1
set $restore_relocated_ibec_static_tail = 1
set $trace_relocated_ibec_root_build = 0
set $trace_relocated_ibec_descriptor_presence = 0
set $trace_relocated_ibec_map_checks = 0
set $trace_relocated_ibec_bdif_enum = 1
set $trace_ibec_allocator = 0
source /home/macvm/src/macvm/tools/trace_ibss_lpol_then_ibec_inject.gdb
