"""Original synthetic Skyrim BSTriShape fixture and native C PPMG compatibility."""
import math
import shutil
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path

from pocketport.skyrim.nif import (
    NIFError, read_nif, encode_mesh, decode_mesh, convert_nif)


def synthetic_nif(stream=130, broken_triangle=False):
    # Single counted NiAVObject, full-float position + bitangent-X vertices.
    av = (struct.pack("<IIII", 0, 0, 0, 0)
          + struct.pack("<3f", 0.0, 0.0, 0.0)
          + struct.pack("<9f", 1,0,0, 0,1,0, 0,0,1)
          + struct.pack("<fI", 1.0, 0xffffffff))
    verts = (struct.pack("<4f", -10, -10, 0, 0)
             + struct.pack("<4f", 10, -10, 0, 0)
             + struct.pack("<4f", 0, 10, 0, 0))
    tri = struct.pack("<3H", 0, 1, 9 if broken_triangle else 2)
    desc = (1 << 44) | 4
    block = (av + bytes(16) + bytes(12)
             + struct.pack("<QHHI", desc, 1, 3, len(verts)+len(tri))
             + verts + tri)
    kind = b"BSTriShape"
    line = b"Gamebryo File Format, Version 20.2.0.7\n"
    return (line + struct.pack("<IBIII", 0x14020007, 1, 12, 1, stream)
            + bytes(3 if stream == 100 else 4)
            + struct.pack("<H", 1)
            + struct.pack("<I", len(kind)) + kind
            + struct.pack("<HI", 0, len(block))
            + struct.pack("<III", 0, 0, 0)
            + block)


class NIFGeometryTests(unittest.TestCase):
    def test_read_bethesda_130(self):
        mesh = read_nif(synthetic_nif(130))
        self.assertEqual(mesh.bethesda_version, 130)
        self.assertEqual(len(mesh.vertices), 3)
        self.assertEqual(mesh.triangles, ((0, 1, 2),))
        self.assertEqual(mesh.vertices[0][:3], (-10., -10., 0.))

    def test_read_2011_stream_100(self):
        self.assertEqual(read_nif(synthetic_nif(100)).bethesda_version, 100)

    def test_broken_index_rejected(self):
        with self.assertRaises(NIFError):
            read_nif(synthetic_nif(broken_triangle=True))

    def test_truncated_and_unsupported(self):
        with self.assertRaises(NIFError):
            read_nif(synthetic_nif()[:-1])
        data = bytearray(synthetic_nif())
        marker = data.find(struct.pack("<IBIII", 0x14020007, 1, 12, 1, 130))
        self.assertNotEqual(marker, -1)
        data[marker+13:marker+17] = struct.pack("<I", 200)
        with self.assertRaises(NIFError):
            read_nif(bytes(data))

    def test_python_roundtrip(self):
        mesh = read_nif(synthetic_nif())
        rebuilt = decode_mesh(encode_mesh(mesh))
        self.assertEqual(rebuilt.vertices, mesh.vertices)
        self.assertEqual(rebuilt.triangles, mesh.triangles)

    def test_convert_creates_private_mesh(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source, dest = root/"sample.nif", root/"mesh.ppmg"
            source.write_bytes(synthetic_nif())
            report = convert_nif(source, dest)
            self.assertEqual(report["vertices"], 3)
            self.assertEqual(decode_mesh(dest.read_bytes()).triangles[0], (0,1,2))
            with self.assertRaises(NIFError):
                convert_nif(source,dest)

    @unittest.skipUnless(shutil.which("cc") or shutil.which("gcc"),
                         "Host C compiler unavailable")
    def test_native_cpp_free_mesh_loader_and_corruption(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            mesh=encode_mesh(read_nif(synthetic_nif()))
            good, bad = root/"good.ppmg", root/"bad.ppmg"
            good.write_bytes(mesh)
            bad.write_bytes(mesh[:-1])
            program=root/"mesh_test.c"
            program.write_text("""
#include <stdio.h>
#include "pp_mesh.h"
static PPMesh mesh;
int main(int argc, char **argv) {
    if (argc != 2) return 3;
    FILE *f = fopen(argv[1], "rb");
    if (!f) return 4;
    int result = pp_mesh_read(f, &mesh);
    fclose(f);
    return result && mesh.vertex_count == 3 &&
           mesh.triangle_count == 1 &&
           mesh.triangles[0].v[2] == 2 ? 0 : 1;
}
""",encoding="utf8")
            executable=root/"mesh_test"
            cc=shutil.which("cc") or shutil.which("gcc")
            build=subprocess.run([cc,"-std=c99","-O2","-Wall","-Wextra",
                                  "-Werror","-I",str(repo/"runtime/skyrim"),
                                  str(program),str(repo/"runtime/skyrim/pp_mesh.c"),
                                  "-lm","-o",str(executable)],capture_output=True,text=True)
            self.assertEqual(build.returncode,0,build.stderr)
            self.assertEqual(subprocess.run([str(executable),str(good)]).returncode,0)
            self.assertNotEqual(subprocess.run([str(executable),str(bad)]).returncode,0)


if __name__=="__main__":
    unittest.main()
