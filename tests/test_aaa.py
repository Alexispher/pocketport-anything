"""AAA synthetic file signatures; no copyrighted game assets."""
import struct
import tempfile
import unittest
from pathlib import Path
from pocketport.aaa import detect_engine, inspect_executable, research_game, compatibility

class AAATests(unittest.TestCase):
    def test_unity_multiple_clues(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/"UnityPlayer.dll").write_bytes(b"x")
            self.assertEqual(detect_engine(p)["engine"],"unknown")
            (p/"GameAssembly.dll").write_bytes(b"x")
            self.assertEqual(detect_engine(p)["engine"],"Unity IL2CPP")

    def test_unreal_containers(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"Content"/"Paks"
            p.mkdir(parents=True)
            (p/"a.utoc").write_bytes(b"x")
            (p/"a.ucas").write_bytes(b"x")
            self.assertEqual(detect_engine(Path(d))["engine"],"Unreal Engine 4/5")

    def test_extensions_are_not_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/"a.txd").write_bytes(b"x")
            (Path(d)/"b.img").write_bytes(b"x")
            self.assertEqual(detect_engine(Path(d))["engine"],"unknown")

    def test_renderware_headers(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/"a.txd").write_bytes(struct.pack("<III",22,0,0))
            (Path(d)/"b.img").write_bytes(b"VER2"+bytes(16))
            self.assertEqual(detect_engine(Path(d))["engine"],"RenderWare-era GTA candidate")

    def test_elf_arm64(self):
        data=bytearray(64)
        data[:6]=b"\x7fELF\x02\x01"
        struct.pack_into("<H",data,18,183)
        struct.pack_into("<Q",data,24,0x1234)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"x.elf"
            p.write_bytes(data)
            info=inspect_executable(p)
            self.assertEqual(info["architecture"],"ARM64")
            self.assertEqual(info["entry_address"],0x1234)

    def test_pe_x64(self):
        data=bytearray(512)
        data[:2]=b"MZ"
        struct.pack_into("<I",data,0x3c,0x80)
        data[0x80:0x84]=b"PE\0\0"
        struct.pack_into("<HH",data,0x84,0x8664,3)
        struct.pack_into("<H",data,0x94,240)
        struct.pack_into("<H",data,0x98,0x20b)
        struct.pack_into("<I",data,0xa8,0x1000)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"x.exe"
            p.write_bytes(data)
            self.assertEqual(inspect_executable(p)["architecture"],"x86-64")

    def test_false_pe_not_verified(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"f.exe"
            p.write_bytes(b"MZ"+bytes(128))
            self.assertNotEqual(inspect_executable(p)["format"],"PE")

    def test_catalogue_and_unknown(self):
        self.assertEqual(research_game("GTA SA")["game"],"Grand Theft Auto: San Andreas")
        self.assertEqual(research_game("GTA SA")["status"],"research-only")
        self.assertEqual(research_game("Unknown game 123")["status"],"unknown")

    def test_disk_is_not_ram(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/"asset").write_bytes(b"abc")
            r=compatibility(Path(d))
            self.assertEqual(r["on_disk_bytes"],3)
            self.assertIsNone(r["application_memory_bytes"])
            self.assertEqual(r["feasibility"],"unverified")

    def test_symlink_and_limit(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"a"
            p.write_bytes(b"x")
            (Path(d)/"link").symlink_to(p)
            self.assertEqual(detect_engine(Path(d))["skipped"],1)
            with self.assertRaises(ValueError):
                detect_engine(Path(d),max_files=0)

if __name__=="__main__":
    unittest.main()
