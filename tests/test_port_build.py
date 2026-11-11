"""Safety gates for real devkitARM build and copyleft source-bundled release."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pocketport.source_port import port_project, PortError
from pocketport.port_build import native_build, package_native


class PortBuildSafetyTests(unittest.TestCase):
    def _workspace(self, root: Path) -> Path:
        game=root/"real-source"
        game.mkdir()
        (game/"src").mkdir()
        (game/"src/main.c").write_text("int main(void) {return 0;}\n")
        (game/"Makefile").write_text("all:\n\t@echo native build requires toolchain\n")
        (game/"COPYING").write_text("GNU GENERAL PUBLIC LICENSE\n")
        dst=root/"adapted"
        port_project(game,dst)
        return dst

    def test_never_execute_untrusted_game_makefile(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            p=self._workspace(root)
            with self.assertRaisesRegex(PortError,"explicit"):
                native_build(p)
            self.assertFalse((p/"native-build.log").exists())

    def test_toolchain_missing_is_clear_and_no_fake_binary(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            p=self._workspace(root)
            with patch.dict(os.environ,{"DEVKITPRO":"","DEVKITARM":""}):
                with self.assertRaisesRegex(PortError,"genuine devkitARM"):
                    native_build(p,execute_trusted_build=True)
            self.assertEqual(list((p/"source").glob("*.3dsx")),[])

    def test_untrusted_package_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            p=self._workspace(root)
            with self.assertRaisesRegex(PortError,"authorization"):
                package_native(p,root/"game.zip")
            self.assertFalse((root/"game.zip").exists())

    def test_missing_compilation_report_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            p=self._workspace(root)
            with self.assertRaisesRegex(PortError,"build evidence"):
                package_native(p,root/"game.zip",redistribution_authorized=True)
            self.assertFalse((root/"game.zip").exists())

    def test_failed_or_invented_build_report_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            p=self._workspace(root)
            (p/"native-build.json").write_text(json.dumps({
                "status":"BUILD_FAILED", "artifacts":[],
                "returncode":1}))
            with self.assertRaisesRegex(PortError,"never produced"):
                package_native(p,root/"game.zip",redistribution_authorized=True)

    def test_fail_closed_if_original_source_modified(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            p=self._workspace(root)
            (p/"source/src/main.c").write_text("tampered code")
            with self.assertRaisesRegex(PortError,"corrupted"):
                native_build(p,execute_trusted_build=True)

    def test_build_timeout_bounds(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            p=self._workspace(root)
            with self.assertRaisesRegex(PortError,"5..600"):
                native_build(p,execute_trusted_build=True,timeout=99999)

if __name__ == "__main__":
    unittest.main()
