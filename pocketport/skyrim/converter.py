"""Host-only, legally supplied Skyrim LE/SE one-static-mesh conversion path.

Resolves TES5 CELL -> REFR -> STAT -> BSA -> BSTriShape. This is a
single-model technical slice; it is not a complete game/environment converter.
Generated packages stay private and are never included in source control.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import struct

from .bsa import BSAArchive, BSAError
from .tes5 import scan_plugin
from .scene import create_scene, read_scene
from .nif import read_nif, encode_mesh, decode_mesh, NIFError


class ConversionError(ValueError):
    pass


def _data_directory(directory: Path) -> Path:
    root = Path(directory)
    if root.is_symlink() or not root.is_dir():
        raise ConversionError("Game installation must be a real directory, not a symlink")
    if (root / "Skyrim.esm").is_file():
        data = root
    elif (root / "Data" / "Skyrim.esm").is_file():
        data = root / "Data"
    else:
        raise ConversionError("Expected a real Skyrim.esm under the Data directory")
    if data.is_symlink() or (data / "Skyrim.esm").is_symlink():
        raise ConversionError("Symlinked Skyrim data paths are not accepted")
    return data.resolve()


def _archive_paths(directory: Path) -> tuple[int, list[Path]]:
    paths = sorted((p for p in directory.iterdir()
                    if p.is_file() and p.suffix.casefold() == ".bsa"), key=lambda p:p.name.casefold())
    if not paths or len(paths) > 160:
        raise ConversionError("Expected 1..160 BSA archives in the game Data directory")
    versions = set()
    for p in paths:
        if p.is_symlink():
            raise ConversionError("Symlinked BSA archive")
        with p.open("rb") as f:
            signature = f.read(8)
        if len(signature) != 8 or signature[:4] != b"BSA\0":
            raise ConversionError(f"Archive not recognized as BSA: {p.name}")
        v = struct.unpack_from("<I", signature, 4)[0]
        if v not in (104, 105):
            raise ConversionError(f"Unsupported BSA {v}: {p.name}")
        versions.add(v)
    if len(versions) != 1:
        raise ConversionError("Mixed BSA v104/v105 detected; edition identity ambiguous")
    return versions.pop(), paths


def convert_game(game_dir: str | Path, output: str | Path, *,
                 cell_id: int, max_instances: int = 128,
                 triangle_limit: int = 1024) -> dict:
    """Convert PPSC and one authentic static BSTriShape into PPMG.

    Model transforms and full cell placement are not combined yet.
    Required user-owned game data are never uploaded or embedded in source.
    """
    if not 1 <= max_instances <= 128 or not 1 <= triangle_limit <= 4096:
        raise ConversionError("Scene and triangle budgets outside supported range")
    if not 0 <= cell_id <= 0xffffffff:
        raise ConversionError("Cell FormID must be a uint32")
    data = _data_directory(Path(game_dir))
    destination = Path(output).resolve()
    if data == destination or data in destination.parents or destination in data.parents:
        raise ConversionError("Output must be outside the game data tree")
    if destination.exists() and any(destination.iterdir()):
        raise ConversionError("Output directory is not empty; refusing to overwrite")
    edition_version, archive_paths = _archive_paths(data)
    scan = scan_plugin(data / "Skyrim.esm")
    refs = sorted((r for r in scan.references if r.cell_id == cell_id
                   and r.base_id in scan.statics), key=lambda r:r.form_id)
    if not refs:
        raise ConversionError(f"No resolvable STAT references in cell 0x{cell_id:08x}")
    if len(refs) > max_instances:
        raise ConversionError("Selected cell exceeds instance budget")
    selected_model = None
    errors = []
    archives_indexed = 0
    archives = []
    for path in archive_paths:
        archive = BSAArchive(path)
        archives.append(archive)
        archives_indexed += 1
    for ref in refs[:64]:
        model = scan.statics[ref.base_id].model.replace("\\", "/").lstrip("/")
        if not model.casefold().startswith("meshes/"):
            model = "meshes/" + model
        parts = model.split("/")
        if any(p in ("", ".", "..") or ":" in p for p in parts):
            errors.append(f"Unsafe model path for 0x{ref.form_id:08x}")
            continue
        for archive in reversed(archives):
            if model.casefold() not in archive.members:
                continue
            try:
                raw = archive.read_member(model, max_bytes=8 * 1024 * 1024)
                nif = read_nif(raw)
                if len(nif.triangles) > triangle_limit:
                    raise NIFError("Chosen NIF exceeds explicit triangle budget")
            except (BSAError, NIFError, KeyError) as exc:
                errors.append(f"{model}: {exc}")
                continue
            selected_model = (ref, model, archive, raw, nif)
            break
        if selected_model:
            break
    if selected_model is None:
        raise ConversionError("No supported static BSTriShape found in BSA archives: "
                              + "; ".join(errors[:8]))
    ref, path, archive, nif_data, nif = selected_model
    subset = replace(scan, references=tuple(refs))
    scene_bytes, report = create_scene(subset, cell_id=cell_id, max_instances=max_instances)
    mesh_bytes = encode_mesh(nif)
    decode_mesh(mesh_bytes)
    read_scene(scene_bytes)
    # Create output only after all parsing and validation completes.
    destination.mkdir(parents=True, exist_ok=True)
    if any(destination.iterdir()):
        raise ConversionError("Concurrent writer created content in output directory")
    (destination / "scene.ppsc").write_bytes(scene_bytes)
    (destination / "mesh.ppmg").write_bytes(mesh_bytes)
    sd=destination/"3ds"/"pocketport"/"skyrim"
    sd.mkdir(parents=True,exist_ok=False)
    (sd/"scene.ppsc").write_bytes(scene_bytes)
    (sd/"mesh.ppmg").write_bytes(mesh_bytes)
    info = {
        "schema_version": 1, "edition": "Skyrim Special Edition" if edition_version==105 else "Skyrim 2011",
        "archive_version": edition_version, "source": str(data),
        "cell_id": f"0x{cell_id:08x}", "reference_id": f"0x{ref.form_id:08x}",
        "base_static_id": f"0x{ref.base_id:08x}", "model_path": path,
        "archive": archive.path.name, "original_nif_sha256": hashlib.sha256(nif_data).hexdigest(),
        "scene": {"instances": len(refs), "file": "scene.ppsc",
                  "sha256": hashlib.sha256(scene_bytes).hexdigest()},
        "mesh": {"vertices": len(nif.vertices), "triangles": len(nif.triangles),
                 "file": "mesh.ppmg", "sha256": hashlib.sha256(mesh_bytes).hexdigest()},
        "supported": "one static BSTriShape; geometry has not been placed at REFR rotation",
        "not_supported": ["other NIF shapes", "materials", "texture uploads", "collision",
                          "Papyrus", "quests", "full worldspace", "gameplay"],
        "warnings": errors[:8],
        "runtime": "Copy output/3ds to Azahar emulated SD root (sdmc/)",
        "sd_root": str(destination/"3ds")
    }
    (destination / "manifest.json").write_text(
        json.dumps(info, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return info
