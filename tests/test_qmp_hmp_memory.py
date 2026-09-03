import unittest

from tools.qmp_hmp_memory import HMPMemory, decode_words


class HMPMemoryTests(unittest.TestCase):
    def test_words_little_endian_and_crlf(self):
        self.assertEqual(decode_words('70000000: 0x0807060504030201\r\n70000008: 0x0000000000000000\r\n', 0x70000000, 2), bytes(range(1, 9)) + bytes(8))

    def test_refuse_bad_extent_address_and_errors(self):
        for reply in ('70000008: 0x0000000000000000',
                      '70000000: 0x0000000000000000 0x0000000000000000',
                      '70000000: Cannot access memory', '',
                      '70000000: 0x0000', 'bad text'):
            with self.subTest(reply=reply), self.assertRaises(ValueError):
                decode_words(reply, 0x70000000, 1)

    def test_physical_mmio_and_overrun_refused_before_command(self):
        m = HMPMemory(None)
        for address, size in ((0x30201014, 4), (0x30201018, 4), (0x470000000, 1),
                              (0x46FFFFFFF, 2), (0x70000000, 4097), (0x70000000, 0)):
            with self.subTest(address=address, size=size), self.assertRaises(ValueError):
                m.physical(address, size)

    def test_kernel_range_and_budget_refuse_before_command(self):
        with self.assertRaises(ValueError):
            HMPMemory(None).read(0x70000000, 8)
        with self.assertRaises(ValueError):
            HMPMemory(None, budget=7).read(0xFFFFFE0000000000, 8)

    def test_unaligned_slice_only_uses_read_command(self):
        class Client:
            def execute(self, name, arguments):
                self.call = name, arguments
                return '70000000: 0x0807060504030201'
        c = Client()
        self.assertEqual(HMPMemory(c).physical(0x70000002, 3), bytes((3, 4, 5)))
        self.assertEqual(c.call, ('human-monitor-command', {'command-line': 'xp/1gx 0x70000000'}))


if __name__ == '__main__':
    unittest.main()
