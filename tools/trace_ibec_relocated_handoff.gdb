set pagination off
set confirm off
set architecture aarch64

# macOS 26.6 (25G72) VirtualMac2,1 restore handoff probe.  Run only in the
# disposable Linux validation VM.  It preserves the signed iBSS -> LPOL -> iBEC
# validation path, then relocates the already-decompressed iBEC image to its
# own preferred low base immediately before the final handoff callback.  This
# tests whether the callback's MMU-off `ret` must receive the low entry address.
set $relocate_ibec_for_final_callback = 1

source /home/macvm/src/macvm/tools/trace_ibss_lpol_then_ibec_inject.gdb
