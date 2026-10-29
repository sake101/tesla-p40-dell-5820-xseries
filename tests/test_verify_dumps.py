import struct
import sys
import unittest
from pathlib import Path
import zlib
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from verify_dumps import NAME, GUID, compare, parse_save

def record(data=None, name=None, guid=GUID, attrs=7):
    if data is None:
        data = bytearray(115)
        data[6:10] = bytes([1, 2, 0, 1])
    name = (NAME + '\0').encode('utf-16-le') if name is None else name
    body = struct.pack('<II', len(name), len(data)) + name + guid + struct.pack('<I', attrs) + data
    return body + struct.pack('<I', zlib.crc32(body) & 0xffffffff)

class VerifyTests(unittest.TestCase):
    def setUp(self):
        self.before = record()
        self.data = bytearray(parse_save(self.before))
        self.data[4] = 3
        self.after = record(self.data)

    def test_one_byte_and_reboot(self):
        result = compare(self.before, self.after, self.after)
        self.assertEqual(result['changed_offsets'], [4])
        self.assertTrue(result['post_reboot_matches'])

    def test_record_corruption_and_bounds(self):
        damaged = bytearray(self.before); damaged[-1] ^= 1
        for blob in (b'', self.before[:7], self.before[:-1], self.before + b'x', bytes(damaged)):
            with self.subTest(length=len(blob)), self.assertRaises(ValueError): parse_save(blob)

    def test_identity_and_layout(self):
        data = bytearray(self.data); data[7] = 0
        for blob in (record(name=b'x' * 42), record(guid=b'\0' * 16), record(attrs=3), record(data), record(b'\0' * 114)):
            with self.subTest(blob=blob[:8]), self.assertRaises(ValueError): parse_save(blob)

    def test_reject_other_writes(self):
        for index in (0, 5, 100):
            data = bytearray(self.data); data[index] ^= 1
            with self.subTest(index=index), self.assertRaises(ValueError): compare(self.before, record(data))

    def test_reject_missing_write_or_wrong_value(self):
        for value in (0, 1, 2, 4, 5):
            data = bytearray(self.data); data[4] = value
            with self.subTest(value=value), self.assertRaises(ValueError): compare(self.before, record(data))

    def test_reject_stale_or_nonmatching_readback(self):
        with self.assertRaises(ValueError): compare(self.before, self.after, self.before)
        with self.assertRaises(ValueError): compare(self.after, self.after)

if __name__ == '__main__':
    unittest.main()
