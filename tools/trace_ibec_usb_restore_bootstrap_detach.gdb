# Bootstrap-only probe for two-stage restore-command tracing.
#
# This follows the known-good signed iBSS -> LocalPolicy -> iBEC path, applies
# the same low-scratch/descriptor/static-tail repairs as the regular USB
# restore light probe, and then detaches once iBEC has enumerated the AUX BDIF
# device.  The smoke runner can then wait for the Stage2 recovery prompt and
# attach a second GDB script for command-phase breakpoints.
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
set $detach_after_ibec_aux_bdif_ready = 1
source /home/macvm/src/macvm/tools/trace_ibss_lpol_then_ibec_inject.gdb
