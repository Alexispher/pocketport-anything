"""Real source import, narrow adaptation, and integrity regressions.

Synthetic fixtures are not presented as a game port. An independent CI job
imports the actual pinned GPL game The Legend of Edgar instead.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from pocketport.source_port import (
    inspect_source, port_project, verify_port, PortError, MAX_FILE_BYTES
)
from pocketport.mcp import handle


ROOT = Path(__file__).resolve().parents[1]


def fixture(base: Path) -> Path:
    source = base / "original"
    (source / "src").mkdir(parents=True)
    (source / "LICENSE").write_text(
        "GNU GENERAL PUBLIC LICENSE\nThis is a noncommercial synthetic test fixture only.\n",
        encoding="utf-8")
    (source / "CMakeLists.txt").write_text(
        "cmake_minimum_required(VERSION 3.10)\nproject(Example C)\n", encoding="utf-8")
    (source / "src" / "game.h").write_text(
        "#ifndef GAME_H\n#define GAME_H\nextern int progress;\n#endif\n", encoding="utf-8")
    (source / "src" / "main.c").write_text(
        '#include "game.h"\n#include <SDL2/SDL.h>\n'
        "int main(int argc, char **argv) {\n"
        " SDL_Init(SDL_INIT_VIDEO); SDL_CreateRenderer(0,0,SDL_RENDERER_ACCELERATED);\n"
        " SDL_Event event; while(SDL_PollEvent(&event)) {progress++;}\n"
        ' fopen("progress.sav","wb");\n'
        " return argc + (argv != 0);\n}\n", encoding="utf-8")
    (source / "src" / "game.c").write_text(
        '#include "game.h"\nint progress=0;\n', encoding="utf-8")
    (source / "assets").mkdir()
    (source / "assets" / "level.dat").write_bytes(b"ORIGINAL_LEVEL_FIXTURE")
    return source


class ImportedSourceTests(unittest.TestCase):
    def test_scan_actual_symbols_build_entrypoint_and_includes(self):
        with tempfile.TemporaryDirectory() as d:
            source=fixture(Path(d))
            inspection=inspect_source(source)
            self.assertEqual(inspection["status"],"STATIC_INSPECTED_NOT_PORTED")
            self.assertIn("CMakeLists.txt",inspection["build_systems"])
            self.assertIn("src/main.c",inspection["entrypoint_candidates"])
            self.assertIn("SDL2_video",inspection["rule_summary"])
            self.assertIn("SDL2_accelerated",inspection["rule_summary"])
            self.assertIn("game_loop",inspection["rule_summary"])
            self.assertIn("filesystem_io",inspection["rule_summary"])
            self.assertFalse(inspection["verified_native_build"])
            self.assertEqual(inspection["languages"],["C"])
            self.assertIn("src/game.h",
                          [x["resolved"] for x in inspection["dependency_graph"]])

    def test_copy_is_non_destructive_and_hashes_original_source(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            source=fixture(root)
            snapshot=(source/"src/main.c").read_bytes()
            target=root/"adapted"
            result=port_project(source,target)
            self.assertEqual(result["status"],"SOURCE_ADAPTED_NOT_NATIVE_COMPILED")
            self.assertEqual(result["patches"],0)
            self.assertEqual((source/"src/main.c").read_bytes(),snapshot)
            self.assertEqual((target/"source/src/main.c").read_bytes(),snapshot)
            self.assertFalse((target/"source/assets/level.dat").exists())
            self.assertEqual(verify_port(target)["verified_files"],5)
            self.assertIn("SDL2_accelerated",
                          [x["symbol"] for x in json.loads((target/"port.json").read_text())
                           ["compatibility"]["open_findings"]])

    def test_assets_copied_only_with_explicit_opt_in(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            source=fixture(root)
            result=port_project(source,root/"all",copy_assets=True)
            self.assertTrue(result["assets_copied"])
            self.assertEqual((root/"all/source/assets/level.dat").read_bytes(),
                             b"ORIGINAL_LEVEL_FIXTURE")
            self.assertEqual(verify_port(root/"all")["verified_files"],6)

    def test_adapter_patches_only_explicit_edgar_renderer(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            source=fixture(root)
            init=source/"src/init.c"
            init.write_text(
                "/* Copyright Parallel Realities; GPL 2 or later. */\n"
                "void init(char *title,int joystickNum) {\n"
                "\trendererFlags = SDL_RENDERER_ACCELERATED;\n"
                "\tkeep_original_game_logic();\n"
                "}\n",encoding="utf-8")
            before=init.read_bytes()
            port=port_project(source,root/"edgar",adapter="edgar-sdl2")
            self.assertEqual(port["patches"],1)
            self.assertEqual(init.read_bytes(),before)
            after=(root/"edgar/source/src/init.c").read_text()
            self.assertIn("SDL_RENDERER_SOFTWARE",after)
            self.assertIn("#if defined(__3DS__)",after)
            self.assertIn("keep_original_game_logic();",after)
            diff=(root/"edgar/review.patch").read_text()
            self.assertIn("--- a/src/init.c",diff)
            self.assertIn("+\t\trendererFlags = SDL_RENDERER_SOFTWARE;",diff)
            self.assertTrue(verify_port(root/"edgar")["sha256_verified"])

    def test_historic_native_abbaye_audio_adapter(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            source=fixture(root)
            (source/"src/3ds").mkdir()
            (source/"src/3ds/audio.h").write_text(
                "void aud_StopMusic();\n",encoding="utf-8")
            (source/"src/main.c").write_text(
                "/* GPL v3 */\nvoid main_game(void){gfx_Init();}\n",encoding="utf-8")
            (source/"src/startscreen.c").write_text(
                "void startscreen(void){aud_StopMusic(music); render_title();}\\n".replace("\\n","\n"),
                encoding="utf-8")
            original="void history(void){ aud_StopMusic(music); keep_game_progression(); }\n"
            (source/"src/history.c").write_text(original,encoding="utf-8")
            adapted=root/"native"
            result=port_project(source,adapted,adapter="abbaye-native-3ds")
            self.assertEqual(result["patches"],2)
            self.assertIn("aud_StopMusic();",(adapted/"source/src/startscreen.c").read_text())
            changed=(adapted/"source/src/history.c").read_text()
            self.assertIn("aud_StopMusic();",changed)
            self.assertIn("keep_game_progression();",changed)
            self.assertEqual((source/"src/history.c").read_text(),original)
            self.assertTrue(verify_port(adapted)["sha256_verified"])

    def test_adapter_rejects_nonmatching_edgar(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            source=fixture(root)
            with self.assertRaises(PortError):
                port_project(source,root/"bad",adapter="edgar-sdl2")
            self.assertFalse((root/"bad").exists())

    def test_never_overwrite_workspace_or_source(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            source=fixture(root)
            with self.assertRaises(PortError):
                port_project(source,source/"output")
            target=root/"already"
            target.mkdir()
            sentinel=target/"untouched"
            sentinel.write_bytes(b"DO_NOT_REPLACE")
            with self.assertRaises(PortError):
                port_project(source,target)
            self.assertEqual(sentinel.read_bytes(),b"DO_NOT_REPLACE")

    def test_verify_detects_file_tampering(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            source=fixture(root)
            target=root/"port"
            port_project(source,target)
            (target/"source/src/game.c").write_text("changed")
            with self.assertRaisesRegex(PortError,"corrupted"):
                verify_port(target)

    def test_verify_rejects_malicious_manifest_relative_path(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            source=fixture(root)
            target=root/"port"
            port_project(source,target)
            manifest=target/"port.json"
            content=json.loads(manifest.read_text())
            content["files"][0]["path"]="../../outside"
            manifest.write_text(json.dumps(content))
            with self.assertRaisesRegex(PortError,"Unsafe"):
                verify_port(target)

    def test_symlink_source_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            source=fixture(root)
            try:
                (source/"linked.c").symlink_to(source/"src/game.c")
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks unavailable")
            with self.assertRaisesRegex(PortError,"Symbolic-link"):
                inspect_source(source)

    def test_excessive_single_asset_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            source=fixture(root)
            with (source/"assets/huge.bin").open("wb") as file:
                file.truncate(MAX_FILE_BYTES + 1)
            with self.assertRaisesRegex(PortError,"Oversized"):
                inspect_source(source)

    def test_cli_inspect_port_verify_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            source=fixture(root)
            out=root/"report.json"
            one=subprocess.run([sys.executable,"-m","pocketport","inspect-source",
                                str(source),"--out",str(out)],
                               cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(one.returncode,0,one.stderr)
            self.assertTrue(out.is_file())
            created=root/"cliport"
            two=subprocess.run([sys.executable,"-m","pocketport","port",str(source),
                                "--out",str(created),"--target","old3ds"],
                               cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(two.returncode,0,two.stderr)
            three=subprocess.run([sys.executable,"-m","pocketport","verify-port",
                                  str(created)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(three.returncode,0,three.stderr)
            self.assertTrue(json.loads(three.stdout)["sha256_verified"])

    def test_readonly_mcp_source_inspection(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            fixture(root)
            request={"jsonrpc":"2.0","id":100,"method":"tools/call",
                     "params":{"name":"inspect_source",
                               "arguments":{"path":"original"}}}
            result=handle(request,root)
            self.assertFalse(result["result"]["isError"])
            answer=json.loads(result["result"]["content"][0]["text"])
            self.assertEqual(answer["files"]["source_files"],3)
            request["params"]["arguments"]["path"]="../non-authorized"
            self.assertTrue(handle(request,root)["result"]["isError"])

    def test_rejects_unsupported_target_or_adapter(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            source=fixture(root)
            for arguments in ({"target":"switch2"},{"adapter":"magic"}):
                with self.assertRaises(PortError):
                    port_project(source,root/"invalid",**arguments)


if __name__=="__main__":
    unittest.main()
