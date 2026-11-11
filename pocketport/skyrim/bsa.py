"""Skyrim LE BSA v104 and Special Edition v105: bounded indexing/extraction.

Independent Python implementation; no game assets, decryption or writes to source.
Unsupported BSA variants and unsafe layouts fail closed. BSA105 uses LZ4.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import io
import struct
import zlib

_HEADER = struct.Struct("<4s8I")
_FOLDER = struct.Struct("<QII")
_FOLDER_SE = struct.Struct("<QIIQ")
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
    """Read-only BSA index and member extraction for Skyrim LE/SE."""

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
            if magic != b"BSA\0" or version not in (104, 105) or start != _HEADER.size:
                raise BSAError("Only Skyrim LE v104 and SE v105 BSA headers are supported")
            if not (flags & 1 and flags & 2) or flags & ~0x1ff:
                raise BSAError("Unsupported BSA archive flags")
            if folders > MAX_FOLDERS or count > MAX_FILES or (folders == 0) != (count == 0):
                raise BSAError("BSA index count outside bounds")
            if folder_len > self.size or names_len > self.size:
                raise BSAError("Invalid name table lengths")
            folder_format = _FOLDER_SE if version == 105 else _FOLDER
            if _HEADER.size + folders * folder_format.size > self.size:
                raise BSAError("Truncated folder records")
            folder_records = [folder_format.unpack(_exact(f, folder_format.size))
                              for _ in range(folders)]
            index = []
            seen = 0
            names_bytes = 0
            for folder_record in folder_records:
                folder_hash, file_count = folder_record[:2]
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
        if self.version == 105:
            try:
                import lz4.block
                import lz4.frame
            except ImportError as exc:
                raise BSAError("Skyrim SE LZ4 requires: pip install lz4") from exc
            compressed = payload[4:]
            try:
                if compressed.startswith(b"\\x04\\x22\\x4d\\x18"):
                    with lz4.frame.open(io.BytesIO(compressed), mode="rb") as stream:
                        decoded = stream.read(expected + 1)
                        extra = stream.read(1)
                    if extra:
                        raise BSAError("LZ4 output exceeds declared length")
                else:
                    decoded = lz4.block.decompress(
                        compressed, uncompressed_size=expected)
            except (RuntimeError, ValueError, EOFError, OSError) as exc:
                raise BSAError("Malformed Skyrim SE LZ4 member") from exc
            if len(decoded) != expected:
                raise BSAError("LZ4 member uncompressed size mismatch")
            return decoded
        decoder = zlib.decompressobj()
        try:
            decoded = decoder.decompress(payload[4:], expected + 1)
        except zlib.error as exc:
            raise BSAError("Invalid zlib member") from exc
        if (not decoder.eof or decoder.unused_data or len(decoded) != expected
                or len(decoded) > max_bytes):
            raise BSAError("Compressed BSA member failed integrity/size checks")
        return decoded


def inspect_bsa(path: str | Path) -> dict:
    archive = BSAArchive(path)
    return {"format": "BSA", "version": archive.version,
            "edition": "Skyrim Special Edition" if archive.version == 105 else "Skyrim 2011",
            "files": len(archive.members), "sample_paths": archive.names()[:24],
            "status": "index parsed; no Skyrim runtime or asset compatibility implied"}
