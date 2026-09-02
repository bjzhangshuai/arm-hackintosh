set pagination off
set confirm off
set architecture aarch64

# Generic one-shot register snapshot for the disposable validation VM's QEMU
# gdbstub.  Use only after QEMU is already running with
# -gdb tcp:127.0.0.1:12345.
target remote 127.0.0.1:12345
printf "SNAPSHOT pc=0x%lx sp=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x30=0x%lx cpsr=0x%lx\n", $pc, $sp, $x0, $x1, $x2, $x3, $x4, $x30, $cpsr
x/24i $pc
info registers x0 x1 x2 x3 x4 x5 x6 x7 x8 x9 x10 x11 x12 x13 x14 x15 x16 x17 x18 x19 x20 x21 x22 x23 x24 x25 x26 x27 x28 x29 x30 sp pc cpsr
detach
quit
