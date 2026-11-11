"""Synthetic BC1/BC3 DDS block and texture budget regressions."""
import struct
import tempfile
import unittest
from pathlib import Path

from pocketport.skyrim.texture_gpu import decode_rgba, convert_t3x
from pocketport.skyrim.dds import DDSError


def dds(fmt: bytes, block: bytes, width=4, height=4):
    h = bytearray(128)
    h[:4] = b"DDS "
    struct.pack_into("<I", h, 4, 124)
    struct.pack_into("<II", h, 12, height, width)
    struct.pack_into("<I", h, 76, 32)
    h[84:88] = fmt
    return bytes(h) + block


class TextureTests(unittest.TestCase):
    def test_bc1_red_opaque(self):
        block=struct.pack("<HHI",0xf800,0x001f,0)
        w,h,raw=decode_rgba(dds(b"DXT1",block))
        self.assertEqual((w,h),(4,4))
        self.assertEqual(raw[:4],bytes([255,0,0,255]))
        self.assertEqual(raw[-4:],bytes([255,0,0,255]))

    def test_bc1_alpha_transparency(self):
        block=struct.pack("<HHI",0x001f,0xf800,0xffffffff)
        w,h,raw=decode_rgba(dds(b"DXT1",block))
        self.assertEqual(raw[3],0)

    def test_bc3_8_alpha_palette(self):
        alpha=bytes([220,20])+bytes(6)
        color=struct.pack("<HHI",0xf800,0x001f,0)
        w,h,raw=decode_rgba(dds(b"DXT5",alpha+color))
        self.assertEqual((w,h),(4,4))
        self.assertEqual(raw[:4],bytes([255,0,0,220]))

    def test_bc3_6_alpha_palette(self):
        alpha=bytes([10,200])+int(7).to_bytes(6,"little")
        color=struct.pack("<HHI",0xf800,0x001f,0)
        self.assertEqual(decode_rgba(dds(b"DXT5",alpha+color))[2][3],255)

    def test_truncation_and_format_failure(self):
        with self.assertRaises(DDSError):
            decode_rgba(dds(b"DXT5",bytes(7)))
        with self.assertRaises(DDSError):
            decode_rgba(dds(b"DX10",bytes(16)))

    def test_missing_dds_fails_without_output(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"missing.dds"
            with self.assertRaises(DDSError):
                convert_t3x(p,Path(td)/"out.t3x")
            self.assertFalse((Path(td)/"out.t3x").exists())


if __name__=="__main__":
    unittest.main()
