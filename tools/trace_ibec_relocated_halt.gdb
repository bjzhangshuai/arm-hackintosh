set pagination off
set confirm off
set architecture aarch64

# macOS 26.6 (25G72) VirtualMac2,1 iBEC early-halt probe.  Run only in the
# disposable Linux validation VM.  It uses the signed restore chain, relocates
# iBEC immediately before the final callback, then installs iBEC-local
# breakpoints after the low-base image is in memory.  The exception probe
# breaks after iBEC has copied ESR/FAR/ELR into general-purpose registers, so
# it does not rely on GDB knowing Apple/QEMU system-register names.
set $relocate_ibec_for_final_callback = 1
set $trace_relocated_ibec_halt = 1
set $trace_relocated_ibec_exceptions = 1
set $trace_relocated_ibec_init_failure = 1
set $trace_relocated_ibec_context_return = 1

source /home/macvm/src/macvm/tools/trace_ibss_lpol_then_ibec_inject.gdb
