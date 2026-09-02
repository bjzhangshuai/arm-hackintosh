set pagination off
set confirm off
set architecture aarch64

# Lightweight AVPBooter/iBSS mode probe.  Run only in the disposable Linux
# validation VM after starting QEMU with -S -gdb tcp:127.0.0.1:12345.
# It identifies whether a given AuxiliaryStorage image reaches the known
# AVPBooter receive point and whether the injected signed iBSS reaches the
# remote-boot handoff point used by the full restore-chain trace.
set $payload_addr = 0x7006c000
set $payload_size = 320862

break *0x10de90
commands
  silent
  printf "PROBE_IBSS_RECEIVE_ENTRY dest=0x%lx max=%u return=0x%lx\n", $x0, $w4, $x30
  restore /home/macvm/macos-restore/26.6/restore-chain/iBSS.fixed-rnd-713471fb.img4 binary $payload_addr
  set $x0 = $payload_size
  set $pc = 0x1007a8
  printf "PROBE_IBSS_INJECTED addr=0x%lx size=%u\n", $payload_addr, $payload_size
  continue
end

break *0x1008d8
commands
  silent
  printf "PROBE_IBSS_VERIFY_RETURN result=0x%x descriptor=0x%lx mode=%u\n", $w0, $x19, $w23
  if $w0 != 0
    detach
    quit
  end
  if $w23 != 6
    printf "PROBE_NON_REMOTE_VERIFY_MODE mode=%u\n", $w23
    detach
    quit
  end
  continue
end

break *0x105c94
commands
  silent
  printf "PROBE_IBSS_HANDOFF_ENTRY arg0=0x%lx image=0x%lx arg2=0x%lx\n", $x0, $x1, $x2
  continue
end

break *0x7006e2cc
commands
  silent
  printf "PROBE_IBSS_REMOTE_BOOT_ABORT_READY pc=0x%lx sp=0x%lx\n", $pc, $sp
  detach
  quit
end

break *0x7007be9c
commands
  silent
  printf "PROBE_IBOOT_PANIC line=%u arg0=0x%lx caller=0x%lx pc=0x%lx\n", $w1, $x0, $x30, $pc
  detach
  quit
end

target remote 127.0.0.1:12345
continue
