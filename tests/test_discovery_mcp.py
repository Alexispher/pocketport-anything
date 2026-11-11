"""Mocked public search and read-only MCP confinement regression tests."""
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from pocketport.discovery import search_repositories
from pocketport.mcp import handle, safe_path

class FakeHTTP:
    def __init__(self,obj):
        self.data=io.BytesIO(json.dumps(obj).encode())
    def __enter__(self):
        return self.data
    def __exit__(self,*args):
        return False

class ReadOnlyAgentTests(unittest.TestCase):
    def test_public_results_are_only_leads(self):
        payload={"items":[{"full_name":"test/repo","html_url":"https://github.com/test/repo",
                           "license":{"spdx_id":"MIT"}}]}
        with patch("pocketport.discovery.urllib.request.urlopen",
                   return_value=FakeHTTP(payload)) as method:
            r=search_repositories("Zelda",limit=3)
        self.assertEqual(r["status"],"search-completed")
        self.assertIn("not buildable",r["candidates"][0]["status"])
        self.assertIn("Nintendo+3DS+port",method.call_args.args[0].full_url)

    def test_network_failure_reports_uncertainty(self):
        with patch("pocketport.discovery.urllib.request.urlopen",
                   side_effect=OSError("offline")):
            self.assertEqual(search_repositories("Skyrim")["status"],"search-unavailable")

    def test_workspace_confinement(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            p=root/"ok"
            p.write_bytes(b"x")
            self.assertEqual(safe_path(root,"ok"),p)
            with self.assertRaises(ValueError):
                safe_path(root,"../secret")
            (root/"link").symlink_to(p)
            with self.assertRaises(ValueError):
                safe_path(root,"link")

    def test_mcp_tools(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            listing=handle({"jsonrpc":"2.0","id":1,"method":"tools/list"},root)
            self.assertIn("research",[tool["name"] for tool in listing["result"]["tools"]])
            answer=handle({"jsonrpc":"2.0","id":2,"method":"tools/call",
                           "params":{"name":"research","arguments":{"game":"Skyrim"}}},root)
            self.assertFalse(answer["result"]["isError"])
            self.assertIn("Skyrim",answer["result"]["content"][0]["text"])
            blocked=handle({"jsonrpc":"2.0","id":3,"method":"tools/call",
                            "params":{"name":"inspect_nup","arguments":{"path":"../secret"}}},root)
            self.assertTrue(blocked["result"]["isError"])

if __name__=="__main__":
    unittest.main()
