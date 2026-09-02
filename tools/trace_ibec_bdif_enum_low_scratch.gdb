# Trace the relocated iBEC BDIF device enumeration path after the low-scratch
# QEMU fix.  This wrapper keeps the static-tail and descriptor-table diagnostic
# restores enabled, but only turns on the narrow BDIF enum breakpoints needed to
# explain why the restore USB backend is detected but not consumed.
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
source /home/macvm/src/macvm/tools/trace_ibss_lpol_then_ibec_inject.gdb
