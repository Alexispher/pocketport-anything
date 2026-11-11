"""Read-only, bounded C/C++ source-port audit. Does not execute imported code.

An evidence-driven first step for adapting an existing engine to Nintendo 3DS.
Findings identify source locations and required investigation, NOT proven
incompatibilities or automated support for arbitrary game engines.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import os
from pathlib import Path
import re

_SOURCE_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx"}
_ASM_SUFFIXES = {".s", ".asm"}
_SKIP = {".git", ".hg", ".svn", "__pycache__", "node_modules", "vendor", "third_party",
         "third-party", "build", "dist", ".venv", "venv", ".idea"}
_BUILD_FILES = {"makefile": "make", "gnumakefile": "make", "cmakelists.txt": "CMake",
                "meson.build": "Meson", "configure.ac": "Autotools",
                "configure.in": "Autotools", "premake5.lua": "Premake",
                "sconstruct": "SCons", "platformio.ini": "PlatformIO"}
_FINDINGS = (
    ("graphics", "desktop-opengl", re.compile(r"\b(glBegin|glEnd|glDrawArrays|glDrawElements|glBindTexture|glfwInit|SDL_GL_CreateContext|glCreateShader)\s*\("),
     "Desktop OpenGL/GLFW interface; evaluate a Citro3D renderer adapter and GPU feature mapping."),
    ("graphics", "direct3d", re.compile(r"\b(D3D11CreateDevice|Direct3DCreate9|D3DCompile|ID3D11Device|IDXGISwapChain)\b"),
     "Direct3D interface; identify the draw/state API boundary before writing a native backend."),
    ("graphics", "vulkan", re.compile(r"\b(vkCreateInstance|vkCreateDevice|vkQueueSubmit|VkDevice)\b"),
     "Vulkan interface; inventory used operations and test feasibility of a different renderer."),
    ("audio", "desktop-audio", re.compile(r"\b(alGenSources|alcOpenDevice|Mix_OpenAudio|FMOD_System_Create|XAudio2Create|DirectSoundCreate)\s*\("),
     "Desktop audio backend; map channels, streaming, callbacks, and ownership to a 3DS-compatible backend."),
    ("input", "desktop-input", re.compile(r"\b(SDL_PollEvent|SDL_GetKeyboardState|GetAsyncKeyState|XInputGetState|glfwGetKey)\s*\("),
     "Desktop input interface; map required actions and verify Old/New 3DS controller coverage."),
    ("threading", "threading-api", re.compile(r"\b(pthread_create|CreateThread|_beginthreadex|std::thread)\b"),
     "Threading dependency; review scheduling, synchronization, stack sizes and runtime service availability."),
    ("filesystem", "platform-file-io", re.compile(r"\b(CreateFile[AW]|GetModuleFileName[AW]|SHGetFolderPath[AW]|GetCurrentDirectory[AW])\s*\("),
     "Desktop filesystem service; design a scoped SD/RomFS adapter and test paths and saving."),
    ("portability", "unaligned-cast-review", re.compile(r"\*\s*\(\s*(?:const\s+)?(?:float|double|u(?:int)?(?:16|32|64)_t|int(?:16|32|64)_t)\s*\*\s*\)\s*\("),
     "Possible unaligned type-pun; inspect binary parser accesses for ARM alignment and aliasing."),
    ("platform", "windows-header", re.compile(r"^\s*#\s*include\s*[<\"](?:windows\.h|d3d9\.h|d3d11\.h|dsound\.h|xinput\.h)[>\"]", re.I),
     "Windows-only header; isolate platform compilation units and provide native alternatives."),
)
_MAIN = re.compile(r"\b(?:int|void|auto)\s+(?:main|WinMain|SDL_main)\s*\(")
_LOOP = re.compile(r"\b(?:while|for)\s*\([^;\n]{0,120}(?:running|gameRunning|quit|QuitRequested|is_running)[^;\n]{0,120}\)")
_INCLUDE = re.compile(r'^\s*#\s*include\s*"([^"\r\n]+)"')
_MAX_FINDINGS = 120
_MAX_SOURCE_FILES = 4000
_MAX_FILE_BYTES = 1_048_576


def _iter_files(root: Path, limit: int):
    """Stable traversal without following directory symlinks or build trees."""
    count = 0
    for directory, dirs, files in os.walk(root, topdown=True, followlinks=False):
        here = Path(directory)
        dirs[:] = sorted(d for d in dirs if d not in _SKIP and
                         not (here / d).is_symlink())
        for filename in sorted(files):
            candidate = here / filename
            if candidate.is_symlink() or not candidate.is_file():
                continue
            count += 1
            if count > limit:
                raise ValueError("Project file limit exceeded; narrow the source tree")
            yield candidate


def inspect_source_project(directory: Path, *, target: str = "old3ds",
                           max_files: int = 2500) -> dict:
    """Safely inspect source; never runs build scripts or modifies source files."""
    if target not in ("old3ds", "new3ds"):
        raise ValueError("Target must be old3ds or new3ds")
    if not 1 <= max_files <= _MAX_SOURCE_FILES:
        raise ValueError("max_files must be between 1 and 4000")
    path = Path(directory)
    if path.is_symlink():
        raise ValueError("Symbolic-link source roots are forbidden")
    root = path.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("A source directory is required")

    sources, skipped, findings, build_systems, licenses, entrypoints, loops = (
        [], [], [], [], [], [], [])
    suffix_counts = Counter()
    includes = Counter()
    inspected_bytes = 0
    for file in _iter_files(root, max_files):
        rel = file.relative_to(root).as_posix()
        lower = file.name.lower()
        if lower in _BUILD_FILES:
            build_systems.append({"path": rel, "system": _BUILD_FILES[lower]})
        elif file.suffix.lower() in (".sln", ".vcxproj", ".vcproj"):
            build_systems.append({"path": rel, "system": "Visual Studio"})
        if lower in ("license", "license.md", "license.txt", "copying", "copying.md"):
            licenses.append(rel)
        ext = file.suffix.lower()
        if ext not in _SOURCE_SUFFIXES | _ASM_SUFFIXES:
            continue
        size = file.stat().st_size
        if size > _MAX_FILE_BYTES:
            skipped.append({"path": rel, "reason": "source file exceeds 1 MiB inspection cap"})
            continue
        raw = file.read_bytes()
        if b"\0" in raw:
            skipped.append({"path": rel, "reason": "binary data in source candidate"})
            continue
        content = raw.decode("utf-8", errors="replace")
        inspected_bytes += len(raw)
        suffix_counts[ext] += 1
        sources.append({"path": rel, "bytes": len(raw),
                        "sha256": hashlib.sha256(raw).hexdigest()})
        if ext in _ASM_SUFFIXES:
            if len(findings) < _MAX_FINDINGS:
                findings.append({"path": rel, "line": 1, "subsystem": "portability",
                                 "symbol": "assembly", "classification": "requires-engineering",
                                 "evidence": "Assembly source file",
                                 "next_action": "Identify ISA/ABI and replace or port incompatible assembly."})
            continue
        for line_number, line in enumerate(content.splitlines(), 1):
            if not line.strip():
                continue
            local = _INCLUDE.match(line)
            if local:
                includes[local.group(1)] += 1
            if _MAIN.search(line) and len(entrypoints) < 24:
                entrypoints.append({"path": rel, "line": line_number,
                                    "status": "signature candidate; requires review"})
            if _LOOP.search(line) and len(loops) < 24:
                loops.append({"path": rel, "line": line_number,
                              "status": "game-loop candidate; requires review"})
            if len(findings) >= _MAX_FINDINGS:
                continue
            for subsystem, symbol, pattern, action in _FINDINGS:
                if pattern.search(line):
                    findings.append({"path": rel, "line": line_number,
                                     "subsystem": subsystem, "symbol": symbol,
                                     "classification": "requires-engineering",
                                     "evidence": line.strip()[:180], "next_action": action})
                    if len(findings) >= _MAX_FINDINGS:
                        break
    summary = dict(sorted(Counter(item["subsystem"] for item in findings).items()))
    tasks = []
    for subsystem in summary:
        tasks.append({
            "subsystem": subsystem,
            "action": "Inspect listed source locations, select or implement a native adapter, "
                      "preserve behavior and add a targeted build/runtime test.",
            "validation": "Host comparison plus real devkitARM build; emulator/hardware checks separately",
        })
    if not sources:
        tasks.append({"subsystem": "source", "action": "Provide a supported C/C++ source tree",
                      "validation": "Source files available for inspection"})
    return {
        "schema_version": 1, "target": target,
        "scope": "read-only source evidence; no code execution or portability guarantee",
        "status": "inspection-completed" if sources else "no-source-found",
        "source_files": sources, "source_counts": dict(sorted(suffix_counts.items())),
        "source_bytes_inspected": inspected_bytes, "skipped_sources": skipped,
        "build_systems": build_systems, "license_file_candidates": licenses,
        "license_status": "not-reviewed; presence of a file is not permission",
        "entrypoint_candidates": entrypoints, "game_loop_candidates": loops,
        "quoted_local_includes": dict(includes.most_common(50)),
        "findings": findings, "findings_truncated": len(findings) >= _MAX_FINDINGS,
        "findings_by_subsystem": summary, "engineering_tasks": tasks,
        "verification": {"source_inspection": True, "native_build": False,
                         "emulator_execution": False, "gameplay": False},
    }


def main(argv: list[str] | None = None) -> int:
    """Standalone entry point for use before native toolchains are available."""
    import argparse
    import json
    parser = argparse.ArgumentParser(description="Read-only C/C++ 3DS porting source audit")
    parser.add_argument("directory")
    parser.add_argument("--target", choices=("old3ds", "new3ds"), default="old3ds")
    parser.add_argument("--max-files", type=int, default=2500)
    args = parser.parse_args(argv)
    try:
        report = inspect_source_project(Path(args.directory),
                                        target=args.target, max_files=args.max_files)
    except (OSError, ValueError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}))
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
