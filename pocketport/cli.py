"""PocketPort command-line interface: observed work, never fake conversion."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

from .aaa import compatibility, detect_engine, inspect_executable, research_game
from .discovery import search_repositories
from .assets import PROFILES, optimize
from .build import build_project, manifest_path, report_project, test_project
from .environment import doctor
from .demo import run_original_demo
from .inventory import inventory, sha256, write_json
from .nup import inspect_nup, NupError
from .skyrim.bsa import inspect_bsa, BSAError
from .skyrim.tes5 import inspect_plugin, TES5Error
from .skyrim.dds import convert_dds, DDSError
from .skyrim.scene import convert_plugin, read_scene, SceneError
from .skyrim.nif import convert_nif, decode_mesh, NIFError
from .skyrim.converter import convert_game, ConversionError
from .skyrim.fixture import generate as generate_fixture
from .skyrim.texture_gpu import convert_t3x, DDSError as GPUDDSError
from .planning import choose
from .translation import parse, verify_host, write_c

ROOT = Path(__file__).resolve().parent.parent


def _project_source(args: argparse.Namespace) -> tuple[Path, dict]:
    p = Path(args.manifest)
    return manifest_path(p)


def run(args: argparse.Namespace) -> dict:
    if args.cmd == "doctor":
        return doctor()
    if args.cmd == "detect-engine":
        return detect_engine(Path(args.directory), max_files=args.max_files)
    if args.cmd == "inspect-executable":
        return inspect_executable(Path(args.file))
    if args.cmd == "research":
        return research_game(args.game)
    if args.cmd == "discover-ports":
        if args.live:
            return search_repositories(args.game, limit=args.limit)
        entry = research_game(args.game)
        return {"game": entry["game"], "status": entry["status"],
                "known_ports": entry.get("known_ports", []),
                "sources": entry.get("sources", []),
                "discovery_scope": entry["discovery_scope"]}
    if args.cmd == "compatibility":
        return compatibility(Path(args.directory), args.target,
                             available_application_bytes=args.application_bytes)
    if args.cmd == "demo":
        return run_original_demo(Path(args.out))
    if args.cmd == "inspect-nup":
        return inspect_nup(Path(args.file))
    if args.cmd == "skyrim-inspect-bsa":
        return inspect_bsa(Path(args.file))
    if args.cmd == "skyrim-inspect-plugin":
        return inspect_plugin(Path(args.file))
    if args.cmd == "skyrim-convert-dds":
        return convert_dds(Path(args.file), Path(args.out))
    if args.cmd == "skyrim-convert-scene":
        return convert_plugin(Path(args.file), Path(args.out),
                              cell_id=(int(args.cell_id, 0) if args.cell_id else None))
    if args.cmd == "skyrim":
        if args.skyrim_cmd == "test-scene":
            return generate_fixture(Path(args.output))
        if args.skyrim_cmd == "convert":
            return convert_game(Path(args.game_dir), Path(args.output),
                                cell_id=int(args.cell, 0),
                                max_instances=args.max_instances,
                                triangle_limit=args.triangle_limit)
        raise ValueError("Unknown Skyrim subcommand")
    if args.cmd == "skyrim-convert-texture":
        return convert_t3x(Path(args.file), Path(args.out), max_dimension=args.max_dimension)
    if args.cmd == "skyrim-convert-nif":
        return convert_nif(Path(args.file), Path(args.out))
    if args.cmd == "skyrim-validate-mesh":
        p = Path(args.file)
        if p.is_symlink() or not p.is_file() or p.stat().st_size > 300000:
            raise NIFError("Invalid or oversized PPMG mesh")
        mesh = decode_mesh(p.read_bytes())
        return {"status":"valid","vertices":len(mesh.vertices),
                "triangles":len(mesh.triangles)}
    if args.cmd == "skyrim-validate-scene":
        path = Path(args.file)
        if path.is_symlink() or path.stat().st_size > 50000:
            raise ValueError("Scene file invalid or exceeds 50 KB cap")
        return {"status": "valid", "scene": read_scene(path.read_bytes())}
    if args.cmd == "hash":
        p = Path(args.file)
        if not p.is_file() or p.is_symlink():
            raise ValueError(f"Missing or symlinked regular file: {p}")
        return {"path": str(p.resolve()), "sha256": sha256(p), "bytes": p.stat().st_size}
    if args.cmd == "inspect":
        data = inventory(Path(args.directory), max_files=args.max_files)
        if args.out:
            write_json(Path(args.out), data)
        return data
    if args.cmd == "manifest":
        data = inventory(Path(args.directory), max_files=args.max_files)
        data["game"] = args.game
        data["target"] = args.target
        write_json(Path(args.out), data)
        return {"manifest": str(Path(args.out).resolve()), "file_count": data["file_count"], "sha256": sha256(Path(args.out))}
    if args.cmd == "init":
        dest = Path(args.directory).resolve()
        if dest.exists() and any(dest.iterdir()):
            raise ValueError("Destination is not empty. Refusing to overwrite user files.")
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "work-private").mkdir(exist_ok=True)
        (dest / "output").mkdir(exist_ok=True)
        (dest / ".gitignore").write_text("work-private/\noutput/\n*.3ds\n*.cia\n*.nup\n*.sav\n", encoding="utf-8")
        doc = {"schema_version": 1, "game": args.game, "target": args.target,
               "asset_root": "work-private", "evidence": {}, "state": "identified-only"}
        write_json(dest / "project.json", doc)
        return {"workspace": str(dest), "manifest": str(dest / "project.json"),
                "note": "Private game files belong in work-private/; no source/game compatibility is assumed."}
    if args.cmd == "plan":
        target = args.target
        if args.evidence:
            evidence_path = Path(args.evidence)
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        else:
            evidence = {}
        result = choose(evidence, target)
        result["investigated_directory"] = str(Path(args.directory).resolve())
        return result
    if args.cmd == "scaffold":
        dest = Path(args.destination)
        if dest.exists() and any(dest.iterdir()):
            raise ValueError("Refusing to overwrite existing scaffold directory")
        shutil.copytree(ROOT / "templates" / "3ds-homebrew", dest, dirs_exist_ok=True)
        return {"destination": str(dest.resolve()), "target": "Nintendo 3DS",
                "status": "source scaffold copied; build NOT executed"}
    if args.cmd == "translate":
        ir = parse(Path(args.program).read_text(encoding="utf-8"))
        header, code = write_c(ir, Path(args.out))
        return {"function": ir.name, "instructions": len(ir.body), "header": str(header),
                "code": str(code), "status": "C source generated; not a machine binary or compiled executable"}
    if args.cmd == "verify-ir":
        program = parse(Path(args.program).read_text(encoding="utf-8"))
        return verify_host(program)
    if args.cmd == "optimize":
        root, doc = _project_source(args)
        if "asset_root" not in doc:
            raise ValueError("Manifest missing asset_root. Source-port project has no image asset pipeline.")
        return optimize(root / doc["asset_root"], Path(args.out), args.profile, args.encode_3ds)
    if args.cmd == "build":
        return build_project(Path(args.manifest), "console" if args.console else "host")
    if args.cmd == "test":
        return test_project(Path(args.manifest), "host" if args.host else "console")
    if args.cmd == "report":
        result = report_project(Path(args.manifest))
        if args.out:
            write_json(Path(args.out), result)
        return result
    raise ValueError(f"Command not implemented: {args.cmd}")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pocketport", description="Evidence-first Nintendo 3DS porting framework")
    commands = p.add_subparsers(dest="cmd", required=True)
    commands.add_parser("doctor", help="Discover installed toolchains without changing your system")
    engine = commands.add_parser("detect-engine", help="Detect read-only engine-family candidates")
    engine.add_argument("directory")
    engine.add_argument("--max-files", type=int, default=5000)
    exe = commands.add_parser("inspect-executable", help="Read-only ELF/PE architecture inspection")
    exe.add_argument("file")
    research = commands.add_parser("research", help="Query curated offline AAA investigation entries")
    research.add_argument("game")
    ports = commands.add_parser("discover-ports", help="Curated or optional public GitHub port discovery")
    ports.add_argument("game")
    ports.add_argument("--live", action="store_true", help="Search public GitHub metadata")
    ports.add_argument("--limit", type=int, default=5)
    comp = commands.add_parser("compatibility", help="Investigate engine evidence and memory gaps")
    comp.add_argument("directory")
    comp.add_argument("--target", choices=("old3ds", "new3ds"), default="new3ds")
    comp.add_argument("--application-bytes", type=int, help="User-measured process application RAM")
    demo = commands.add_parser("demo", help="Exercise integrated original game inspect->plan->translate->optimize->build->test")
    demo.add_argument("--out", required=True)
    nupcmd = commands.add_parser("inspect-nup", help="Read-only authenticated NUP v1 header and package index")
    nupcmd.add_argument("file")
    sk_bsa = commands.add_parser("skyrim-inspect-bsa", help="Skyrim 2011 BSA v104 safe index inspection")
    sk_bsa.add_argument("file")
    sk_esm = commands.add_parser("skyrim-inspect-plugin", help="Limited TES5 STAT/CELL/REFR scanner")
    sk_esm.add_argument("file")
    sk_dds = commands.add_parser("skyrim-convert-dds", help="Convert DXT1 DDS to RGB565 intermediate")
    sk_dds.add_argument("file")
    sk_dds.add_argument("--out", required=True)
    sk_scene = commands.add_parser("skyrim-convert-scene", help="Serialize authentic TES5 static placements to PPSC")
    sk_scene.add_argument("file")
    sk_scene.add_argument("--out", required=True)
    sk_scene.add_argument("--cell-id", help="Cell FormID decimal or 0x hexadecimal")
    skyrim = commands.add_parser("skyrim", help="Skyrim LE/SE local conversion pipeline")
    sk_cmd = skyrim.add_subparsers(dest="skyrim_cmd", required=True)
    sk_fixture = sk_cmd.add_parser("test-scene", help="Original reproducible 3D test scene and SD-card folder")
    sk_fixture.add_argument("--output",required=True)
    sk_convert = sk_cmd.add_parser("convert", help="Convert one authentic cell and static NIF from local Skyrim files")
    sk_convert.add_argument("--game-dir", required=True)
    sk_convert.add_argument("--cell", required=True, help="TES5 cell FormID (decimal or 0xhex)")
    sk_convert.add_argument("--target", choices=("new3ds",), default="new3ds")
    sk_convert.add_argument("--output", required=True)
    sk_convert.add_argument("--max-instances", type=int, default=128)
    sk_convert.add_argument("--triangle-limit", type=int, default=1024)
    sk_tex = commands.add_parser("skyrim-convert-texture", help="Convert BC1/BC3 DDS to PICA200 tex3ds .t3x")
    sk_tex.add_argument("file")
    sk_tex.add_argument("--out", required=True)
    sk_tex.add_argument("--max-dimension",type=int,choices=(32,64,128,256),default=128)
    sk_nif = commands.add_parser("skyrim-convert-nif", help="Convert limited static BSTriShape NIF to PPMG")
    sk_nif.add_argument("file")
    sk_nif.add_argument("--out", required=True)
    sk_mesh = commands.add_parser("skyrim-validate-mesh", help="Validate a PPMG v1 geometry package")
    sk_mesh.add_argument("file")
    sk_verify = commands.add_parser("skyrim-validate-scene", help="Validate PPSC scene package without execution")
    sk_verify.add_argument("file")
    hashcmd = commands.add_parser("hash", help="SHA-256 hash an existing file")
    hashcmd.add_argument("file")
    inspect = commands.add_parser("inspect", help="Read-only file inventory and signature identification")
    inspect.add_argument("directory")
    inspect.add_argument("--max-files", type=int, default=5000)
    inspect.add_argument("--out")
    manifest = commands.add_parser("manifest", help="Write read-only asset inspection manifest with hashes")
    manifest.add_argument("directory")
    manifest.add_argument("--out", required=True)
    manifest.add_argument("--game", default="Unknown game")
    manifest.add_argument("--target", choices=("old3ds", "new3ds"), default="new3ds")
    manifest.add_argument("--max-files", type=int, default=5000)
    init = commands.add_parser("init", help="Create a new isolated game working directory")
    init.add_argument("directory")
    init.add_argument("--game", required=True)
    init.add_argument("--target", choices=("old3ds", "new3ds"), default="new3ds")
    plan = commands.add_parser("plan", help="Route selection gated by independently supplied evidence JSON")
    plan.add_argument("directory")
    plan.add_argument("--target", choices=("old3ds", "new3ds"), default="new3ds")
    plan.add_argument("--evidence", help="JSON with verified, explicit boolean route evidence")
    scaffold = commands.add_parser("scaffold", help="Copy original Nintendo 3DS project without building")
    scaffold.add_argument("destination")
    translate = commands.add_parser("translate", help="Compile PocketPort IR v1 to C99 (NOT arbitrary CPU instructions)")
    translate.add_argument("program")
    translate.add_argument("--out", required=True)
    verify = commands.add_parser("verify-ir", help="Compile generated host C and compare against the IR interpreter")
    verify.add_argument("program")
    optimize_cmd = commands.add_parser("optimize", help="Prepare PNGs; optionally invoke real tex3ds")
    optimize_cmd.add_argument("manifest")
    optimize_cmd.add_argument("--out", required=True)
    optimize_cmd.add_argument("--profile", choices=sorted(PROFILES), default="balanced")
    optimize_cmd.add_argument("--encode-3ds", action="store_true")
    build = commands.add_parser("build", help="Compile original source-port game using host C compiler or devkitARM")
    build.add_argument("manifest")
    target = build.add_mutually_exclusive_group(required=True)
    target.add_argument("--host", action="store_true")
    target.add_argument("--console", action="store_true")
    test = commands.add_parser("test", help="Run deterministic host game regressions; never invent emulator tests")
    test.add_argument("manifest")
    testgroup = test.add_mutually_exclusive_group(required=True)
    testgroup.add_argument("--host", action="store_true")
    testgroup.add_argument("--console", action="store_true")
    report = commands.add_parser("report", help="Make a truthful evidence classification report")
    report.add_argument("manifest")
    report.add_argument("--out")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        data = run(args)
    except (OSError, KeyError, ValueError, RuntimeError, AssertionError,
            BSAError, TES5Error, DDSError, SceneError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2
    print(json.dumps(data, indent=2, sort_keys=True))
    if "returncode" in data and data["returncode"] != 0:
        return 1
    return 0
