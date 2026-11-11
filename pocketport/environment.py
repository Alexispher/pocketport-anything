"""Non-invasive diagnostics for the external 3DS build environment."""
from __future__ import annotations

import os
from pathlib import Path
import shutil


def doctor() -> dict:
    candidates = ("arm-none-eabi-gcc", "3dsxtool", "3dslink", "tex3ds", "picasso", "make", "cc", "cmake", "ffmpeg")
    paths = {item: shutil.which(item) for item in candidates}
    root = os.getenv("DEVKITPRO")
    arm = os.getenv("DEVKITARM")
    env = {"DEVKITPRO": root, "DEVKITARM": arm,
           "devkitARM_3ds_rules": str(Path(arm) / "3ds_rules") if arm and (Path(arm) / "3ds_rules").exists() else None,
           "libctru_header": str(Path(root) / "libctru/include/3ds.h") if root and (Path(root) / "libctru/include/3ds.h").exists() else None}
    ready = bool(paths["arm-none-eabi-gcc"] and paths["3dsxtool"] and env["devkitARM_3ds_rules"])
    return {"tools": paths, "environment": env, "toolchain_ready_minimum": ready,
            "note": "Tool discovery is not proof that a 3DS project compiles or runs. Build, emulator, and hardware require separate evidence."}
