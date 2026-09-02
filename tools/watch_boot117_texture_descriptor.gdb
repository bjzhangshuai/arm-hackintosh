set pagination off
set confirm off
set architecture aarch64
set print thread-events off
python
import gdb
import platform
import socket
import struct

if platform.system() != 'Linux' or socket.gethostname() != 'macvm-validation':
    raise ValueError('isolated validation VM required')
gdb.execute('target remote 127.0.0.1:12353')
slide = 0x19344000
address = 0xfffffe00084f4438 + slide
read = lambda address, count: gdb.selected_inferior().read_memory(address, count).tobytes()
# Exact 25G72 allocateTextureHandle: type selected before the common addObject BL.
for at, instruction in ((0xfffffe00084f4418, 0x52800181),
                        (0xfffffe00084f4430, 0xaa1603e3),
                        (0xfffffe00084f4434, 0xaa1503e4),
                        (0xfffffe00084f4438, 0x94001b23)):
    if struct.unpack('<I', read(at + slide, 4))[0] != instruction:
        gdb.execute('detach')
        raise ValueError('texture allocation instruction contract mismatch')

class DescriptorProbe(gdb.Breakpoint):
    def __init__(self):
        super().__init__(f'*{address:#x}', gdb.BP_HARDWARE_BREAKPOINT)
        self.silent = True

    def stop(self):
        if int(gdb.parse_and_eval('$x1')) & 0xffffffff != 12:
            return False
        length = int(gdb.parse_and_eval('$x3')) & 0xffffffff
        pointer = int(gdb.parse_and_eval('$x4')) & ((1 << 64) - 1)
        ref = int(gdb.parse_and_eval('$x2')) & 0xffffffff
        if not 12 <= length <= 4096 or pointer < 0xfffffe0000000000:
            gdb.write(f'PVG_DESCRIPTOR_ERROR unsafe length/pointer length={length} pointer={pointer:#x} ref={ref}\n')
            return True
        gdb.write(f'PVG_TYPE12 ref={ref} length={length} pointer={pointer:#x} bytes={read(pointer, length).hex()}\n')
        return True

probe = DescriptorProbe()
gdb.write('PVG_TYPE12_WATCH_ARMED observe_only=1\n')
end
continue
delete breakpoints
detach
quit
