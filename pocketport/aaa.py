"""Bounded, read-only AAA game engine evidence and executable identity.
All matches are investigation candidates, NEVER verified 3DS ports.
"""
from __future__ import annotations
import json
import struct
from pathlib import Path

MAX_HEADER = 4096
MAX_FILES = 5000

def _head(path: Path) -> bytes:
    with path.open("rb") as f:
        return f.read(MAX_HEADER)

def inspect_executable(path: Path) -> dict:
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        raise ValueError("Executable must be an existing non-symlink file")
    data = _head(path)
    base = {"format": "unknown", "architecture": "unknown",
            "scope": "header only; no execution, imports or ABI validation"}
    if data.startswith(b"\x7fELF"):
        if len(data) < 52 or data[4] not in (1, 2) or data[5] not in (1, 2):
            raise ValueError("Invalid ELF identification")
        bits = 32 if data[4] == 1 else 64
        if len(data) < (52 if bits == 32 else 64):
            raise ValueError("Truncated ELF header")
        order = "little" if data[5] == 1 else "big"
        prefix = "<" if order == "little" else ">"
        machine = struct.unpack_from(prefix + "H", data, 18)[0]
        entry = struct.unpack_from(prefix + ("I" if bits == 32 else "Q"), data, 24)[0]
        return {**base, "format": "ELF", "bits": bits, "endianness": order,
                "machine_id": machine, "entry_address": entry,
                "architecture": {3: "x86", 8: "MIPS", 40: "ARM32",
                                 62: "x86-64", 183: "ARM64"}.get(machine, "unknown")}
    if data.startswith(b"MZ"):
        if len(data) < 0x40:
            raise ValueError("Truncated DOS header")
        offset = struct.unpack_from("<I", data, 0x3c)[0]
        if offset > len(data) - 24 or data[offset:offset + 4] != b"PE\0\0":
            return {**base, "format": "MZ (PE signature not verified)"}
        machine, sections = struct.unpack_from("<HH", data, offset + 4)
        opt_bytes = struct.unpack_from("<H", data, offset + 20)[0]
        opt = offset + 24
        if opt + opt_bytes > len(data) or opt_bytes < 20:
            raise ValueError("Truncated PE optional header")
        magic = struct.unpack_from("<H", data, opt)[0]
        if magic not in (0x10b, 0x20b):
            raise ValueError("Unsupported PE optional header")
        entry = struct.unpack_from("<I", data, opt + 16)[0]
        return {**base, "format": "PE", "bits": 32 if magic == 0x10b else 64,
                "endianness": "little", "machine_id": machine, "sections": sections,
                "entry_rva": entry,
                "architecture": {0x14c: "x86", 0x8664: "x86-64", 0x1c0: "ARM32",
                                 0xaa64: "ARM64"}.get(machine, "unknown")}
    return base

