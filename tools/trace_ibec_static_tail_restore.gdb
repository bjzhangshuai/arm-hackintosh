set pagination off
set confirm off
set architecture aarch64

# macOS 26.6 (25G72) VirtualMac2,1 static-tail restore probe.  Run only in the
# disposable Linux validation VM.  This diagnostic restores the decompressed
# iBEC static-data tail after relocated iBEC has cleared its tables, so we can
# verify whether the Firebloom metadata next to the descriptor table is the
# current root-build blocker.  It is not a production boot strategy.
set $relocate_ibec_for_final_callback = 1
set $trace_relocated_ibec_halt = 1
set $trace_relocated_ibec_exceptions = 1
set $trace_relocated_ibec_init_failure = 1
set $trace_relocated_ibec_context_return = 1
set $trace_relocated_ibec_descriptor_table = 1
set $restore_relocated_ibec_descriptor_table = 1
set $restore_relocated_ibec_static_tail = 1
set $trace_relocated_ibec_root_build = 1

source /home/macvm/src/macvm/tools/trace_ibss_lpol_then_ibec_inject.gdb
