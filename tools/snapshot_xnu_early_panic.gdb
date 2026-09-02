set pagination off
set confirm off
set architecture aarch64

# Read-only snapshot for the macOS 26 early-XNU terminal spin observed after
# natural execution.  It records the suspected panic/debugger argument, the
# surrounding code, stack words, and a bounded frame-pointer chain.  PAC bits
# in saved link registers are preserved and a canonical high-VA view is also
# printed; neither guest registers nor guest memory are changed.

target remote 127.0.0.1:12345

printf "XNU_EARLY_PANIC_SELECTED pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x8=0x%lx x16=0x%lx x17=0x%lx x29=0x%lx x30=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x8, $x16, $x17, $x29, $x30, $sp, $cpsr
printf "XNU_EARLY_PANIC_ARGUMENT_X2\n"
x/s $x2
x/96bx $x2
printf "XNU_EARLY_PANIC_SPIN_DISASM\n"
x/160i $pc-0x180
printf "XNU_EARLY_PANIC_CALLER_DISASM\n"
x/192i $x30-0x180
printf "XNU_EARLY_PANIC_BACKTRACE\n"
bt
printf "XNU_EARLY_PANIC_STACK\n"
x/96gx $sp
printf "XNU_EARLY_PANIC_FRAME_POINTERS\n"
set $panic_fp = $x29
set $panic_frame_index = 0
while $panic_frame_index < 8 && $panic_fp >= 0xffff000000000000
  set $panic_next_fp = *(unsigned long long *)$panic_fp
  set $panic_saved_lr = *(unsigned long long *)($panic_fp + 8)
  set $panic_canonical_lr = 0xffff000000000000 | ($panic_saved_lr & 0x0000ffffffffffff)
  printf "XNU_EARLY_PANIC_FRAME index=%u fp=0x%lx next_fp=0x%lx saved_lr=0x%lx canonical_lr=0x%lx\n", $panic_frame_index, $panic_fp, $panic_next_fp, $panic_saved_lr, $panic_canonical_lr
  set $panic_fp = $panic_next_fp
  set $panic_frame_index = $panic_frame_index + 1
end
detach
quit
