"""Read-only file inventory with bounded identification and SHA-256."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

SIGNATURES = [
    (b"NUP\x01", "nup-v1-unverified"),
    (b"\x7fELF", "elf"), (b"MZ", "pe-candidate"),
    (b"\x89PNG\r\n\x1a\n", "png"), (b"\xff\xd8\xff", "jpeg"),
    (b"GIF87a", "gif"), (b"GIF89a", "gif"),
    (b"PK\x03\x04", "zip-container"), (b"RIFF", "riff-container"),
    (b"OggS", "ogg"), (b"fLaC", "flac"),
]
SUFFIXES = {
    ".3dsx": "3dsx-unverified", ".cia": "cia-unverified", ".cxi": "cxi-unverified",
    ".3ds": "3ds-unverified", ".nup": "nup-unverified",
    ".gltf": "gltf-json-unverified", ".glb": "glb-unverified",
    ".wav": "wave-unverified", ".mp3": "mp3-unverified",
    ".obj": "wavefront-obj-unverified", ".fbx": "fbx-unverified",
    ".exe": "exe-unverified", ".so": "shared-library-unverified",
    ".c": "c-source", ".cpp": "cpp-source", ".h": "c-header",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify(path: Path) -> str:
    with path.open("rb") as stream:
        head = stream.read(32)
    for signature, kind in SIGNATURES:
        if head.startswith(signature):
            if kind == "riff-container" and head[8:12] == b"WAVE":
                return "wav"
            return kind
    if head.startswith(b"glTF"):
        return "glb"
    if head[:4] == b"3DSX":
        return "3dsx"
    return SUFFIXES.get(path.suffix.lower(), "unknown")


def inventory(root: Path, *, max_files: int = 5000) -> dict:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"Not a directory: {root}")
    records: list[dict] = []
    skipped = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            skipped.append({"path": path.relative_to(root).as_posix(), "reason": "symlink"})
            continue
        if not path.is_file():
            continue
        if len(records) >= max_files:
            raise ValueError(f"File limit exceeded ({max_files}); use a smaller isolated directory")
        try:
            stat = path.stat()
            records.append({"path": path.relative_to(root).as_posix(), "size": stat.st_size,
                            "format": classify(path), "sha256": sha256(path)})
        except (PermissionError, OSError) as exc:
            skipped.append({"path": path.relative_to(root).as_posix(), "reason": str(exc)})
    return {"schema_version": 1, "source_directory": str(root), "file_count": len(records),
            "total_bytes": sum(entry["size"] for entry in records),
            "files": records, "skipped": skipped,
            "notice": "Classification identifies signatures/extension only; it does not decode encrypted or proprietary containers."}


def write_json(destination: Path, data: dict) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
