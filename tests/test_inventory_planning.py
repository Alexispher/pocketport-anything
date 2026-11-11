import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from pocketport.inventory import classify, inventory, sha256
from pocketport.planning import choose


class InventoryPlanningTests(unittest.TestCase):
    def test_readonly_signatures_and_sha(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.png").write_bytes(b"\x89PNG\r\n\x1a\nfoo")
            self.assertEqual(classify(root / "a.png"), "png")
            self.assertEqual(sha256(root / "a.png"), hashlib.sha256((root / "a.png").read_bytes()).hexdigest())
            info = inventory(root)
            self.assertEqual(info["file_count"], 1)
            self.assertEqual(info["files"][0]["format"], "png")

    def test_unknown_format_not_mislabeled_as_supported(self):
        with TemporaryDirectory() as tmp:
            file = Path(tmp) / "x.nup"
            file.write_bytes(b"random")
            self.assertEqual(classify(file), "nup-unverified")

    def test_file_limit(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a").write_text("x")
            with self.assertRaises(ValueError):
                inventory(root, max_files=0)

    def test_symlink_skipped(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a").write_text("x")
            try:
                (root / "link").symlink_to(root / "a")
            except (OSError, NotImplementedError):
                self.skipTest("symlink unavailable")
            result = inventory(root)
            self.assertEqual(result["file_count"], 1)
            self.assertEqual(result["skipped"][0]["reason"], "symlink")

    def test_evidence_planner_prefers_native(self):
        result = choose({"existing_3ds_version": True, "source_available": True}, "old3ds")
        self.assertEqual(result["route"], "existing-3ds-version")

    def test_missing_evidence_requires_research(self):
        self.assertEqual(choose({}, "new3ds")["route"], "feasibility")

    def test_license_disallows(self):
        self.assertEqual(choose({"source_available": True, "license_ok": False}, "new3ds")["route"], "blocked")
