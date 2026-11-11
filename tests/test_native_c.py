from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parent.parent


class NativeCRuntimeTests(unittest.TestCase):
    def test_compiles_and_executes_real_core(self):
        cc = shutil.which("cc") or shutil.which("gcc")
        if not cc:
            self.skipTest("Host C compiler missing")
        with tempfile.TemporaryDirectory() as temp:
            binary = str(Path(temp) / "native_runtime_test")
            result = subprocess.run([
                cc, "-std=c99", "-Wall", "-Wextra", "-Werror", "-O2",
                "-I", str(REPO / "runtime/core"),
                "-I", str(REPO / "examples/source-port/generated"),
                str(REPO / "runtime/core/pp_runtime.c"),
                str(REPO / "runtime/core/pp_game.c"),
                str(REPO / "examples/source-port/generated/score.c"),
                str(REPO / "tests/native_runtime_test.c"), "-o", binary,
            ], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            run = subprocess.run([binary], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn("points=9", run.stdout)
