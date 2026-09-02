# Fast relocated iBEC USB restore probe.
#
# This keeps the known-good signed iBSS -> LocalPolicy -> iBEC path and the
# low-scratch/descriptor/static-tail repair switches, but disables allocator
# spam so socket/chardev restore experiments can reach the USB pending receive
# point quickly enough under x86_64 TCG.
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
