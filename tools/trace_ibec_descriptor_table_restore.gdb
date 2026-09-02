set pagination off
set confirm off
set architecture aarch64

# macOS 26.6 (25G72) VirtualMac2,1 descriptor-table restore probe.  Run only
# in the disposable Linux validation VM.  This is a diagnostic shim, not the
# production fix: after relocated iBEC clears its descriptor-table region, this
# restores the 46-entry table captured from the decompressed iBEC runtime so we
# can measure exactly how far a complete descriptor table moves the boot chain.
set $relocate_ibec_for_final_callback = 1
set $trace_relocated_ibec_halt = 1
set $trace_relocated_ibec_exceptions = 1
set $trace_relocated_ibec_init_failure = 1
set $trace_relocated_ibec_context_return = 1
set $trace_relocated_ibec_descriptor_table = 1
set $restore_relocated_ibec_descriptor_table = 1
set $trace_relocated_ibec_root_build = 1

source /home/macvm/src/macvm/tools/trace_ibss_lpol_then_ibec_inject.gdb
