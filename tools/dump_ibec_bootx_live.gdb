set pagination off
set confirm off
set architecture aarch64

# Attach after the bootstrap GDB has already loaded iBSS/LocalPolicy/iBEC and
# Stage2 has reached the recovery prompt.  The restore helper then drives the
# normal TrustCache -> RamDisk -> DeviceTree -> KernelCache -> bootx sequence.
# This script dumps the live iBEC text window at the first bootx MMIO probe so
# later analysis can scan the actual executed bytes rather than a stale offline
# copy.  Do not dump the full 0x70000000..0x70130000 span: the relocated image
# has unreadable holes before the executable iBEC window, and GDB aborts the
# command file on the first inaccessible byte.
set $dumped_ibec_bootx_live = 0

define dump_ibec_bootx_live_once
  if $dumped_ibec_bootx_live == 0
    set $dumped_ibec_bootx_live = 1
    dump binary memory /tmp/macvm-ibec-bootx-live.bin 0x7006c000 0x70130000
    printf "IBEC_BOOTX_LIVE_DUMP path=/tmp/macvm-ibec-bootx-live.bin base=0x7006c000 end=0x70130000\n"
  end
end

target remote 127.0.0.1:12345

# Known bootx probe that reads 0x30240040.
break *0x70085834
commands
  silent
  printf "IBEC_BOOTX_MMIO_PROBE_30240040 pc=0x%lx x8=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x8, $sp, $x30
  x/32i $pc
  dump_ibec_bootx_live_once
  continue
end

# Known bootx/CTRR probe that reads 0x30260000.
break *0x7008450c
commands
  silent
  printf "IBEC_BOOTX_MMIO_PROBE_30260000_BLOCK pc=0x%lx x8=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x8, $sp, $x30
  x/32i $pc
  dump_ibec_bootx_live_once
  continue
end

# Preserve exception evidence if the boot path reaches a new unmapped MMIO.
break *0x700cc818
commands
  silent
  set $post_ibec_esr = $x8
  set $post_ibec_far = $x9
  set $post_ibec_elr = *(unsigned long long *)($x19 + 240)
  set $post_ibec_ec = ($post_ibec_esr >> 26) & 0x3f
  set $post_ibec_il = ($post_ibec_esr >> 25) & 0x1
  set $post_ibec_iss = $post_ibec_esr & 0x1ffffff
  printf "IBEC_BOOTX_EXCEPTION_ESR_FAR pc=0x%lx frame=0x%lx esr=0x%lx ec=0x%lx il=%lu iss=0x%lx far=0x%lx saved_elr=0x%lx sp=0x%lx x30=0x%lx cpsr=0x%lx\n", $pc, $x19, $post_ibec_esr, $post_ibec_ec, $post_ibec_il, $post_ibec_iss, $post_ibec_far, $post_ibec_elr, $sp, $x30, $cpsr
  if $post_ibec_elr >= 0x7006c000 && $post_ibec_elr < 0x70130000
    x/32i $post_ibec_elr
  end
  dump_ibec_bootx_live_once
  continue
end

continue
