"""Contract tests for measured telemetry and same-build evidence integrity."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from pocketport.cli import parser, run
from pocketport.field_lab import FieldLabError, analyze_frames, audit_field_manifest


class FieldLabTests(unittest.TestCase):
    def test_profile_real_numeric_samples_and_percentiles(self):
        with tempfile.TemporaryDirectory() as d:
            csv_file = Path(d) / "frames.csv"
            csv_file.write_text(
                "frame_ms,phase,cpu_ms,gpu_ms,heap_free_kb,linear_free_kb\n"
                "12,world,4,3,1000,1500\n"
                "16,world,5,7,900,1400\n"
                "40,world,12,20,850,1200\n"
                "120,loading,20,90,700,600\n",
                encoding="utf-8",
            )
            data = analyze_frames(csv_file, target_fps=30)
            self.assertEqual(data["source_rows"], 4)
            self.assertEqual(data["frame_time"]["p99_ms"], 120)
            self.assertEqual(data["frame_time"]["over_frame_budget"], 2)
            self.assertEqual(data["frame_time"]["stalls_over_50ms"], 1)
            self.assertEqual(data["phases"]["world"]["frames"], 3)
            self.assertEqual(data["minimum_available_kb"]["linear_free_kb"], 600)
            self.assertEqual(data["optional_metrics"]["gpu_ms"]["worst"], 90)

    def test_profile_rejects_fabricated_or_invalid_numbers(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "log.csv"
            for entry in ("nan", "-1", "inf", "oops", "120001", ""):
                p.write_text("frame_ms\n" + entry + "\n", encoding="utf-8")
                with self.assertRaises(FieldLabError):
                    analyze_frames(p)
            p.write_text("other\n1\n")
            with self.assertRaises(FieldLabError):
                analyze_frames(p)
            with self.assertRaises(FieldLabError):
                analyze_frames(p, target_fps=25)

    def _make_project(self, folder: Path):
        binary = folder / "game.3dsx"
        binary.write_bytes(b"3DSX" + bytes(64))
        digest = hashlib.sha256(binary.read_bytes()).hexdigest()
        (folder / "boot.log").write_text("Observed boot test report\n", encoding="utf-8")
        manifest = {
            "schema_version": 1,
            "target": "new3ds",
            "artifact": {"path": "game.3dsx", "sha256": digest},
            "scenarios": [{
                "id": "boot", "environment": "emulator",
                "result": "pass", "artifact_sha256": digest,
                "evidence": "boot.log",
            }],
        }
        p = folder / "field.json"
        p.write_text(json.dumps(manifest), encoding="utf-8")
        return p, manifest, digest

    def test_audit_records_but_never_invents_gameplay(self):
        with tempfile.TemporaryDirectory() as d:
            path, manifest, digest = self._make_project(Path(d))
            data = audit_field_manifest(path)
            self.assertTrue(data["artifact_header_and_sha256_verified"])
            self.assertEqual(data["status"], "evidence-recorded-needs-human-review")
            self.assertFalse(data["playable_verified"])
            self.assertEqual(data["recorded_scenarios"][0]["same_build_hash"], True)
            self.assertIn("movement", data["core_scenarios_not_evidenced"])
            self.assertEqual(data["actual_artifact_sha256"], digest)

    def test_mismatched_build_and_missing_evidence_downgrade(self):
        with tempfile.TemporaryDirectory() as d:
            path, manifest, _ = self._make_project(Path(d))
            manifest["scenarios"][0]["artifact_sha256"] = "0" * 64
            manifest["scenarios"][0].pop("evidence")
            path.write_text(json.dumps(manifest), encoding="utf-8")
            data = audit_field_manifest(path)
            self.assertEqual(data["status"], "incomplete-or-inconsistent")
            self.assertFalse(data["recorded_scenarios"][0]["same_build_hash"])
            self.assertTrue(any("pass claim" in x for x in data["issues"]))

    def test_header_hash_path_safety_and_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            path, manifest, _ = self._make_project(folder)
            (folder / "game.3dsx").write_bytes(b"EXEX" + bytes(64))
            self.assertFalse(audit_field_manifest(path)["artifact_header_and_sha256_verified"])
            manifest["artifact"]["path"] = "../outside.3dsx"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(FieldLabError):
                audit_field_manifest(path)
            path.write_text('{"schema_version":1,"target":"new3ds","target":"old3ds"}')
            with self.assertRaises(FieldLabError):
                audit_field_manifest(path)

    def test_cli_wiring(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            f = folder / "frames.csv"
            f.write_text("frame_ms,phase\n20,world\n", encoding="utf-8")
            args = parser().parse_args(["profile-frames", str(f), "--target-fps", "60"])
            self.assertEqual(run(args)["target_fps"], 60)
            p, _, _ = self._make_project(folder)
            args = parser().parse_args(["field-audit", str(p)])
            self.assertFalse(run(args)["playable_verified"])

    def test_missing_artifact_is_not_a_native_success(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "field.json"
            p.write_text(json.dumps({"schema_version": 1, "target": "old3ds",
                                     "scenarios": []}), encoding="utf-8")
            data = audit_field_manifest(p)
            self.assertFalse(data["artifact_header_and_sha256_verified"])
            self.assertEqual(data["status"], "incomplete-or-inconsistent")

    def test_input_bounds_and_symlink_protection(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "field.json"
            p.write_text(" " * (64 * 1024 + 1), encoding="utf-8")
            with self.assertRaises(FieldLabError):
                audit_field_manifest(p)
            q = Path(d) / "symlink.json"
            try:
                q.symlink_to(p)
            except (NotImplementedError, OSError):
                pass
            else:
                with self.assertRaises(FieldLabError):
                    audit_field_manifest(q)


    def test_rejects_invalid_json_types(self):
        with tempfile.TemporaryDirectory() as d:
            p, manifest, _ = self._make_project(Path(d))
            manifest["target"] = []
            p.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(FieldLabError):
                audit_field_manifest(p)
            manifest["target"] = "new3ds"
            manifest["scenarios"][0]["result"] = {}
            p.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(FieldLabError):
                audit_field_manifest(p)

    def test_rejects_symlinked_evidence_even_inside_workspace(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            p, manifest, _ = self._make_project(folder)
            link = folder / "boot-link.txt"
            try:
                link.symlink_to(folder / "boot.log")
            except (NotImplementedError, OSError):
                self.skipTest("Symlink support unavailable")
            manifest["scenarios"][0]["evidence"] = "boot-link.txt"
            p.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(FieldLabError):
                audit_field_manifest(p)


if __name__ == "__main__":
    unittest.main()
