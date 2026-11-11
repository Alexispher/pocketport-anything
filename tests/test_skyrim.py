"""Skyrim LE synthetic data fixtures; no commercial game files."""
from __future__ import annotations
import os
import shutil
import struct
import subprocess
import tempfile
import unittest
import zlib
from pathlib import Path

from pocketport.skyrim.bsa import BSAArchive, BSAError
from pocketport.skyrim.tes5 import scan_plugin, TES5Error
from pocketport.skyrim.dds import decode_dxt1, pack_texture, DDSError
from pocketport.skyrim.scene import create_scene, read_scene, SceneError


def sub(tag: bytes, payload: bytes) -> bytes:
    return struct.pack("<4sH", tag, len(payload)) + payload


def rec(tag: bytes, form_id: int, fields: bytes, flags: int = 0) -> bytes:
    return struct.pack("<4sIIIII", tag, len(fields), flags, form_id, 0, 0) + fields


def group(label: int, gtype: int, content: bytes) -> bytes:
    return struct.pack("<4sIIIII", b"GRUP", 24 + len(content),
                       label, gtype, 0, 0) + content


def plugin_data() -> bytes:
    stat = rec(b"STAT", 0x100, sub(b"EDID", b"OriginalTestStatic\0") +
               sub(b"MODL", b"meshes\\test.nif\0"))
    cell = rec(b"CELL", 0x200, sub(b"EDID", b"TestCell\0"))
    ref = rec(b"REFR", 0x300,
              sub(b"NAME", struct.pack("<I", 0x100)) +
              sub(b"DATA", struct.pack("<6f", 1000., 20., 200., 0., 0., 0.)) +
              sub(b"XSCL", struct.pack("<f", 1.5)))
    return rec(b"TES4", 0, b"") + stat + cell + group(0x200, 6, ref)


def bsa_data(payload: bytes = b"original placeholder mesh bytes",
             compressed: bool = False) -> bytes:
    folder = b"meshes\0"
    filename = b"test.nif\0"
    if compressed:
        stored = struct.pack("<I", len(payload)) + zlib.compress(payload)
    else:
        stored = payload
    offset = 36 + 16 + 1 + len(folder) + 16 + len(filename)
    flags = 3
    packed = len(stored) | (0x40000000 if compressed else 0)
    return (struct.pack("<4s8I", b"BSA\0", 104, 36, flags, 1, 1,
                        len(folder) + 1, len(filename), 0) +
            struct.pack("<QII", 0, 1, 0) +
            bytes([len(folder)]) + folder +
            struct.pack("<QII", 0, packed, offset) +
            filename + stored)


def dds_data() -> bytes:
    header = bytearray(128)
    header[:4] = b"DDS "
    struct.pack_into("<I", header, 4, 124)
    struct.pack_into("<II", header, 12, 4, 4)
    struct.pack_into("<I", header, 76, 32)
    header[84:88] = b"DXT1"
    return bytes(header) + struct.pack("<HHI", 0xf800, 0x001f, 0)


