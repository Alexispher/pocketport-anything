"""Bounded, read-only NUP v1 container metadata inspection.

Independent implementation informed by Lichii's documented format; no GPL code
is incorporated. Never decodes, decrypts, decompresses, extracts, or executes members.
"""
from __future__ import annotations

import hashlib
import struct
from pathlib import Path

MAGIC = b"NUP\x01"
TOC_MAGIC = b"TOC\x01"
SUPERBLOCK = struct.Struct("<4sHHQQ32sQQII16s32s")
TOC_HEADER = struct.Struct("<4sIQQQQQ")
PACKAGE = struct.Struct("<QIIII BBH IQI20s")
MAX_TOC_BYTES = 64 * 1024 * 1024
MAX_PACKAGES = 10000


class NupError(ValueError):
    """Invalid, truncated, or unsupported NUP metadata."""


def inspect_nup(path: Path) -> dict:
    """Inspect authenticated TOC and fixed package records; no data is written.

    Whole-file hashes must be computed separately using pocketport hash. This
    parser reads only the 128-byte superblock and at most 64 MiB of TOC.
    """
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        raise NupError("Expected an existing regular NUP file, not a symlink")
    actual_size = path.stat().st_size
    with path.open("rb") as source:
        head = source.read(SUPERBLOCK.size)
        if len(head) != SUPERBLOCK.size:
            raise NupError("Truncated NUP superblock")
        (magic, header_size, version, toc_off, toc_size, toc_hash,
         blob_off, recorded_size, package_count, flags, _uuid, _reserved) = SUPERBLOCK.unpack(head)
        if magic != MAGIC:
            raise NupError("NUP signature mismatch")
        if header_size < SUPERBLOCK.size or version != 1 or flags != 0:
            raise NupError("Unsupported NUP header version or flags")
        if recorded_size != actual_size or not (header_size <= toc_off <= blob_off <= actual_size):
            raise NupError("NUP file size or offsets invalid")
        if toc_size < TOC_HEADER.size or toc_size > MAX_TOC_BYTES or toc_size > blob_off - toc_off:
            raise NupError("NUP TOC size outside bounds")
        if blob_off % 16:
            raise NupError("NUP blob offset must be 16-byte aligned")
        if not 0 < package_count <= MAX_PACKAGES:
            raise NupError("NUP package count out of bounds")
        source.seek(toc_off)
        toc = source.read(toc_size)
    if len(toc) != toc_size or hashlib.sha256(toc).digest() != toc_hash:
        raise NupError("NUP table of contents failed SHA-256 integrity validation")
    (toc_magic, toc_package_count, dirs, files, pool_offset, pool_size, reserved) = TOC_HEADER.unpack_from(toc)
    if toc_magic != TOC_MAGIC or toc_package_count != package_count or reserved != 0:
        raise NupError("Unsupported or inconsistent NUP TOC header")
    needed = TOC_HEADER.size + package_count * PACKAGE.size + dirs * 0x18 + files * 0x50
    if needed > len(toc) or not (needed <= pool_offset <= len(toc)) or pool_size > len(toc) - pool_offset:
        raise NupError("NUP TOC records or string pool outside bounds")
    if (pool_offset - needed) % 4:
        raise NupError("NUP child index table is not aligned")
    packages = []
    kinds = ("base", "update", "addon")
    for i in range(package_count):
        fields = PACKAGE.unpack_from(toc, TOC_HEADER.size + i * PACKAGE.size)
        title_id, root_dir, exefs_dir, romfs_dir, version_num, kind, pkg_flags, _reserved16, _reserved32, meta_off, meta_size, _ = fields
        if kind > 2 or pkg_flags & ~1:
            raise NupError("Unsupported NUP package kind or flags")
        if root_dir >= dirs or any(v != 0xffffffff and v >= dirs for v in (exefs_dir, romfs_dir)):
            raise NupError("NUP package directory reference outside bounds")
        if meta_size and (meta_off < 0 or meta_off > len(toc) or meta_size > len(toc) - meta_off):
            raise NupError("NUP package metadata outside TOC")
        packages.append({"title_id": f"{title_id:016x}", "version": version_num,
                         "kind": kinds[kind], "standalone_update": bool(pkg_flags & 1),
                         "has_exefs": exefs_dir != 0xffffffff,
                         "has_romfs": romfs_dir != 0xffffffff,
                         "metadata_bytes": meta_size})
    return {"format": "nup-v1", "file_size": actual_size, "toc_verified": True,
            "package_count": len(packages), "directory_count": dirs,
            "file_entry_count": files, "packages": packages,
            "scope": "Read-only authenticated index and package records only. No member integrity or gameplay verification."}
