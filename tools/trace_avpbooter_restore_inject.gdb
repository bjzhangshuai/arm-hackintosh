set pagination off
set confirm off
set architecture aarch64

# macOS 26.6 (25G72) VirtualMac2,1 restore probe.  Run only in the
# disposable Linux validation VM after starting QEMU with
# -M vmapple,rnd=0x713471fb -S -gdb tcp:127.0.0.1:12345.  The payload and
# matching TSS ticket are deliberately kept outside the repo.
set $payload_addr = 0x7006c000
set $payload_size = 320862
set $error_count = 0

break *0x10de90
commands
  silent
  printf "IBSS_RECEIVE_ENTRY dest=0x%lx max=%u return=0x%lx\n", $x0, $w4, $x30
  restore /home/macvm/macos-restore/26.6/restore-chain/iBSS.fixed-rnd-713471fb.img4 binary 0x7006c000
  set $x0 = $payload_size
  set $pc = 0x1007a8
  printf "IBSS_INJECTED addr=0x%lx size=%u\n", $payload_addr, $payload_size
  continue
end

break *0x102b0c
commands
  silent
  printf "BNCH_PARSE_START tag=0x%lx manifest=0x%lx state=0x%lx\n", $x8, $x23, $x27
  x/8gx $x23
  continue
end

break *0x102b30
commands
  silent
  printf "BNCH_PARSE_RETURN result=%u ptr=0x%lx len=%lu\n", $w0, *(unsigned long long *)($sp+48), *(unsigned long long *)($sp+56)
  continue
end

break *0x102b40
commands
  silent
  printf "BNCH_PARSE_OK ptr=0x%lx len=%lu\n", *(unsigned long long *)($sp+48), *(unsigned long long *)($sp+56)
  continue
end

break *0x102850
commands
  silent
  printf "BNCH_COMPARE mode=%u tag=0x%x manifest=0x%lx expected=0x%lx expected_end=0x%lx current=0x%lx\n", $w0, $w1, $x2, $x6, $x7, $x20
  x/8gx $x6
  x/48bx $x6
  continue
end

break *0x116d2c
commands
  silent
  set $error_count = $error_count + 1
  printf "ERROR_CALL %u code=0x%x direct_lr=0x%lx fp=0x%lx\n", $error_count, $w0, $x30, $x29
  if $error_count == 64
    printf "ERROR_LIMIT_REACHED\n"
    detach
    quit
  end
  continue
end

break *0x1008d8
commands
  silent
  printf "IBSS_VERIFY_RETURN result=0x%x descriptor=0x%lx mode=%u\n", $w0, $x19, $w23
  info registers x0 x1 x2 x3 x4 x5 x19 x20 x21 x22 x23 x24 x25 x26 x27 x28 pc
  if $w0 != 0
    detach
    quit
  end
  continue
end

break *0x105c94
commands
  silent
  printf "IBSS_HANDOFF_ENTRY arg0=0x%lx image=0x%lx arg2=0x%lx\n", $x0, $x1, $x2
  x/16wx $x1
  x/16i $x1
  # Preserve the verified, decompressed ARM64 stage for offline analysis.  The
  # upper bound is deliberately inside guest RAM and only adds trailing bytes;
  # analysis tools can recover the Mach-O/prelinked image's true extent.
  dump binary memory /home/macvm/macos-restore/26.6/restore-chain/iBSS.runtime-7006c000-70120000.bin 0x7006c000 0x70120000
  printf "IBSS_RUNTIME_DUMP path=/home/macvm/macos-restore/26.6/restore-chain/iBSS.runtime-7006c000-70120000.bin size=737280\n"
  detach
  quit
end

target remote 127.0.0.1:12345
continue
