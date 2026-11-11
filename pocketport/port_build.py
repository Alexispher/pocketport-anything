"""Explicit native build orchestration for adapted, user-trusted C/C++ game trees.

A source manifest is not a native binary; only an actual devkitARM command
and a newly produced 3DSX magic-valid artifact may earn CROSS_COMPILED.
Imported makefiles can execute commands and are NEVER run by inspection.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import zipfile

from .source_port import PortError, verify_port
from .build_diagnostics import diagnose

BUILD_TIMEOUT = 600
MAX_LOG = 2 * 1024 * 1024
BINARY_LIMIT = 64 * 1024 * 1024


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def _read_build(workspace: Path) -> tuple[dict, Path]:
    workspace = Path(workspace).resolve(strict=True)
    verify_port(workspace)
    m = json.loads((workspace / "port.json").read_text(encoding="utf-8"))
    root = workspace / "source"
    if not root.is_dir() or root.is_symlink():
        raise PortError("Imported source tree missing or unsafe")
    return m, root


def _valid_3dsx(binary: Path) -> bool:
    return (binary.is_file() and not binary.is_symlink() and
            32 < binary.stat().st_size <= BINARY_LIMIT and
            binary.open("rb").read(4) == b"3DSX")


def native_build(workspace: str | Path, *, execute_trusted_build: bool = False,
                 timeout: int = 300) -> dict:
    if not execute_trusted_build:
        raise PortError("External source build scripts can execute commands. "
                        "Require explicit --execute-trusted-build authorization.")
    if type(timeout) is not int or not 5 <= timeout <= BUILD_TIMEOUT:
        raise PortError("Build timeout must be 5..600 seconds")
    workspace = Path(workspace).resolve(strict=True)
    m, source = _read_build(workspace)
    makefile = source / "Makefile"
    if not makefile.is_file() or makefile.is_symlink():
        raise PortError("No supported native Makefile in adapted source tree; "
                        "a project-specific build adapter is required")
    pro = os.environ.get("DEVKITPRO")
    arm = os.environ.get("DEVKITARM")
    if not pro or not arm or not (Path(arm) / "3ds_rules").is_file():
        raise PortError("DEVKITPRO/DEVKITARM and genuine devkitARM 3ds_rules are required")
    path = os.pathsep.join([str(Path(arm) / "bin"), str(Path(pro) / "tools" / "bin"),
                            os.environ.get("PATH", "")])
    needed = ("make", "arm-none-eabi-gcc", "3dsxtool", "picasso")
    unavailable = [tool for tool in needed if not shutil.which(tool, path=path)]
    if unavailable:
        raise PortError("Missing actual Nintendo 3DS build tools: " + ", ".join(unavailable))
    before = {p.name: _sha(p) for p in source.glob("*.3dsx") if p.is_file()}
    start = time.monotonic()
    command = ["make", "-C", str(source)]
    env = dict(os.environ)
    env["PATH"] = path
    try:
        p = subprocess.run(command, env=env, cwd=workspace,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=timeout, check=False)
        output = p.stdout[:MAX_LOG].decode("utf-8", errors="replace")
        code = p.returncode
        truncated = len(p.stdout) > MAX_LOG
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or b"")[:MAX_LOG].decode("utf-8", errors="replace")
        code = 124
        truncated = True
    elapsed = round(time.monotonic() - start, 3)
    (workspace / "native-build.log").write_text(output, encoding="utf-8")
    artifacts = []
    for path_obj in sorted(source.glob("*.3dsx")):
        if not _valid_3dsx(path_obj):
            continue
        digest = _sha(path_obj)
        if before.get(path_obj.name) == digest:
            continue
        artifacts.append({"file": "source/" + path_obj.name,
                          "sha256": digest, "bytes": path_obj.stat().st_size,
                          "magic": "3DSX", "target": m["target"]})
    status = ("CROSS_COMPILED" if code == 0 and artifacts else
              "BUILD_FAILED" if code else "NO_NEW_NATIVE_3DSX")
    important = ("error:", "fatal error:", "undefined reference",
                 "no rule to make target", "not found", "make: ***",
                 "recipe for target", "failed")
    diagnostic_lines = [line.strip()[:450] for line in output.splitlines()
                        if any(token in line.lower() for token in important)]
    result = {"status": status,
              "structured_diagnostics": diagnose(output),
              "compiler_diagnostics": diagnostic_lines[-30:],
              "log_tail": "\n".join(output.splitlines()[-35:])[-12000:],
              "command": command, "returncode": 0 if status == "CROSS_COMPILED" else (code or 1),
              "elapsed_seconds": elapsed, "log_truncated": truncated,
              "log": str(workspace / "native-build.log"), "artifacts": artifacts,
              "emulator_tested": False, "hardware_tested": False,
              "gameplay_tested": False,
              "note": "This is a real cross-compile; no emulator/hardware observation."}
    (workspace / "native-build.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return result


def package_native(workspace: str | Path, output: str | Path, *,
                   redistribution_authorized: bool = False) -> dict:
    if not redistribution_authorized:
        raise PortError("Explicit redistribution authorization required; "
                        "verify ALL source, asset and music licenses")
    workspace = Path(workspace).resolve(strict=True)
    manifest, source = _read_build(workspace)
    report = workspace / "native-build.json"
    if not report.is_file() or report.is_symlink() or report.stat().st_size > 65536:
        raise PortError("No valid native build evidence; build first")
    data = json.loads(report.read_text(encoding="utf-8"))
    if data.get("status") != "CROSS_COMPILED" or not data.get("artifacts"):
        raise PortError("Native build never produced verified 3DSX")
    artifact_names = {x["file"] for x in data["artifacts"]}
    if len(artifact_names) != len(data["artifacts"]) or len(artifact_names)>32:
        raise PortError("Invalid artifact manifest: duplicate or excessive binaries")
    for name in artifact_names:
        # An external build report is NOT trusted as a filesystem path.
        if (not isinstance(name,str) or not name.startswith("source/") or
            len(name)>255 or Path(name).is_absolute() or
            any(part in ("", ".", "..") for part in name.split("/")) or
            len(Path(name).parts)!=2 or not name.endswith(".3dsx")):
            raise PortError("Unsafe native artifact location in build evidence")

        path_obj = workspace / name
        details = next(x for x in data["artifacts"] if x["file"] == name)
        if not _valid_3dsx(path_obj) or _sha(path_obj) != details["sha256"]:
            raise PortError("Native 3DSX missing or integrity mismatch: " + name)
    output = Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise PortError("Release destination already exists; refusing overwrite")
    if workspace == output.parent or workspace in output.parent.parents:
        raise PortError("Release must not overwrite imported project")
    files = sorted(p for p in source.rglob("*") if p.is_file() and not p.is_symlink())
    manifest_files = {item["path"] for item in manifest["files"]}
    # Keep binary distribution self-contained for copyleft source obligations.
    include = [p for p in files if p.relative_to(source).as_posix() in manifest_files]
    zip_part = output.with_name(output.name + ".incomplete")
    if zip_part.exists():
        raise PortError("Incomplete release archive exists; manual cleanup required")
    try:
        with zipfile.ZipFile(zip_part, "w", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=6, allowZip64=True) as zf:
            for p in include:
                zf.write(p, "source/" + p.relative_to(source).as_posix())
            for name in sorted(artifact_names):
                zf.write(workspace / name, "native/" + Path(name).name)
            for name in ("port.json", "review.patch", "native-build.json"):
                zf.write(workspace / name, name)
            zf.writestr("README-PORTING.txt",
                "PocketPort native game build (same-source bundle)\\n"
                "Original game and license notices are under source/.\\n"
                "Review all source and media/music licenses before distribution.\\n"
                "Binary was cross-compiled, not automatically verified in Azahar.\\n"
                "This ZIP includes the complete imported source and license evidence.\\n")
        os.replace(zip_part, output)
    finally:
        if zip_part.exists():
            zip_part.unlink()
    return {"file": str(output), "bytes": output.stat().st_size,
            "sha256": _sha(output), "source_files": len(include),
            "binaries": len(artifact_names), "status": "PACKAGED_WITH_SOURCE",
            "note": "Redistribution authorization was user-supplied, not independently verified"}
