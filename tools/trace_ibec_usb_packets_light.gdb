# Fast relocated iBEC USB packet-format probe.
#
# This uses the known-good signed restore path, then traces only the relocated
# iBEC USB packet parser and request wrappers needed to reverse the host-side
# restore transaction format.  It remains observe-only: no synthetic USB
# packets or descriptor patches are injected here beyond the already-required
# static-tail/descriptor-table restores used by the light restore probe.
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
set $trace_relocated_ibec_bdif_enum = 0
set $trace_relocated_ibec_usb_packets = 1
set $trace_ibec_allocator = 0
source /home/macvm/src/macvm/tools/trace_ibss_lpol_then_ibec_inject.gdb
