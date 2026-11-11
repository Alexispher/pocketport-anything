"""Integrated original game sample: inspect, plan, translate, optimize, build, test, report."""
from __future__ import annotations

from pathlib import Path
from .assets import optimize
from .build import build_project, test_project, report_project
from .inventory import inventory, sha256, write_json
from .planning import choose
from .translation import parse, verify_host

ROOT = Path(__file__).resolve().parent.parent


def run_original_demo(out: Path) -> dict:
    sample = ROOT / "examples/asset-pipeline/assets"
    project = ROOT / "examples/source-port/project.json"
    ir = ROOT / "examples/translation-demo/score.ppir"
    out = out.resolve()
    if out == sample or sample in out.parents or out in sample.parents:
        raise ValueError("Refusing to put demo outputs in original source assets")
    # This is an original, MIT-redistributable game; its source provenance is known.
    inspected = inventory(sample)
    plan = choose({"source_available": True, "license_ok": True}, "new3ds")
    reference = verify_host(parse(ir.read_text(encoding="utf-8")))
    assets = optimize(sample, out / "assets", "balanced")
    built = build_project(project, "host")
    tests = test_project(project, "host") if built["returncode"] == 0 else {"returncode": 1, "error": "build failed"}
    classified = report_project(project)
    result = {"game": "Star Catcher (original)", "inventory": inspected, "route": plan,
              "translation": reference, "assets": {"processed": assets["processed_count"],
                                                    "report_sha256": sha256(out / "assets/asset-report.json")},
              "host_build": {"returncode": built["returncode"], "artifact": built.get("artifact")},
              "host_tests": {"returncode": tests["returncode"], "cases": tests.get("cases")},
              "console_levels": classified["levels"],
              "conclusion": "Host-side demo verified if return codes are zero; no devkitARM, emulator or hardware claim"}
    write_json(out / "unified-demo-report.json", result)
    return result