def detect_engine(directory: Path, *, max_files: int = MAX_FILES) -> dict:
    root = Path(directory).resolve()
    if not root.is_dir() or max_files < 1:
        raise ValueError("Expected a directory and a positive file limit")
    seen = []
    skipped = 0
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            skipped += 1
            continue
        if not path.is_file():
            continue
        if len(seen) >= max_files:
            raise ValueError(f"File limit exceeded ({max_files})")
        try:
            rel = path.relative_to(root).as_posix().casefold()
            seen.append((rel, _head(path)))
        except OSError:
            skipped += 1
    names = {Path(rel).name for rel, _ in seen}
    matches = []
    def add(name, clues):
        if clues:
            matches.append({"engine_candidate": name, "evidence": sorted(set(clues)),
                            "evidence_count": len(set(clues)),
                            "status": "candidate; game and port compatibility unverified"})
    if "unityplayer.dll" in names and "gameassembly.dll" in names:
        add("Unity IL2CPP", ["UnityPlayer.dll present", "GameAssembly.dll present"])
    elif "unityplayer.dll" in names and "assembly-csharp.dll" in names:
        add("Unity Mono", ["UnityPlayer.dll present", "Assembly-CSharp.dll present"])
    utoc = [p for p, _ in seen if p.endswith(".utoc")]
    ucas = [p for p, _ in seen if p.endswith(".ucas")]
    if utoc and ucas and any("/paks/" in "/" + p for p in utoc + ucas):
        add("Unreal Engine 4/5", [".utoc in Paks directory", ".ucas companion present"])
    upks = [p for p, h in seen if p.endswith(".upk") and h.startswith(b"\xc1\x83\x2a\x9e")]
    if len(upks) >= 2:
        add("Unreal Engine 3", ["two or more verified UPK package headers"])
    if (any(p.endswith(".bsa") and h.startswith(b"BSA\0") for p, h in seen)
            and any(p.endswith(".esm") and h.startswith(b"TES4") for p, h in seen)):
        add("Bethesda Gamebryo / Creation", ["BSA archive header", "TES4 plugin header"])
    rw = any(p.endswith(".txd") and len(h) >= 12
             and struct.unpack_from("<I", h)[0] == 0x16 for p, h in seen)
    img = any(p.endswith(".img") and h[:4] in (b"VER2", b"VER3") for p, h in seen)
    if rw and img:
        add("RenderWare-era GTA candidate", ["TXD chunk signature", "IMG archive signature"])
    if any(h[:4] in (b"RPF7", b"RPF8") for _, h in seen):
        add("RAGE family", ["RPF header signature"])
    if any(h.startswith(b"CR2W") for _, h in seen):
        add("REDengine asset family", ["CR2W asset header"])
    if (any(p.endswith(".bsp") and h.startswith(b"IBSP") for p, h in seen)
        and any(p.endswith(".pk3") and h.startswith(b"PK\x03\x04") for p, h in seen)):
        add("id Tech 3 family", ["IBSP map header", "PK3 ZIP archive header"])
    matches.sort(key=lambda x: (-x["evidence_count"], x["engine_candidate"]))
    return {"directory": str(root), "scanned_files": len(seen), "skipped": skipped,
            "engine": matches[0]["engine_candidate"] if len(matches) == 1 else "unknown",
            "candidates": matches,
            "warning": "Signatures are candidates only, not proof of a native 3DS game."}

CATALOGUE = Path(__file__).resolve().parent.parent / "knowledge" / "aaa_targets.json"

def research_game(title: str) -> dict:
    if not title.strip():
        raise ValueError("Game title must not be blank")
    key = " ".join(title.casefold().split())
    entries = json.loads(CATALOGUE.read_text(encoding="utf-8"))["games"]
    for item in entries:
        if key in {" ".join(s.casefold().split()) for s in [item["game"], *item.get("aliases", [])]}:
            return {**item, "status": "research-only",
                    "discovery_scope": "curated offline references; no network search performed"}
    return {"game": title, "status": "unknown", "known_ports": [], "sources": [],
            "discovery_scope": "no offline match; network not searched",
            "next_action": "Verify exact build, engine and available sources"}

def compatibility(directory: Path, target: str = "new3ds",
                  *, available_application_bytes: int | None = None) -> dict:
    if target not in ("old3ds", "new3ds"):
        raise ValueError("Target must be old3ds or new3ds")
    engine = detect_engine(directory)
    disk = sum(p.stat().st_size for p in Path(directory).rglob("*")
               if p.is_file() and not p.is_symlink())
    if available_application_bytes is not None and available_application_bytes <= 0:
        raise ValueError("Process memory budget must be positive")
    return {"target": target, "engine_detection": engine, "on_disk_bytes": disk,
            "application_memory_bytes": available_application_bytes,
            "memory_status": ("user-measured budget supplied" if available_application_bytes
                              else "unknown; hardware probe required"),
            "feasibility": "unverified", "route": "research-first",
            "warning": "Disk size is not resident RAM or game compatibility."}
