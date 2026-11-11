"""Evidence-gated import of real C/C++ game source projects.

No execution of imported build files, unknown plugins or game binaries occurs.
The original tree is immutable. A game-specific adapter can only patch a
narrow, audited source expression and must write a reviewable unified diff.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

SCHEMA = 1
MAX_FILES = 15000
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 384 * 1024 * 1024
SKIP_DIRS = {".git", ".hg", ".svn", "__pycache__", ".venv", "build",
             "build-host", "node_modules", "target", ".idea"}
SOURCES = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx"}
BUILD_FILES = {"makefile", "gnumakefile", "cmakelists.txt", "meson.build",
               "configure.ac", "makefile.am", "sconstruct"}
LICENSE_FILES = {"license", "license.txt", "license.md", "copying", "copying.txt"}
RULES = (
    ("SDL2_video", r"\bSDL_(?:Init|CreateWindow|CreateRenderer|RenderPresent)\s*\(",
     "existing-adapter", "Nintendo 3DS SDL2 software video backend; verify API and native portlibs"),
    ("SDL2_accelerated", r"\bSDL_RENDERER_ACCELERATED\b",
     "game-specific-change", "SDL2 Nintendo 3DS supports software rendering; negotiate instead of requesting accelerated only"),
    ("SDL2_image", r"\b(?:IMG_Load|IMG_Init)\s*\(",
     "requires-dependency", "3DS SDL2_image dependency and asset format compatibility must be verified"),
    ("SDL2_mixer", r"\b(?:Mix_OpenAudio|Mix_PlayChannel|Mix_PlayMusic|Mix_LoadMUS)\s*\(",
     "requires-dependency", "3DS SDL2_mixer/audio backend and music/sfx concurrency require native testing"),
    ("SDL2_ttf", r"\b(?:TTF_Init|TTF_OpenFont)\s*\(",
     "requires-dependency", "3DS SDL2_ttf/font resources need resolution and testing"),
    ("OpenGL", r"\b(?:glBegin|glDrawArrays|glDrawElements|SDL_GL_CreateContext)\s*\(",
     "new-adapter", "Desktop OpenGL cannot run unchanged on PICA200"),
    ("Direct3D", r"\b(?:D3D11CreateDevice|Direct3DCreate9)\s*\(",
     "new-adapter", "Desktop Direct3D requires target-specific renderer replacement"),
    ("POSIX_user_home", r"\b(?:getpwuid|getpwnam|geteuid)\s*\(",
     "game-specific-change", "3DS uses explicit app-specific SD path and safe save handling"),
    ("POSIX_process", r"\b(?:fork|execve|popen)\s*\(",
     "unsupported", "OS process creation cannot be assumed on 3DS homebrew"),
    ("pthreads", r"\b(?:pthread_create|pthread_join)\s*\(",
     "requires-investigation", "3DS threading and shared resource lifetimes require explicit audit"),
    ("native_windows", r"\b(?:GetModuleHandle|CreateFileW|CreateWindowExW)\s*\(",
     "new-adapter", "Windows-only system APIs require platform replacement"),
    ("filesystem_io", r"\b(?:fopen|open|stat|rename|remove)\s*\(",
     "requires-investigation", "Audit RomFS read-only resources versus writable private save paths"),
    ("game_loop", r"\b(?:SDL_PollEvent|SDL_WaitEvent|aptMainLoop)\s*\(",
     "source-evidence", "Actual event loop candidate; verify game simulation call graph"),
    ("timing", r"\b(?:SDL_GetTicks|SDL_Delay|clock_gettime)\s*\(",
     "requires-investigation", "Review fixed-step update, frame sync and time units"),
)
RULE_DICT = {r[0]: r for r in RULES}
SOURCE_RE = re.compile(r'^\s*#\s*include\s*["<]([^">]+)[">]', re.MULTILINE)
MAIN_RE = re.compile(r"\b(?:int|auto)\s+main\s*\(")


class PortError(ValueError):
    pass


def _bounded_tree(root: Path, *, include_assets: bool = True) -> list[tuple[str, Path, int]]:
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise PortError("Game source root must be an existing directory")
    found: list[tuple[str, Path, int]] = []
    total = 0
    for folder, dirs, files in os.walk(root, topdown=True, followlinks=False):
        parent = Path(folder)
        for d in dirs:
            if (parent / d).is_symlink():
                raise PortError("Symbolic-link directory forbidden: " + str(parent / d))
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(files):
            path = parent / name
            if path.is_symlink() or not path.is_file():
                raise PortError("Symbolic-link or nonregular file forbidden: " + str(path))
            rel = path.relative_to(root).as_posix()
            is_source = (path.suffix.lower() in SOURCES or
                         path.name.lower() in BUILD_FILES | LICENSE_FILES or
                         path.suffix.lower() in {".cmake", ".s", ".asm"})
            if not include_assets and not is_source:
                continue
            size = path.stat().st_size
            if size > MAX_FILE_BYTES:
                raise PortError(f"Oversized input file ({size} bytes): {rel}")
            total += size
            if total > MAX_TOTAL_BYTES:
                raise PortError("Project exceeds 384 MiB import budget; reduce scope")
            found.append((rel, path, size))
            if len(found) > MAX_FILES:
                raise PortError("Project exceeds 15000 files; reduce scope")
    if not found:
        raise PortError("No source files found")
    return found


def _digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            result.update(chunk)
    return result.hexdigest()


def _source_text(path: Path, size: int) -> str:
    if size > 2_000_000:
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _license(paths: dict[str, Path]) -> dict:
    candidates = [name for name in paths
                  if Path(name).name.lower() in LICENSE_FILES]
    evidence = []
    for path in sorted(candidates)[:8]:
        p = paths[path]
        if p.stat().st_size > 131072:
            continue
        data = p.read_text(encoding="utf-8", errors="replace")
        family = "unknown"
        if "GNU GENERAL PUBLIC LICENSE" in data.upper():
            family = "GPL family; inspect exact version and assets"
        elif "MIT LICENSE" in data.upper() or "Permission is hereby granted, free of charge" in data:
            family = "MIT evidence"
        elif "BSD" in data.upper():
            family = "BSD family evidence"
        evidence.append({"file": path, "family": family})
    return {"detected": bool(evidence), "files": evidence,
            "verified_rights": False,
            "note": "Static text evidence only. Inspect each source and asset license."}


def inspect_source(root: str | Path) -> dict:
    root = Path(root).resolve(strict=True)
    entries = _bounded_tree(root)
    paths = {rel: path for rel, path, _ in entries}
    src = [(rel, p, size) for rel, p, size in entries if p.suffix.lower() in SOURCES]
    if not src:
        raise PortError("No C/C++ source or headers detected")
    build = sorted(rel for rel in paths if Path(rel).name.lower() in BUILD_FILES)
    includes = []
    findings = []
    entrypoints = []
    languages = sorted({"C++" if p.suffix.lower() in {".cc", ".cpp", ".cxx", ".hpp", ".hh", ".hxx"}
                        else "C" for _, p, _ in src})
    for rel, p, size in src:
        code = _source_text(p, size)
        if not code:
            findings.append({"file": rel, "line": 0, "symbol": "oversized-source",
                             "category": "requires-investigation",
                             "action": "Source exceeds 2 MB scan bound; inspect manually"})
            continue
        if MAIN_RE.search(code):
            entrypoints.append(rel)
        for line_no, line in enumerate(code.splitlines(), 1):
            inc = SOURCE_RE.match(line)
            if inc and len(includes) < 20000:
                include = inc.group(1)
                if len(include) <= 240:
                    includes.append({"file": rel, "line": line_no, "include": include})
            # Never claim syntax-level certainty: these are static token observations.
            if line.lstrip().startswith(("/*", "*", "//")):
                continue
            for name, pattern, category, action in RULES:
                if re.search(pattern, line) and len(findings) < 2500:
                    findings.append({"file": rel, "line": line_no,
                                     "symbol": name, "category": category,
                                     "action": action})
    known = set(paths)
    graph = []
    for inc in includes:
        frm, name = inc["file"], inc["include"]
        candidate = (Path(frm).parent / name).as_posix()
        if candidate in known:
            graph.append({"file": frm, "include": name, "resolved": candidate})
        elif name in known:
            graph.append({"file": frm, "include": name, "resolved": name})
    stats = {"file_count": len(entries),
             "source_files": len(src),
             "total_bytes": sum(e[2] for e in entries)}
    return {
        "schema_version": SCHEMA, "source_root": str(root),
        "status": "STATIC_INSPECTED_NOT_PORTED",
        "files": stats, "languages": languages, "build_systems": build,
        "entrypoint_candidates": sorted(entrypoints),
        "dependency_graph": graph[:8000],
        "includes": includes[:8000],
        "findings": findings,
        "rule_summary": {name: sum(f["symbol"] == name for f in findings)
                         for name, *_ in RULES if any(f["symbol"] == name for f in findings)},
        "license": _license(paths),
        "verified_native_build": False,
        "verified_gameplay": False,
        "limits": ["Static patterns are candidates, not proof of linked dependencies",
                   "No untrusted scripts/executables were executed",
                   "No engine support or gameplay compatibility inferred by filename"]
    }


def _edgar_patch(file: str, before: str) -> tuple[str, list[str]]:
    if file != "src/init.c":
        return before, []
    if ("Parallel Realities" not in before or
            "void init(" not in before or
            "rendererFlags = SDL_RENDERER_ACCELERATED;" not in before):
        raise PortError("Requested Edgar adapter does not match original src/init.c")
    needle = "\trendererFlags = SDL_RENDERER_ACCELERATED;"
    if before.count(needle) != 1:
        raise PortError("Edgar renderer expression changed; manual review required")
    after = before.replace(
        needle,
        "\t/* PocketPort: 3DS SDL2 has software rendering only. */\n"
        "\t#if defined(__3DS__)\n"
        "\t\trendererFlags = SDL_RENDERER_SOFTWARE;\n"
        "\t#else\n"
        "\t\trendererFlags = SDL_RENDERER_ACCELERATED;\n"
        "\t#endif",
        1
    )
    return after, ["src/init.c: SDL renderer selection guarded by __3DS__"]


def port_project(root: str | Path, output: str | Path, *, target: str = "new3ds",
                 adapter: str = "none", copy_assets: bool = False) -> dict:
    if target not in ("old3ds", "new3ds"):
        raise PortError("Target must be old3ds or new3ds")
    if adapter not in ("none", "edgar-sdl2"):
        raise PortError("Unknown adapter; game-specific adapters must be explicitly selected")
    source = Path(root).resolve(strict=True)
    output = Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise PortError("Output exists: never overwrite an existing port workspace")
    parent = output.parent.resolve(strict=True)
    if source == parent or source in parent.parents or parent == source:
        raise PortError("Destination cannot live inside source project")
    if output == source or output in source.parents:
        raise PortError("Destination must be separate from imported source")
    report = inspect_source(source)
    if adapter == "edgar-sdl2":
        marker = source / "src" / "init.c"
        if not marker.is_file():
            raise PortError("Edgar adapter needs src/init.c")
        _edgar_patch("src/init.c", marker.read_text(encoding="utf-8"))
    files = _bounded_tree(source, include_assets=copy_assets)
    changes, checksum = [], []
    with tempfile.TemporaryDirectory(prefix=".pp-port-", dir=parent) as temporary:
        staged = Path(temporary)
        copied = staged / "source"
        copied.mkdir()
        for rel, original, _ in files:
            destination = copied / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            if adapter == "edgar-sdl2" and rel == "src/init.c":
                previous = original.read_text(encoding="utf-8")
                revised, actions = _edgar_patch(rel, previous)
                destination.write_text(revised, encoding="utf-8")
                patch = "".join(difflib.unified_diff(
                    previous.splitlines(True), revised.splitlines(True),
                    fromfile="a/" + rel, tofile="b/" + rel))
                changes.append({"path": rel, "adapter": adapter,
                                "source_sha256": _digest(original),
                                "adapted_sha256": _digest(destination),
                                "actions": actions,
                                "unified_diff": patch})
            else:
                shutil.copyfile(original, destination)
            checksum.append({"path": rel, "source_sha256": _digest(original),
                             "output_sha256": _digest(destination)})
        blockers = list(report["findings"])
        retained = [f for f in blockers if f["category"] != "source-evidence"]
        if adapter == "edgar-sdl2":
            retained = [f for f in retained if
                        not (f["symbol"] == "SDL2_accelerated"
                             and f["file"] == "src/init.c")]
        manifest = {
            "schema_version": SCHEMA, "target": target, "adapter": adapter,
            "original_root": str(source),
            "source_fingerprint": hashlib.sha256(
                "".join(x["path"]+x["source_sha256"] for x in checksum).encode()).hexdigest(),
            "asset_copy": copy_assets, "files": checksum,
            "patches": changes,
            "compatibility": {"entrypoint_candidates": report["entrypoint_candidates"],
                              "languages": report["languages"],
                              "build_systems": report["build_systems"],
                              "open_findings": retained[:1000]},
            "status": "SOURCE_ADAPTED_NOT_NATIVE_COMPILED",
            "next_steps": ["Resolve missing target dependencies and all mandatory controls",
                           "Integrate native 3DS SDL2 or renderer backend",
                           "Cross-compile source game's actual entrypoint and game loops",
                           "Test title, levels, enemy AI, audio, save/load and exit in emulator",
                           "Preserve upstream gameplay and license notices"]
        }
        (staged / "port.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (staged / "review.patch").write_text(
            "".join(item["unified_diff"] for item in changes), encoding="utf-8")
        (staged / "inspection.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(staged, output)
    return {"workspace": str(output), "target": target,
            "files_copied": len(files), "assets_copied": copy_assets,
            "patches": len(changes), "remaining_findings": len(retained),
            "status": "SOURCE_ADAPTED_NOT_NATIVE_COMPILED",
            "manifest": str(output / "port.json"),
            "note": "Original game logic retained, source not run or cross-compiled"}


def verify_port(workspace: str | Path) -> dict:
    workspace = Path(workspace).resolve(strict=True)
    file = workspace / "port.json"
    if not file.is_file() or file.is_symlink() or file.stat().st_size > 4_000_000:
        raise PortError("Invalid/oversized port manifest")
    data = json.loads(file.read_text(encoding="utf-8"))
    if data.get("schema_version") != SCHEMA or not isinstance(data.get("files"), list):
        raise PortError("Unsupported or malformed port manifest")
    files = data["files"]
    if len(files) > MAX_FILES:
        raise PortError("Manifest file count exceeds import budget")
    checked = set()
    for record in files:
        name = record.get("path") if isinstance(record, dict) else None
        if not isinstance(name, str) or not name or name in checked or "\\" in name:
            raise PortError("Invalid/duplicate source path in manifest")
        p = Path(name)
        if p.is_absolute() or ".." in p.parts or "." in p.parts:
            raise PortError("Unsafe resource path in manifest")
        checked.add(name)
        destination = workspace / "source" / p
        if not destination.is_file() or destination.is_symlink() or _digest(destination) != record.get("output_sha256"):
            raise PortError("Missing, symlinked, modified or corrupted adapted file: " + name)
    return {"verified_files": len(checked), "sha256_verified": True,
            "native_compiled": False, "gameplay_tested": False,
            "status": "INTEGRITY_VERIFIED_NO_EXECUTION"}
