import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from pocketport.assets import PROFILES, optimize
from pocketport.build import build_project, report_project, test_project as run_project_tests
from pocketport.cli import main
from pocketport.environment import doctor
from pocketport.demo import run_original_demo

REPO = Path(__file__).resolve().parent.parent
PROJECT = REPO / "examples/source-port/project.json"


class PipelineTests(unittest.TestCase):
    def test_doctor_reports_external_dependency(self):
        self.assertIn("toolchain_ready_minimum", doctor())

    def test_cli_init_does_not_overwrite(self):
        with TemporaryDirectory() as tmp:
            dest = Path(tmp) / "game"
            self.assertEqual(main(["init", str(dest), "--game", "Original Sample"]), 0)
            self.assertEqual(json.loads((dest / "project.json").read_text())["state"], "identified-only")
            self.assertEqual(main(["init", str(dest), "--game", "Other"]), 2)

    def test_host_game_build_and_gameplay(self):
        result = build_project(PROJECT, "host")
        self.assertEqual(result["returncode"], 0, result.get("stderr"))
        self.assertTrue(result["host_compiled"])
        test = run_project_tests(PROJECT, "host")
        self.assertEqual(test["returncode"], 0)
        self.assertEqual(len(test["cases"]), 4)
        self.assertEqual(test["cases"][-1]["expected_fragment"], "score=9")
        report = report_project(PROJECT)
        self.assertFalse(report["levels"]["6"])
        self.assertFalse(report["levels"]["2"])

    def test_3ds_build_fails_without_toolchain(self):
        with patch("pocketport.build.shutil.which", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "toolchain missing"):
                build_project(PROJECT, "console")

    def test_3ds_testing_must_be_explicit(self):
        with self.assertRaises(RuntimeError):
            run_project_tests(PROJECT, "console")

    def test_optional_image_preparation_and_bounds(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow optional")
        with TemporaryDirectory() as tmp:
            source = Path(tmp) / "input"
            source.mkdir()
            Image.new("RGB", (700, 350), "red").save(source / "sample.png")
            (source / "unknown.xyz").write_bytes(b"x")
            out = Path(tmp) / "output"
            result = optimize(source, out, "old-3ds")
            self.assertEqual(result["processed_count"], 1)
            self.assertEqual(result["unsupported_count"], 1)
            self.assertFalse(result["files"][0]["hardware_compatible_encoded"])
            self.assertEqual(result["files"][0]["texture_dimensions"], [256, 128])
            self.assertTrue((out / "intermediate/sample.png").is_file())
            with self.assertRaises(ValueError):
                optimize(source, source / "output", "balanced")

    def test_unified_workflow_executes_components(self):
        try:
            import PIL  # noqa: F401
        except ImportError:
            self.skipTest("Pillow optional")
        with TemporaryDirectory() as tmp:
            result = run_original_demo(Path(tmp) / "outputs")
            self.assertEqual(result["route"]["route"], "source-port")
            self.assertEqual(result["host_tests"]["returncode"], 0)
            self.assertGreater(result["assets"]["processed"], 0)
            self.assertFalse(result["console_levels"]["2"])

    def test_unavailable_encoder_does_not_succeed(self):
        with TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            source.mkdir()
            with patch("pocketport.assets.shutil.which", return_value=None):
                with self.assertRaisesRegex(RuntimeError, "tex3ds"):
                    optimize(source, Path(tmp) / "output", "balanced", encode_3ds=True)
