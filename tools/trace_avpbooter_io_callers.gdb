set pagination off
set confirm off
set architecture aarch64
set $io_count = 0

break *0x10c8e0
commands
  silent
  set $io_count = $io_count + 1
  set $caller_lr = *(unsigned long long *)($sp + 56)
  set $caller_fp = *(unsigned long long *)$x29
  set $grand_lr = *(unsigned long long *)($caller_fp + 8)
  set $grand_fp = *(unsigned long long *)$caller_fp
  set $great_lr = *(unsigned long long *)($grand_fp + 8)
  printf "IO_CALL %u caller_lr=0x%lx grand_lr=0x%lx great_lr=0x%lx sp=0x%lx\n", $io_count, $caller_lr, $grand_lr, $great_lr, $sp
  if $io_count == 36
    detach
    quit
  end
  continue
end

target remote 127.0.0.1:12345
continue