class SkyrimParserTests(unittest.TestCase):
    def test_bsa_uncompressed_reads_member(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "test.bsa"
            p.write_bytes(bsa_data())
            a = BSAArchive(p)
            self.assertEqual(a.version, 104)
            self.assertEqual(a.names(), ["meshes/test.nif"])
            self.assertEqual(a.read_member("meshes/test.nif"),
                             b"original placeholder mesh bytes")

    def test_bsa_zlib_member(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "test.bsa"
            p.write_bytes(bsa_data(b"abc" * 8, True))
            self.assertEqual(BSAArchive(p).read_member("meshes/test.nif"), b"abc" * 8)

    def test_bsa_truncated_and_unsupported(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "test.bsa"
            p.write_bytes(bsa_data()[:-2])
            with self.assertRaises(BSAError):
                BSAArchive(p)
            data = bytearray(bsa_data())
            struct.pack_into("<I", data, 4, 105)
            p.write_bytes(data)
            with self.assertRaises(BSAError):
                BSAArchive(p)

    def test_bsa_member_size_budget(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "test.bsa"
            p.write_bytes(bsa_data(b"long enough"))
            with self.assertRaises(BSAError):
                BSAArchive(p).read_member("meshes/test.nif", max_bytes=3)

    def test_tes5_stat_cell_refr(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "test.esm"
            p.write_bytes(plugin_data())
            scan = scan_plugin(p)
            self.assertEqual(scan.scanned_records, 4)
            self.assertEqual(scan.statics[0x100].model, "meshes\\test.nif")
            self.assertEqual(scan.cells[0x200], "TestCell")
            self.assertEqual(scan.references[0].cell_id, 0x200)
            self.assertEqual(scan.references[0].scale, 1.5)

    def test_tes5_truncated_and_invalid(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "test.esm"
            p.write_bytes(plugin_data()[:-1])
            with self.assertRaises(TES5Error):
                scan_plugin(p)
            p.write_bytes(b"BAD!" + plugin_data()[4:])
            with self.assertRaises(TES5Error):
                scan_plugin(p)

    def test_tes5_record_count_limit(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "test.esm"
            p.write_bytes(plugin_data())
            with self.assertRaises(TES5Error):
                scan_plugin(p, max_records=2)

    def test_scene_python_roundtrip_and_budget(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "test.esm"
            p.write_bytes(plugin_data())
            scan = scan_plugin(p)
            payload, metadata = create_scene(scan, cell_id=0x200)
            parsed = read_scene(payload)
            self.assertEqual(parsed["count"], 1)
            self.assertEqual(parsed["instances"][0]["form_id"], 0x300)
            self.assertEqual(metadata["unresolved"], 0)
            with self.assertRaises(SceneError):
                create_scene(scan, cell_id=0x999)
            with self.assertRaises(SceneError):
                read_scene(payload[:-1])

    def test_dds_dxt1_rgb565_intermediate(self):
        width, height, rgb = decode_dxt1(dds_data())
        self.assertEqual((width,height), (4,4))
        self.assertEqual(rgb, struct.pack("<H",0xf800)*16)
        self.assertEqual(pack_texture(width,height,rgb)[:4], b"PPTR")

    def test_dds_unsupported_or_corrupt(self):
        with self.assertRaises(DDSError):
            decode_dxt1(dds_data()[:-1])
        data=bytearray(dds_data())
        data[84:88]=b"DXT5"
        with self.assertRaises(DDSError):
            decode_dxt1(bytes(data))

    def test_bsa_compression_budget_and_corruption(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "test.bsa"
            p.write_bytes(bsa_data(b"x" * 300, True))
            with self.assertRaises(BSAError):
                BSAArchive(p).read_member("meshes/test.nif", max_bytes=128)
            data = bytearray(bsa_data(b"ok" * 10, True))
            data[-1] ^= 0xff
            p.write_bytes(data)
            with self.assertRaises(BSAError):
                BSAArchive(p).read_member("meshes/test.nif")

    def test_compressed_tes5_static_record(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "compressed.esm"
            fields = sub(b"MODL", b"meshes/test.nif\0")
            encoded = struct.pack("<I", len(fields)) + zlib.compress(fields)
            p.write_bytes(rec(b"TES4", 0, b"") +
                          rec(b"STAT", 0x110, encoded, flags=0x00040000))
            self.assertIn(0x110, scan_plugin(p).statics)

    def test_scene_origin_rejects_nan(self):
        data = bytearray(struct.pack("<4sHHIfff", b"PPSC", 1, 0, 1,
                                     float("nan"), 0.0, 0.0) + bytes(40))
        with self.assertRaises(SceneError):
            read_scene(bytes(data))

    @unittest.skipUnless(shutil.which("gcc") or shutil.which("cc"),
                         "Host native C compiler unavailable")
    def test_host_compiles_and_loads_python_scene(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as d:
            tmp=Path(d)
            p=tmp/"test.esm"
            p.write_bytes(plugin_data())
            data,_=create_scene(scan_plugin(p))
            (tmp/"scene.ppsc").write_bytes(data)
            test_c=tmp/"check.c"
            test_c.write_text("""
#include <stdio.h>
#include "pp_scene.h"
int main(int argc,char **argv) {
    FILE *f; static PPScene scene;
    if(argc != 2 || !(f=fopen(argv[1],"rb"))) return 7;
    int ok=pp_scene_read(f,&scene); fclose(f);
    if(!ok || scene.count!=1 || scene.refs[0].form_id!=0x300 ||
       scene.refs[0].base_id!=0x100 || scene.refs[0].scale!=1.5f) return 3;
    if(pp_scene_nearest(&scene,0.f,0.f,0.f,10.f)!=0) return 4;
    return 0;
}""",encoding="utf-8")
            exe=tmp/"check"
            cc=shutil.which("cc") or shutil.which("gcc")
            compile=subprocess.run([cc,"-std=c99","-O2","-Wall","-Wextra",
                                    "-Werror","-I",str(repo/"runtime/skyrim"),
                                    str(test_c),str(repo/"runtime/skyrim/pp_scene.c"),
                                    "-lm","-o",str(exe)],capture_output=True,text=True)
            self.assertEqual(compile.returncode,0,compile.stderr)
            run=subprocess.run([str(exe),str(tmp/"scene.ppsc")],
                               capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            invalid=tmp/"scene-bad.ppsc"
            invalid.write_bytes(data[:-2])
            self.assertNotEqual(subprocess.run([str(exe),str(invalid)]).returncode,0)


if __name__=="__main__":
    unittest.main()
