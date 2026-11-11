"""Actual subprocess host/console build orchestration with captured evidence."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

from .inventory import sha256, write_json
from .translation import parse, emit_c

REPO = Path(__file__).resolve().parent.parent


def manifest_path(path: Path) -> tuple[Path, dict]:
    path = path.resolve()
    if not path.is_file():
        raise ValueError(f"Missing project manifest: {path}")
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema_version") != 1:
        raise ValueError("Unsupported project manifest schema version")
    return path.parent, doc


def ensure_generated(root: Path, doc: dict) -> Path:
    ir = root / doc["translation_input"]
    output = root / "generated"
    program = parse(ir.read_text(encoding="utf-8"))
    header, code = emit_c(program)
    expected = {"score.h": header, "score.c": code}
    for name, content in expected.items():
        dest = output / name
        if dest.is_file() and dest.read_text(encoding="utf-8") != content:
            raise RuntimeError(f"Generated file modified or out of sync: {dest}. Regenerate after reviewing changes.")
        if not dest.is_file():
            output.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
    return output


def run_logged(command: list[str], cwd: Path, evidence_file: Path, artifact: Path | None = None, timeout: int = 120) -> dict:
    started = time.time()
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False)
        record = {"command": command, "cwd": str(cwd), "returncode": result.returncode,
                  "stdout": result.stdout, "stderr": result.stderr, "duration_seconds": round(time.time()-started,3)}
    except (OSError, subprocess.TimeoutExpired) as exc:
        record = {"command": command, "cwd": str(cwd), "returncode": None, "error": str(exc),
                  "duration_seconds": round(time.time()-started,3)}
    if artifact and artifact.exists() and record["returncode"] == 0:
        record["artifact"] = {"path": str(artifact), "sha256": sha256(artifact), "bytes": artifact.stat().st_size}
    evidence_file.parent.mkdir(parents=True, exist_ok=True)
    write_json(evidence_file, record)
    return record


def build_project(manifest: Path, target: str) -> dict:
    root, doc = manifest_path(manifest)
    ensure_generated(root, doc)
    if target == "host":
        cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
        if not cc:
            raise RuntimeError("Host C compiler missing (cc/gcc/clang)")
        output = root / "build-host"
        output.mkdir(parents=True, exist_ok=True)
        exe = output / ("star-catcher-host.exe" if sys.platform == "win32" else "star-catcher-host")
        core = (root / doc["game_core"]).resolve()
        includes = ["-I", str(core.parent), "-I", str(root / "generated")]
        inputs = [str(root / "source" / "host_main.c"), str(core),
                  str(core.parent / "pp_runtime.c"), str(root / "generated" / "score.c")]
        command = [cc, "-std=c99", "-O2", "-Wall", "-Wextra", "-Werror", *includes, *inputs, "-o", str(exe)]
        record = run_logged(command, root, output / "build-evidence.json", exe)
        record["host_compiled"] = record["returncode"] == 0 and "artifact" in record
        record["platform"] = "host C executable, NOT Nintendo 3DS"
        return record
    if target == "console":
        if not (shutil.which("arm-none-eabi-gcc") and shutil.which("3dsxtool")):
            raise RuntimeError("3DS toolchain missing: install devkitPro devkitARM/libctru/citro2d and provide arm-none-eabi-gcc + 3dsxtool")
        record = run_logged(["make", "-C", str(root)], REPO, root / "build-evidence-console.json",
                            root / "star-catcher.3dsx", timeout=600)
        record["level"] = 2 if record["returncode"] == 0 and "artifact" in record else None
        record["platform"] = "3DS toolchain build; emulator/hardware not validated"
        return record
    raise ValueError("target must be host or console")


def test_project(manifest: Path, target: str) -> dict:
    root, doc = manifest_path(manifest)
    if target != "host":
        raise RuntimeError("Automated 3DS emulator/hardware tests are not configured; do not report success")
    build = build_project(manifest, "host")
    if build["returncode"] != 0 or "artifact" not in build:
        return {"returncode": build["returncode"], "error": "Host build failed", "build": build}
    exe = Path(build["artifact"]["path"])
    cases = [("N" * 66, "score=0"), ("B", "score=0"), ("L" * 30, "player=0"),
             ("L" * 4 + "N" * 62, "score=9")]
    observations = []
    for script, fragment in cases:
        command = [str(exe), "--script", script]
        proc = subprocess.run(command, capture_output=True, text=True, timeout=30)
        passed = proc.returncode == 0 and fragment in proc.stdout
        observations.append({"command": command, "returncode": proc.returncode, "stdout": proc.stdout,
                             "expected_fragment": fragment, "passed": passed})
    data = {"returncode": 0 if all(c["passed"] for c in observations) else 1,
            "cases": observations, "platform": "host game-core regression only; NOT console launch"}
    write_json(root / "build-host" / "test-evidence.json", data)
    return data


def report_project(manifest: Path) -> dict:
    root, doc = manifest_path(manifest)
    build = root / "build-host" / "build-evidence.json"
    test = root / "build-host" / "test-evidence.json"
    record = {"game": doc.get("game"), "target": doc.get("target"),
              "levels": {str(i): False for i in range(8)},
              "interpretation": {"0": "Identified", "1": "Analyzed", "2": "Buildable", "3": "Launches in emulator",
                                 "4": "Interactive", "5": "Playable vertical slice", "6": "Hardware validated", "7": "Full game validated"},
              "host_build": json.loads(build.read_text()) if build.exists() else None,
              "host_tests": json.loads(test.read_text()) if test.exists() else None,
              "warning": "Host evidence never upgrades 3DS Level 2-7. Console evidence is independently required."}
    # A manifest exists, so game identity is known; this does not imply 3DS runtime progress.
    record["levels"]["0"] = True
    return record
