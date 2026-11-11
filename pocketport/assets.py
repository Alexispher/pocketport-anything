"""Explicit, optional 3DS image preparation and real tex3ds backend.

Pillow produces interim PNGs. `tex3ds` (if requested and installed) actually
produces .t3x; no pretend GPU image conversion occurs without it.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

from .inventory import sha256, write_json

PROFILES = {
    "visual-quality": 1024,
    "balanced": 512,
    "performance": 256,
    "old-3ds": 256,
    "new-3ds": 512,
}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def _power2(value: int) -> int:
    return max(8, 1 << (value - 1).bit_length())


def optimize(source: Path, out: Path, profile: str, encode_3ds: bool = False) -> dict:
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile {profile!r}; use {sorted(PROFILES)}")
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Install Pillow via `pip install -r requirements-optional.txt`") from exc
    source = source.resolve()
    out = out.resolve()
    if not source.is_dir():
        raise ValueError(f"No asset directory: {source}")
    if out == source or source in out.parents or out in source.parents:
        raise ValueError("Output must be outside the input asset directory to preserve originals")
    tex3ds = shutil.which("tex3ds")
    if encode_3ds and not tex3ds:
        raise RuntimeError("--encode-3ds requires devkitPro tex3ds on PATH; cannot claim .t3x conversion")
    max_side = PROFILES[profile]
    result = {"schema_version": 1, "profile": profile, "max_side": max_side,
              "backend": "Pillow + tex3ds" if encode_3ds else "Pillow PNG preparation only",
              "files": [], "unsupported": []}
    for file in sorted(source.rglob("*")):
        if not file.is_file() or file.is_symlink():
            continue
        relative = file.relative_to(source)
        if file.suffix.lower() not in IMAGE_SUFFIXES:
            result["unsupported"].append({"path": relative.as_posix(), "reason": "unsupported image or non-image format"})
            continue
        try:
            with Image.open(file) as raw:
                raw.load()
                image = raw.convert("RGBA")
                original_size = image.size
        except (OSError, ValueError) as exc:
            result["unsupported"].append({"path": relative.as_posix(), "reason": str(exc)})
            continue
        ratio = min(1.0, max_side / max(image.width, image.height))
        if ratio < 1:
            image = image.resize((max(1, int(image.width * ratio)), max(1, int(image.height * ratio))), Image.Resampling.LANCZOS)
        resized = image.size
        pw, ph = _power2(image.width), _power2(image.height)
        if pw > 1024 or ph > 1024:
            raise ValueError("Power-of-two dimensions exceed the supported texture helper range")
        texture = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        texture.paste(image, (0, 0))
        png = out / "intermediate" / relative.with_suffix(".png")
        png.parent.mkdir(parents=True, exist_ok=True)
        texture.save(png, "PNG", optimize=True)
        entry = {"path": relative.as_posix(), "input_sha256": sha256(file), "original_bytes": file.stat().st_size,
                 "original_dimensions": list(original_size), "content_dimensions": list(resized),
                 "texture_dimensions": [pw, ph], "uv_scale": [resized[0]/pw, resized[1]/ph],
                 "intermediate_png": str(png), "intermediate_sha256": sha256(png),
                 "intermediate_bytes": png.stat().st_size, "hardware_compatible_encoded": False}
        if encode_3ds:
            t3x = out / "t3x" / relative.with_suffix(".t3x")
            t3x.parent.mkdir(parents=True, exist_ok=True)
            command = [tex3ds, "-f", "rgba8", "-o", str(t3x), str(png)]
            run = subprocess.run(command, capture_output=True, text=True, timeout=120)
            if run.returncode or not t3x.is_file() or not t3x.stat().st_size:
                raise RuntimeError(f"tex3ds failed for {file}: rc={run.returncode}; stderr={run.stderr}")
            entry.update({"tex3ds_command": command, "t3x": str(t3x), "t3x_sha256": sha256(t3x),
                          "t3x_bytes": t3x.stat().st_size, "hardware_compatible_encoded": True})
        result["files"].append(entry)
    out.mkdir(parents=True, exist_ok=True)
    result["processed_count"] = len(result["files"])
    result["unsupported_count"] = len(result["unsupported"])
    write_json(out / "asset-report.json", result)
    return result
