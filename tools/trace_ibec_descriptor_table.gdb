set pagination off
set confirm off
set architecture aarch64

# macOS 26.6 (25G72) VirtualMac2,1 live descriptor-table probe.  Run only in
# the disposable Linux validation VM.  This trace does not inject or patch any
# descriptor; it only checks whether relocated iBEC still has the static
# selector table entry for restore root (selector 0xa7) and whether the live
# lookup loop reaches it.
set $relocate_ibec_for_final_callback = 1
set $trace_relocated_ibec_halt = 1
set $trace_relocated_ibec_exceptions = 1
set $trace_relocated_ibec_init_failure = 1
set $trace_relocated_ibec_context_return = 1
set $trace_relocated_ibec_descriptor_table = 1

source /home/macvm/src/macvm/tools/trace_ibss_lpol_then_ibec_inject.gdb
