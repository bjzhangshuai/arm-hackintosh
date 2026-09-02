set pagination off
set confirm off
set architecture aarch64

define dump_hufa
  printf "HUFA x28=0x%lx page_offset=0x%lx candidate=%u\n", $x28, $x24, $w25
  x/16wx $x28
end

break *0x115224
commands
  silent
  printf "EVENT magic-candidate\n"
  dump_hufa
  continue
end

break *0x115254
commands
  silent
  printf "EVENT magic-and-full-read-ok\n"
  dump_hufa
  continue
end

break *0x1152dc
commands
  silent
  printf "EVENT header-validation-return result=%u\n", $w0
  dump_hufa
  continue
end

break *0x1152a8
commands
  silent
  printf "EVENT header-digest-computed\n"
  printf "computed digest at sp+0x48:\n"
  x/8wx $sp+0x48
  printf "stored digest at header+0x20:\n"
  x/8wx $x28+0x20
  continue
end

break *0x1152e0
commands
  silent
  printf "EVENT header-validation-rejected result=%u\n", $w0
  dump_hufa
  detach
  quit
end

break *0x1153e8
commands
  silent
  printf "EVENT header-accepted\n"
  dump_hufa
  detach
  quit
end

target remote 127.0.0.1:12345
continue
