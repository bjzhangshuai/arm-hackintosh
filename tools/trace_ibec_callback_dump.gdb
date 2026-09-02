set pagination off
set confirm off
set architecture aarch64

# macOS 26.6 (25G72) VirtualMac2,1 restore callback dumper.  Run only in the
# disposable Linux validation VM.  This follows the same signed iBSS -> LPOL ->
# iBEC validation path as trace_ibss_lpol_then_ibec_inject.gdb, but stops at the
# final stage-handoff callback and dumps the RAM trampoline so QEMU-side
# behavior can be implemented from the actual code path instead of guessed.
set $dump_final_callback = 1
set $stop_at_final_callback = 1

source /home/macvm/src/macvm/tools/trace_ibss_lpol_then_ibec_inject.gdb
