"""Real source-project compatibility and Old/New 3DS control coverage."""
import json
from pathlib import Path
import tempfile
import unittest

from pocketport.port_assessment import (
    AssessmentError, assess_project, control_coverage, load_controls)
from pocketport.cli import parser, run


class PortAssessmentTests(unittest.TestCase):
    def game(self, root):
        src=root/"my-game"
        src.mkdir()
        (src/"COPYING").write_text("GNU GENERAL PUBLIC LICENSE\n")
        (src/"Makefile").write_text("all:\n\t@echo only local fixture\n")
        (src/"main.c").write_text(
            "#include <SDL.h>\n"
            "int main(void) { SDL_PollEvent(&event); glDrawArrays(0,0,3);\n"
            "Mix_OpenAudio(44100,0,2,2048); return 0; }\n")
        return src

    @staticmethod
    def controls():
        return {"schema_version":1,"required":["move","pause","attack","back"],
                "bindings":{"move":["circle_left","dpad_left"],
                            "pause":["start"],"attack":["a"],"back":["b"]}}

    def test_source_issues_with_exact_locations(self):
        with tempfile.TemporaryDirectory() as td:
            src=self.game(Path(td))
            result=assess_project(src,target="old3ds",controls=self.controls())
            self.assertTrue(result["verification"]["source_inspected"])
            self.assertFalse(result["verification"]["gameplay"])
            self.assertFalse(result["verification"]["native_build"])
            self.assertEqual(result["controller_coverage"]["status"],"complete")
            symbols={i["symbol"] for i in result["issues"]}
            self.assertIn("desktop-opengl",symbols)
            self.assertIn("desktop-audio",symbols)
            self.assertIn("desktop-input",symbols)
            for item in result["issues"]:
                self.assertIn(item["classification"],("existing-adapter","new-adapter",
                              "requires-investigation","game-specific"))
                self.assertEqual(item["path"],"main.c")
                self.assertGreaterEqual(item["line"],1)

    def test_controls_missing_or_new_only(self):
        c=self.controls()
        c["bindings"]["attack"]=["zr"]
        result=control_coverage(c,"old3ds")
        self.assertEqual(result["status"],"incomplete")
        self.assertIn("attack",result["new3ds_only_on_old"])
        result=control_coverage(c,"new3ds")
        self.assertEqual(result["status"],"complete")

    def test_touch_only_cannot_replace_essential_action(self):
        c=self.controls()
        c["bindings"]["pause"]=["touch"]
        result=control_coverage(c,"new3ds")
        self.assertIn("pause",result["missing"])
        self.assertIn("pause",result["touch_only"])

    def test_schema_rejection(self):
        c=self.controls()
        c["schema_version"]=2
        with self.assertRaises(AssessmentError):
            control_coverage(c,"old3ds")
        c=self.controls()
        c["bindings"]["attack"]=["arbitrary_command"]
        with self.assertRaises(AssessmentError):
            control_coverage(c,"new3ds")

    def test_cli_reports_and_refuses_invalid(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            src=self.game(root)
            controls=root/"controls.json"
            controls.write_text(json.dumps(self.controls()))
            args=parser().parse_args(["port-assess",str(src),"--target","new3ds",
                                      "--controls",str(controls)])
            data=run(args)
            self.assertEqual(data["controller_coverage"]["status"],"complete")
            args=parser().parse_args(["control-coverage",str(controls),"--target","old3ds"])
            self.assertEqual(run(args)["status"],"complete")

    def test_readonly_controls_loader(self):
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)/"controls.json"
            target.write_text(json.dumps(self.controls()))
            self.assertEqual(load_controls(target)["required"][0],"move")
            target.write_text("{not json")
            with self.assertRaises(AssessmentError):
                load_controls(target)


if __name__ == "__main__":
    unittest.main()
