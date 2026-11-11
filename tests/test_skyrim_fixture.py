"""Verify original built-in geometry and SD-card preparation."""
from __future__ import annotations
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pocketport.skyrim.fixture import fixture_mesh, fixture_scene, generate, _c_header
from pocketport.skyrim.nif import decode_mesh, encode_mesh
from pocketport.skyrim.scene import read_scene


class NativeFixtureTests(unittest.TestCase):
    def test_original_floor_and_three_boxes(self):
        mesh=fixture_mesh()
        self.assertGreater(len(mesh.triangles), 12)
        self.assertGreater(len(mesh.vertices), 24)
        self.assertTrue(any(v[2] < 0 for v in mesh.vertices))
        self.assertTrue(any(v[2] > 90 for v in mesh.vertices))
        self.assertEqual(len(mesh.triangles), len(decode_mesh(encode_mesh(mesh)).triangles))
        self.assertEqual(len(read_scene(fixture_scene())["instances"]), 3)

    def test_production_roundtrip_and_deterministic_output(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            a=generate(root/"first",header=root/"first.h")
            b=generate(root/"second",header=root/"second.h")
            self.assertEqual(a["mesh_sha256"],b["mesh_sha256"])
            self.assertEqual(a["scene_sha256"],b["scene_sha256"])
            self.assertEqual((root/"first.h").read_bytes(),(root/"second.h").read_bytes())
            for name in ("mesh.ppmg","scene.ppsc"):
                self.assertEqual((root/"first/3ds/pocketport/skyrim"/name).read_bytes(),
                                 (root/"second/3ds/pocketport/skyrim"/name).read_bytes())

    def test_generated_c_header_has_real_geometry(self):
        text=_c_header(decode_mesh(encode_mesh(fixture_mesh())))
        self.assertIn("PP_BUILTIN_VERTICES",text)
        self.assertIn("PP_BUILTIN_TRIANGLES",text)
        self.assertIn("pp_builtin_vertices[]",text)
        self.assertIn("pp_builtin_triangles[]",text)

    def test_cli_generates_ready_sd_folder(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            repository=Path(__file__).resolve().parents[1]
            completed=subprocess.run([sys.executable,"-m","pocketport","skyrim",
                                     "test-scene","--output",str(root)],
                                     cwd=repository,capture_output=True,text=True)
            self.assertEqual(completed.returncode,0,completed.stderr)
            self.assertTrue((root/"3ds/pocketport/skyrim/mesh.ppmg").exists())
            self.assertTrue((root/"3ds/pocketport/skyrim/scene.ppsc").exists())
            self.assertEqual(json.loads(completed.stdout)["mesh_triangles"],
                             len(fixture_mesh().triangles))

    def test_corrupted_payload_rejected(self):
        mesh=encode_mesh(fixture_mesh())
        from pocketport.skyrim.nif import NIFError
        with self.assertRaises(NIFError):
            decode_mesh(mesh[:-1])
        from pocketport.skyrim.scene import SceneError
        with self.assertRaises(SceneError):
            read_scene(fixture_scene()[:-1])

if __name__ == "__main__":
    unittest.main()
