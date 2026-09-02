set pagination off
set confirm off
set architecture aarch64

# Attach to a naturally running post-boot XNU instance, record all virtual
# CPU program counters plus the selected CPU state, then detach.  This script
# must remain read-only so the snapshot describes the state QEMU actually
# reached without debugger single-stepping or guest mutation.

target remote 127.0.0.1:12345

printf "XNU_NATURAL_SNAPSHOT_SELECTED pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x8=0x%lx x16=0x%lx x17=0x%lx x29=0x%lx x30=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x8, $x16, $x17, $x29, $x30, $sp, $cpsr
printf "XNU_NATURAL_SNAPSHOT_THREADS\n"
info threads
thread apply all p/x $pc
printf "XNU_NATURAL_SNAPSHOT_DISASM\n"
x/96i $pc
detach
quit
