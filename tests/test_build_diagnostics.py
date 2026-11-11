"""Structured native compiler diagnostics do not pretend to fix failures."""
import tempfile
import unittest
from pathlib import Path
from pocketport.build_diagnostics import diagnose,diagnose_file
from pocketport.cli import parser,run


class BuildDiagnosticTests(unittest.TestCase):
    def test_missing_header_and_link_failure(self):
        log=("source/main.c:9:10: fatal error: SDL.h: No such file or directory\n"
             "ld: undefined reference to pp_main_game\n"
             "collect2: error: ld returned 1 exit status\n")
        r=diagnose(log)
        kinds={x["kind"] for x in r["findings"]}
        self.assertIn("missing-header",kinds)
        self.assertIn("undefined-symbol",kinds)
        self.assertTrue(all(x["correction_verified"] is False for x in r["findings"]))

    def test_linker_library_and_shader_failure(self):
        r=diagnose("ld: cannot find -lSDL2_mixer\npicasso: error syntax error\n")
        self.assertEqual({x["kind"] for x in r["findings"]},
                         {"missing-library","shader-failure"})

    def test_unmatched_log_must_not_claim_success(self):
        r=diagnose("unknown build event with no recognized patterns")
        self.assertEqual(r["status"],"no-matching-patterns")
        self.assertEqual(r["findings"],[])

    def test_log_limits_and_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"bad.log"
            p.write_text("something\n"*300000)
            with self.assertRaises(ValueError):
                diagnose_file(p)
            with self.assertRaises(ValueError):
                diagnose("x"*(2*1024*1024+1))

    def test_cli_diagnose(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"out.log"
            p.write_text("ld: undefined reference to 'missing_sym'\n")
            result=run(parser().parse_args(["diagnose-build",str(p)]))
            self.assertEqual(result["findings"][0]["kind"],"undefined-symbol")


if __name__=="__main__":
    unittest.main()
