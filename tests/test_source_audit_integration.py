"""CLI + MCP regression tests for the agent-facing source audit."""
import json
from pathlib import Path
import tempfile
import unittest

from pocketport.cli import parser, run
from pocketport.mcp import handle


class SourceAuditIntegrations(unittest.TestCase):
    def test_cli_source_audit(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "game.cpp").write_text("int main(void) { glDrawArrays(0,0,3); }\n")
            args = parser().parse_args(["source-audit", str(root), "--target", "new3ds"])
            response = run(args)
            self.assertEqual(response["target"], "new3ds")
            self.assertTrue(response["verification"]["source_inspection"])
            self.assertFalse(response["verification"]["gameplay"])
            self.assertIn("graphics", response["findings_by_subsystem"])

    def test_mcp_audit_is_scoped_and_readonly(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            game = root / "game"
            game.mkdir()
            (game / "main.c").write_text("int main(void) { return 0; }\n")
            request = {"jsonrpc": "2.0", "id": 11, "method": "tools/call",
                       "params": {"name": "source_audit",
                                  "arguments": {"path": "game", "target": "old3ds"}}}
            response = handle(request, root)
            self.assertFalse(response["result"]["isError"])
            payload = json.loads(response["result"]["content"][0]["text"])
            self.assertEqual(payload["source_counts"][".c"], 1)
            self.assertEqual(payload["target"], "old3ds")
            self.assertEqual(len(list(game.iterdir())), 1)
            request["params"]["arguments"]["path"] = "../escape"
            blocked = handle(request, root)
            self.assertTrue(blocked["result"]["isError"])

    def test_mcp_rejects_malformed_target(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "main.c").write_text("int main(void){}\n")
            result = handle(
                {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                 "params": {"name": "source_audit",
                            "arguments": {"path": ".", "target": "desktop"}}}, root)
            self.assertTrue(result["result"]["isError"])


if __name__ == "__main__":
    unittest.main()
