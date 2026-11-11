"""Provider-neutral Agent Skills discovery, CLI and confined MCP regression."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pocketport.mcp import handle

ROOT=Path(__file__).resolve().parents[1]
PROFILE=ROOT/"examples"/"source-port"/"display-profile.json"


class ScreenAgentTests(unittest.TestCase):
    def test_skill_discovery_and_canonical_root(self):
        root=(ROOT/"SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(root.startswith("---\n"))
        self.assertIn("name: pocketport-anything",root)
        self.assertIn("docs/DUAL_SCREEN.md",root)
        for item in (".agents/skills/pocketport-anything/SKILL.md",
                     ".claude/skills/pocketport-anything/SKILL.md"):
            path=ROOT/item
            self.assertTrue(path.is_file())
            self.assertFalse(path.is_symlink())
            content=path.read_text(encoding="utf-8")
            self.assertTrue(content.startswith("---\n"))
            self.assertIn("description:",content)
            self.assertIn("SKILL.md",content)
            self.assertIn("canonical",content)

    def test_cli_assessment_and_compile_header(self):
        r=subprocess.run([sys.executable,"-m","pocketport","screen-assess",
                          str(PROFILE)],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)
        report=json.loads(r.stdout)
        self.assertEqual(report["hardware"]["bottom_logical_pixels"],[320,240])
        self.assertFalse(report["verified"]["emulator_visual"])
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)/"generated.h"
            p=subprocess.run([sys.executable,"-m","pocketport","screen-header",
                              str(PROFILE),"--out",str(output)],cwd=ROOT,
                             capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertIn("PP_PROFILE_INITIAL_PAGE",output.read_text())

    def test_mcp_display_assessment_workspace_only(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/"screen.json").write_bytes(PROFILE.read_bytes())
            request={"jsonrpc":"2.0","id":8,"method":"tools/call",
                     "params":{"name":"display_assessment",
                               "arguments":{"path":"screen.json"}}}
            result=handle(request,root)
            self.assertFalse(result["result"]["isError"])
            report=json.loads(result["result"]["content"][0]["text"])
            self.assertEqual(report["layout"]["bottom"],"hud")
            request["params"]["arguments"]["path"]="../private"
            blocked=handle(request,root)
            self.assertTrue(blocked["result"]["isError"])


if __name__=="__main__":
    unittest.main()
