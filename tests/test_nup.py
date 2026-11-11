"""Original synthetic NUPs: no copyrighted content, no GPL code."""
import hashlib
import struct
import tempfile
import unittest
from pathlib import Path
from pocketport.nup import NupError, inspect_nup
from pocketport.inventory import classify
from pocketport.planning import choose


def fixture(*, bad_hash=False):
    pkg = struct.pack('<QIIIIBBHIQI20s', 0x400486024dec000, 0, 0xffffffff, 0xffffffff,
                      131072, 0, 0, 0, 0, 0, 0, b'\0'*20)
    directory = b'\0' * 24
    pool = b''
    toc = struct.pack('<4sIQQQQQ', b'TOC\x01', 1, 1, 0, 48+64+24, len(pool), 0) + pkg + directory
    digest = bytearray(hashlib.sha256(toc).digest())
    if bad_hash: digest[0] ^= 1
    blob_offset = (128 + len(toc) + 15) & ~15
    header = struct.pack('<4sHHQQ32sQQII16s32s', b'NUP\x01',128,1,128,len(toc),bytes(digest),
                         blob_offset,blob_offset,1,0,b'\0'*16,b'\0'*32)
    return header + toc + b'\0'*(blob_offset-128-len(toc))


class NupTests(unittest.TestCase):
    def test_valid_synthetic_index(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'example.nup';p.write_bytes(fixture())
            result=inspect_nup(p)
            self.assertEqual(result['package_count'],1)
            self.assertTrue(result['toc_verified'])
            self.assertEqual(result['packages'][0]['version'],131072)
            self.assertEqual(classify(p),'nup-v1-unverified')

    def test_invalid_digest_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.nup';p.write_bytes(fixture(bad_hash=True))
            with self.assertRaisesRegex(NupError,'SHA-256'):inspect_nup(p)

    def test_mismatched_length_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'short.nup';p.write_bytes(fixture()[:-1])
            with self.assertRaises(NupError):inspect_nup(p)

    def test_runtime_route(self):
        result = choose({"runtime_available": True}, "new3ds")
        self.assertEqual(result["route"], "runtime-rehost")

    def test_fake_extension_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fake.nup';p.write_bytes(b'not a nup')
            with self.assertRaises(NupError):inspect_nup(p)


if __name__ == '__main__':unittest.main()
