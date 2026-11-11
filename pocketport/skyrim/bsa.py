"""Skyrim Legendary Edition BSA v104: bounded metadata and selective extraction.

Independent Python implementation; no game assets, decryption or writes to source.
Other BSA variants and unsafe layouts fail closed rather than being guessed.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os
import struct
import zlib

_HEADER = struct.Struct("<4s8I")
_FOLDER = struct.Struct("<QII")
_FILE = struct.Struct("<QII")
MAX_FILES = 200000
MAX_FOLDERS = 30000
MAX_MEMBER = 32 * 1024 * 1024


class BSAError(ValueError):
    pass


@dataclass(frozen=True)
class Member:
    name: str
    offset: int
    stored_size: int
    compressed: bool


def _exact(f, length: int) -> bytes:
    data = f.read(length)
    if len(data) != length:
        raise BSAError("Truncated BSA table or member")
    return data


def _name(raw: bytes) -> str:
    if not raw or b"\0" in raw[:-1]:
        raise BSAError("Invalid BSA resource name")
    name = raw.rstrip(b"\0").decode("cp1252").replace("\\", "/")
    parts = name.split("/")
    if (name.startswith("/") or any(p in ("", ".", "..") for p in parts)
            or ":" in name or any(ord(c) < 32 for c in name)):
        raise BSAError("Unsafe BSA member name")
    return name


class BSAArchive:
    """Read-only Skyrim 2011 BSA index with bounded member extraction."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        if self.path.is_symlink() or not self.path.is_file():
            raise BSAError("BSA must be an existing regular file")
        self.size = self.path.stat().st_size
        self.members: dict[str, Member] = {}
        self.version = 0
        self._parse()

    def _parse(self) -> None:
        if self.size < _HEADER.size:
            raise BSAError("Truncated BSA header")
        with self.path.open("rb") as f:
            magic, version, start, flags, folders, count, folder_len, names_len, types = (
                _HEADER.unpack(_exact(f, _HEADER.size)))
            if magic != b"BSA\0" or version != 104 or start != _HEADER.size:
                raise BSAError("Requires Skyrim 2011 BSA v104, 36-byte header")
            if not (flags & 1 and flags & 2) or flags & ~0x1ff:
                raise BSAError("Unsupported BSA archive flags")
            if folders > MAX_FOLDERS or count > MAX_FILES or (folders == 0) != (count == 0):
                raise BSAError("BSA index count outside bounds")
            if folder_len > self.size or names_len > self.size:
                raise BSAError("Invalid name table lengths")
            if _HEADER.size + folders * _FOLDER.size > self.size:
                raise BSAError("Truncated folder records")
            folder_records = [_FOLDER.unpack(_exact(f, _FOLDER.size))
                              for _ in range(folders)]
            index = []
            seen = 0
            names_bytes = 0
            for folder_hash, file_count, record_offset in folder_records:
                if file_count > count - seen:
                    raise BSAError("Folder count exceeds declared total")
                # Skyrim v104 offsets vary by archive flags; the sequential
                # blocks are authoritative and validated against file data.
                size = _exact(f, 1)[0]
                raw = _exact(f, size)
                if size == 0 or raw[-1:] != b"\0":
                    raise BSAError("Invalid null-terminated folder name")
                folder = _name(raw)
                names_bytes += size + 1
                for _ in range(file_count):
                    file_hash, packed, offset = _FILE.unpack(_exact(f, _FILE.size))
                    stored = packed & 0x3fffffff
                    compressed = bool(flags & 4) ^ bool(packed & 0x40000000)
                    index.append((folder, offset, stored, compressed))
                seen += file_count
            if seen != count or names_bytes != folder_len:
                raise BSAError("BSA folder name length/count mismatch")
            filename_start = f.tell()
            raw_names = _exact(f, names_len)
            filenames = raw_names.split(b"\0")
            if len(filenames) != count + 1 or filenames[-1] != b"":
                raise BSAError("BSA file name count/termination mismatch")
            data_start = f.tell()
            for (folder, offset, stored, compressed), raw_name in zip(index, filenames):
                name = _name(raw_name)
                full = folder + "/" + name
                if (offset < data_start or stored > self.size - offset
                        or stored > MAX_MEMBER + 1024 * 1024):
                    raise BSAError("Invalid BSA member extent or size")
                key = full.casefold()
                if key in self.members:
                    raise BSAError("Duplicate BSA member path")
                self.members[key] = Member(full, offset, stored, compressed)
            self.version = version

    def names(self) -> list[str]:
        return sorted(m.name for m in self.members.values())

    def read_member(self, name: str, *, max_bytes: int = MAX_MEMBER) -> bytes:
        if not 0 < max_bytes <= MAX_MEMBER:
            raise BSAError("Invalid extraction byte budget")
        key = _name(name.encode("cp1252")).casefold()
        if key not in self.members:
            raise KeyError(name)
        entry = self.members[key]
        if entry.stored_size > max_bytes + 1024 * 1024:
            raise BSAError("Member exceeds compressed input budget")
        with self.path.open("rb") as f:
            f.seek(entry.offset)
            payload = _exact(f, entry.stored_size)
        # Optional embedded name prefix (common in some mod archives).
        with self.path.open("rb") as f:
            _HEADER_values = _HEADER.unpack(_exact(f, _HEADER.size))
        if _HEADER_values[3] & 0x100:
            if not payload:
                raise BSAError("Missing embedded name")
            skip = 1 + payload[0]
            if skip > len(payload):
                raise BSAError("Truncated embedded name")
            payload = payload[skip:]
        if not entry.compressed:
            if len(payload) > max_bytes:
                raise BSAError("Member exceeds output budget")
            return payload
        if len(payload) < 4:
            raise BSAError("Compressed member missing output length")
        expected = struct.unpack_from("<I", payload)[0]
        if expected > max_bytes:
            raise BSAError("Declared decompressed size exceeds budget")
        decoder = zlib.decompressobj()
        try:
            decoded = decoder.decompress(payload[4:], expected + 1)
            decoded += decoder.flush()
        except zlib.error as exc:
            raise BSAError("Invalid zlib member") from exc
        if (not decoder.eof or decoder.unused_data or len(decoded) != expected
                or len(decoded) > max_bytes):
            raise BSAError("Compressed BSA member failed integrity/size checks")
        return decoded


def inspect_bsa(path: str | Path) -> dict:
    archive = BSAArchive(path)
    return {"format": "BSA", "version": archive.version,
            "files": len(archive.members), "sample_paths": archive.names()[:24],
            "status": "index parsed; no Skyrim runtime or asset compatibility implied"}
