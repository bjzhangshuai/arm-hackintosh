set pagination off
set confirm off
set architecture aarch64

# Attach after iBEC has entered the Stage2 recovery prompt.  This follows the
# SVC #7 trampoline into the macOS kernel and advances to the first early XNU
# HVC call at 0x76f5c33c.  It executes exactly that HVC and, if control reaches
# the following CBNZ, executes that branch too so a nonzero-return spin is
# reported explicitly.  It is diagnostic-only: no registers or guest memory are
# patched.

set $kernel_hvc_trampoline = 0
set $kernel_hvc_entry = 0
set $kernel_hvc_boot_args = 0
set $kernel_hvc_ret = 0

target remote 127.0.0.1:12345

break *0x70087c8c
commands
  silent
  set $kernel_hvc_trampoline = $x24
  set $kernel_hvc_entry = $x0
  set $kernel_hvc_boot_args = $x1
  printf "IBEC_BOOTX_KERNEL_HVC_CALLBACK_CALL pc=0x%lx trampoline=0x%lx entry=0x%lx boot_args=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx sp=0x%lx x30=0x%lx cpsr=0x%lx\n", $pc, $kernel_hvc_trampoline, $kernel_hvc_entry, $kernel_hvc_boot_args, $x2, $x3, $x4, $sp, $x30, $cpsr
  if $kernel_hvc_trampoline >= 0x70000000 && $kernel_hvc_trampoline < 0xd0000000
    set $kernel_hvc_ret = $kernel_hvc_trampoline + 0x2b8
    advance *$kernel_hvc_ret
    si
    si
    printf "IBEC_BOOTX_KERNEL_HVC_BRANCH_TARGET pc=0x%lx entry=0x%lx boot_args=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx sp=0x%lx x30=0x%lx cpsr=0x%lx\n", $pc, $kernel_hvc_entry, $kernel_hvc_boot_args, $x0, $x1, $x2, $sp, $x30, $cpsr
    advance *0x76f5c104
    printf "IBEC_BOOTX_KERNEL_HVC_ZERO_TABLE_DONE pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x20=0x%lx x22=0x%lx x23=0x%lx x24=0x%lx x25=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x20, $x22, $x23, $x24, $x25, $sp, $cpsr
    advance *0x76f5c13c
    printf "IBEC_BOOTX_KERNEL_HVC_ASLR_DONE pc=0x%lx x0=0x%lx x18=0x%lx x22=0x%lx x23=0x%lx x24=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x18, $x22, $x23, $x24, $sp, $cpsr
    advance *0x76f5c1f4
    printf "IBEC_BOOTX_KERNEL_HVC_MAP1_DONE pc=0x%lx x0=0x%lx x2=0x%lx x4=0x%lx x5=0x%lx x6=0x%lx x10=0x%lx x14=0x%lx x15=0x%lx x24=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x2, $x4, $x5, $x6, $x10, $x14, $x15, $x24, $sp, $cpsr
    advance *0x76f5c33c
    printf "IBEC_BOOTX_KERNEL_HVC_BEFORE pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x30=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x30, $sp, $cpsr
    x/16i $pc
    si
    printf "IBEC_BOOTX_KERNEL_HVC_AFTER pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x30=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x30, $sp, $cpsr
    if $pc >= 0x70000000 && $pc < 0xffffffffffffffff
      x/32i $pc
    end
    if $pc == 0x76f5c340
      si
      printf "IBEC_BOOTX_KERNEL_HVC_AFTER_CBNZ pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x30=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x30, $sp, $cpsr
      if $pc == 0x76f5c340
        printf "IBEC_BOOTX_KERNEL_HVC_NONZERO_RETURN_SPIN pc=0x%lx x0=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $sp, $cpsr
      end
    end
  end
  detach
  quit
end

continue
