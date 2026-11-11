"""End-to-end original synthetic Skyrim LE and SE installation conversion."""
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import lz4.block

from pocketport.skyrim.converter import convert_game, ConversionError
from pocketport.skyrim.nif import decode_mesh
from pocketport.skyrim.scene import read_scene
from test_skyrim import plugin_data, bsa_data
from test_skyrim_nif import synthetic_nif


def se_bsa(content: bytes) -> bytes:
    folder=b"meshes" + bytes([0])
    filename=b"test.nif" + bytes([0])
    packed=struct.pack("<I",len(content))+lz4.block.compress(content,store_size=False)
    offset=36+24+1+len(folder)+16+len(filename)
    return (struct.pack("<4s8I",b"BSA"+bytes([0]),105,36,3,1,1,
                        len(folder)+1,len(filename),0)
            +struct.pack("<QIIQ",0,1,0,0)
            +bytes([len(folder)])+folder
            +struct.pack("<QII",0,len(packed)|0x40000000,offset)
            +filename+packed)


class SkyrimConversionIntegration(unittest.TestCase):
    def _install(self,root,edition):
        game=root/"game"
        data=game/"Data"
        data.mkdir(parents=True)
        (data/"Skyrim.esm").write_bytes(plugin_data())
        nif=synthetic_nif(130 if edition=="SE" else 100)
        (data/"Skyrim - Meshes.bsa").write_bytes(
            se_bsa(nif) if edition=="SE" else bsa_data(nif))
        return game

    def test_original_skyrim_converts_static_geometry(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            source=self._install(root,"LE")
            output=root/"converted"
            report=convert_game(source,output,cell_id=0x200)
            self.assertEqual(report["archive_version"],104)
            self.assertEqual(report["mesh"]["triangles"],1)
            self.assertEqual(read_scene((output/"scene.ppsc").read_bytes())["count"],1)
            self.assertEqual(len(decode_mesh((output/"mesh.ppmg").read_bytes()).vertices),3)
            self.assertTrue((output/"manifest.json").is_file())
            with self.assertRaises(ConversionError):
                convert_game(source,output,cell_id=0x200)

    def test_special_edition_lz4_converts_static_geometry(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            source=self._install(root,"SE")
            report=convert_game(source,root/"output",cell_id=0x200)
            self.assertEqual(report["archive_version"],105)
            self.assertEqual(report["edition"],"Skyrim Special Edition")
            self.assertEqual(report["mesh"]["vertices"],3)

    def test_no_fake_scene_when_reference_missing(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            source=self._install(root,"SE")
            output=root/"missing"
            with self.assertRaises(ConversionError):
                convert_game(source,output,cell_id=0xabcd)
            self.assertFalse(output.exists())

    def test_python_cli_convert_subcommand(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            source=self._install(root,"SE")
            out=root/"cli_output"
            repo=Path(__file__).resolve().parents[1]
            p=subprocess.run([sys.executable,"-m","pocketport","skyrim","convert",
                             "--game-dir",str(source),"--cell","0x200","--output",str(out)],
                             cwd=repo,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertTrue((out/"scene.ppsc").is_file())
            self.assertEqual(json.loads((out/"manifest.json").read_text())["archive_version"],105)


if __name__=="__main__":
    unittest.main()
