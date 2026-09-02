set pagination off
set confirm off
set architecture aarch64

# macOS 26.6 (25G72) VirtualMac2,1 iBEC descriptor probe.  Run only in the
# disposable Linux validation VM.  This is a diagnostic shim, not a production
# bypass: it leaves IMG4/iBSS/LocalPolicy/iBEC validation intact, relocates iBEC
# through the observed final callback, and only injects a minimal in-memory
# descriptor when iBEC's selector lookup returns NULL for the early restore
# root object.  The goal is to prove whether the next blocker is the missing
# restore object graph before implementing it in QEMU/restore-provider code.
set $relocate_ibec_for_final_callback = 1
set $trace_relocated_ibec_halt = 1
set $trace_relocated_ibec_exceptions = 1
set $trace_relocated_ibec_init_failure = 1
set $trace_relocated_ibec_context_return = 1
set $inject_synthetic_root_descriptor = 1

source /home/macvm/src/macvm/tools/trace_ibss_lpol_then_ibec_inject.gdb
