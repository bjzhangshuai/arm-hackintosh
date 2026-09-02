import struct
import unittest

from tools.arm64_user_memory import TranslationError, UserMemory16K, frame_chain


class UserMemoryTests(unittest.TestCase):
    def setUp(self):
        self.slots = {0x4000: 0x8003, 0x8000 + 11 * 8: 0xC003,
                      0xC000 + 7 * 8: 0x20003, 0xC000 + 8 * 8: 0x30003}
        self.calls = []
        self.va = (11 << 25) | (7 << 14)

        def read(address, size):
            self.calls.append((address, size))
            if address in self.slots and size == 8:
                return struct.pack("<Q", self.slots[address])
            return bytes([address >> 16 & 255]) * size

        self.memory = UserMemory16K(read, 0x4000)

    def test_page_translation_and_cache(self):
        self.assertEqual(self.memory.translate(self.va + 9), 0x20009)
        self.assertEqual(self.memory.translate(self.va + 23), 0x20017)
        self.assertEqual(len(self.calls), 3)

    def test_cross_page(self):
        self.assertEqual(self.memory.read(self.va + 0x3FFC, 8), b'\x02' * 4 + b'\x03' * 4)

    def test_level2_block(self):
        self.slots[0x8000 + 11 * 8] = 0x4000001
        self.assertEqual(self.memory.translate(self.va + 9), 0x4000000 + (7 << 14) + 9)

    def test_invalid_descriptors_fail_closed(self):
        for entry in (0, 1, 2, 3):
            with self.subTest(entry=entry):
                self.slots[0x4000] = entry
                self.memory.entries.clear()
                with self.assertRaises(TranslationError):
                    self.memory.translate(self.va)

    def test_invalid_regime_and_addresses(self):
        for root in (0, -1, 0x4001, 1 << 48):
            with self.assertRaises(TranslationError):
                UserMemory16K(lambda a, n: b'', root)
        with self.assertRaises(TranslationError):
            UserMemory16K(lambda a, n: b'', 0x4000, va_bits=39)
        for address in (-1, 1 << 47, 0xFFFF000000000001):
            with self.assertRaises(TranslationError):
                self.memory.translate(address)
        for address, size in ((0, -1), (0, 65537), ((1 << 47) - 2, 4)):
            with self.assertRaises(TranslationError):
                self.memory.read(address, size)

    def test_short_read_rejected(self):
        self.memory.translate(self.va)
        self.memory.read_physical = lambda a, n: b''
        with self.assertRaises(TranslationError):
            self.memory.read(self.va, 8)

    def test_frame_unwind_pac_and_loop_guard(self):
        class Memory:
            va_bits = 47
            def read(self, address, size):
                return struct.pack('<QQ', address + 32 if address == 0x1000 else address,
                                   0xBCFA000184E665A4)
        self.assertEqual(frame_chain(Memory(), 0x1000),
                         [(0x1000, 0x184E665A4), (0x1020, 0x184E665A4)])
        self.assertEqual(frame_chain(Memory(), 0x1001), [])
        self.assertEqual(len(frame_chain(Memory(), 0x1000, max_frames=1)), 1)
        with self.assertRaises(ValueError):
            frame_chain(Memory(), 0x1000, max_frames=0)
