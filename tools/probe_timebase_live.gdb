set pagination off
set confirm off
set architecture aarch64
python
import os, sys, struct
import gdb
sys.path.insert(0, '/home/macvm/src/macvm/tools')
from apple_device_tree import parse_device_tree
port = int(os.environ.get('MACVM_GDB_PORT', '12351'))
if not 1024 <= port <= 65535:
    raise ValueError('invalid port')
gdb.execute(f'target remote 127.0.0.1:{port}')
slide = 0x19344000
inferior = gdb.selected_inferior()
for cpu in inferior.threads():
    cpu.switch()
    try:
        instruction = struct.unpack('<I', inferior.read_memory(0xfffffe000a4f66a4 + slide, 4).tobytes())[0]
        if instruction == 0xf9439508:
            break
    except gdb.MemoryError:
        pass
else:
    raise ValueError('no vCPU maps the reviewed 25G72 PE callback')
frequency = struct.unpack('<Q', inferior.read_memory(0xfffffe000a993728 + slide, 8).tobytes())[0]
gdb.write(f'MACVM_XNU_PLATFORM_TIMEBASE_HZ={frequency}\n')
for name in ('CNTFRQ_EL0', 'CNTVCT_EL0', 'CNTPCT_EL0', 'CNTV_CTL_EL0', 'CNTV_CVAL_EL0'):
    try:
        gdb.write(f'MACVM_TIMER_REGISTER {name}={int(gdb.parse_and_eval("$" + name))}\n')
    except Exception as error:
        gdb.write(f'MACVM_TIMER_REGISTER_UNAVAILABLE {name} {error}\n')
address = int(os.environ['MACVM_DT_PHYSICAL'], 0)
size = int(os.environ['MACVM_DT_SIZE'], 0)
if not 0x70000000 <= address < 0x80000000 or not 4096 <= size <= 1048576:
    raise ValueError('invalid DT range')
reply = gdb.execute('maintenance packet Qqemu.PhyMemMode:1', to_string=True)
if 'received: "OK"' not in reply:
    raise ValueError('physical mode refused')
try:
    data = gdb.selected_inferior().read_memory(address, size).tobytes()
finally:
    gdb.execute('maintenance packet Qqemu.PhyMemMode:0', to_string=True)
tree = parse_device_tree(data, allow_zero_padding=True)
def visit(node, parent):
    path = parent + '/' + node.name
    for prop in node.properties:
        if any(token in prop.name for token in ('timebase', 'clock-frequency', 'bus-frequency')) and len(prop.value) <= 32:
            gdb.write(f'MACVM_TIMEBASE_DT {path}/{prop.name} raw={prop.value.hex()} le={int.from_bytes(prop.value, "little")}\n')
    for child in node.children:
        visit(child, path)
visit(tree, '')
end
detach
quit
