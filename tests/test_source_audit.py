"""Deterministic tests of read-only porting evidence discovery."""
import tempfile
import unittest
from pathlib import Path

from pocketport.source_audit import inspect_source_project


class SourceAuditTests(unittest.TestCase):
    def test_detects_actionable_platform_boundaries(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "CMakeLists.txt").write_text("project(Example)\n")
            (root / "LICENSE").write_text("Test fixture, not a permission grant\n")
            src = root / "src"
            src.mkdir()
            (src / "game.cpp").write_text(
                '#include "game.h"\n'
                '#include <windows.h>\n'
                'int main(int argc, char** argv) {\n'
                '  SDL_PollEvent(nullptr);\n'
                '  glDrawArrays(0, 0, 3);\n'
                '  while (running) { tick(); }\n'
                '  return 0;\n'
                '}\n')
            result = inspect_source_project(root)
            self.assertEqual(result["status"], "inspection-completed")
            self.assertFalse(result["verification"]["native_build"])
            self.assertEqual(result["license_status"], "not-reviewed; presence of a file is not permission")
            self.assertEqual(result["build_systems"][0]["system"], "CMake")
            self.assertEqual(result["entrypoint_candidates"][0]["line"], 3)
            self.assertEqual(result["game_loop_candidates"][0]["line"], 6)
            self.assertIn("graphics", result["findings_by_subsystem"])
            self.assertIn("input", result["findings_by_subsystem"])
            self.assertIn("platform", result["findings_by_subsystem"])
            self.assertEqual(result["quoted_local_includes"]["game.h"], 1)
            self.assertTrue(all(f["path"].startswith("src/") for f in result["findings"]))
            self.assertEqual(len(result["source_files"][0]["sha256"]), 64)

    def test_bounded_output_and_no_execution(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "Makefile").write_text("all:\n\ttouch ACTIVATED\n")
            (root / "game.c").write_text("void render() {\n" +
                                          " glDrawArrays(0,0,3);\n" * 140 + "}\n")
            report = inspect_source_project(root)
            self.assertEqual(len(report["findings"]), 120)
            self.assertTrue(report["findings_truncated"])
            self.assertFalse((root / "ACTIVATED").exists())

    def test_symlinks_and_build_trees_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "safe.c").write_text("int main(void) { return 0; }\n")
            (root / "unsafe.c").symlink_to(root / "safe.c")
            (root / "build").mkdir()
            (root / "build" / "bad.c").write_text("D3D11CreateDevice();\n")
            report = inspect_source_project(root)
            self.assertEqual(len(report["source_files"]), 1)
            self.assertEqual(report["findings"], [])
            with self.assertRaises(ValueError):
                inspect_source_project(root / "unsafe.c")

    def test_rejects_limits_and_wrong_target(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "one.c").write_text("int main(void){}\n")
            (root / "two.c").write_text("int main(void){}\n")
            with self.assertRaises(ValueError):
                inspect_source_project(root, max_files=1)
            with self.assertRaises(ValueError):
                inspect_source_project(root, max_files=5000)
            with self.assertRaises(ValueError):
                inspect_source_project(root, target="ps5")

    def test_large_and_binary_sources_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "big.c").write_bytes(b"a" * (1_048_576 + 1))
            (root / "binary.cpp").write_bytes(b"\0x")
            result = inspect_source_project(root)
            self.assertEqual(result["status"], "no-source-found")
            self.assertEqual(len(result["skipped_sources"]), 2)
            self.assertFalse(result["verification"]["gameplay"])

    def test_read_only_report_is_deterministic(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "game.c").write_text("int main(void){return 0;}\n")
            self.assertEqual(inspect_source_project(root), inspect_source_project(root))


if __name__ == "__main__":
    unittest.main()
