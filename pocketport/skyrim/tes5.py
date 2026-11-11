"""Bounded TES5 master/plugin record reader: STAT models and placed REFR transforms.

Handles GRUP nesting, XXX long subrecords, and flagged zlib records. Data is
never executed; scripts, Havok, animation, NIF, and gameplay are unsupported.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import math
import struct
import zlib

REC_HDR = struct.Struct("<4sIIIII")  # 24 bytes, also group common header size
MAX_RECORD = 16 * 1024 * 1024
MAX_SCAN = 4 * 1024 * 1024 * 1024
MAX_RECORDS = 500000


class TES5Error(ValueError):
    pass


@dataclass(frozen=True)
class Static:
    form_id: int
    editor_id: str
    model: str


@dataclass(frozen=True)
class Reference:
    form_id: int
    base_id: int
    cell_id: int
    position: tuple[float, float, float]
    rotation: tuple[float, float, float]
    scale: float


@dataclass(frozen=True)
class Scan:
    statics: dict[int, Static]
    cells: dict[int, str]
    references: tuple[Reference, ...]
    scanned_records: int


def _fields(data: bytes):
    offset = 0
    extended = None
    while offset < len(data):
        if len(data) - offset < 6:
            raise TES5Error("Truncated subrecord")
        tag, size = struct.unpack_from("<4sH", data, offset)
        offset += 6
        if tag == b"XXXX":
            if size != 4 or extended is not None or len(data) - offset < 4:
                raise TES5Error("Invalid XXXX extended-size marker")
            extended = struct.unpack_from("<I", data, offset)[0]
            offset += 4
            continue
        if extended is not None:
            size = extended
            extended = None
        if size > len(data) - offset or size > MAX_RECORD:
            raise TES5Error("Subrecord extends beyond record")
        yield tag, data[offset:offset + size]
        offset += size
    if extended is not None:
        raise TES5Error("Dangling XXXX subrecord")


def _inflate(payload: bytes) -> bytes:
    if len(payload) < 4:
        raise TES5Error("Compressed record truncated")
    expected = struct.unpack_from("<I", payload)[0]
    if expected > MAX_RECORD:
        raise TES5Error("Record decompression budget exceeded")
    try:
        decoder = zlib.decompressobj()
        data = decoder.decompress(payload[4:], expected + 1)
    except zlib.error as exc:
        raise TES5Error("Invalid compressed TES5 record") from exc
    if not decoder.eof or decoder.unused_data or len(data) != expected:
        raise TES5Error("Compressed record length/integrity mismatch")
    return data


def _string(data: bytes) -> str:
    return data.split(b"\0", 1)[0].decode("cp1252")


def scan_plugin(path: str | Path, *, max_records: int = MAX_RECORDS) -> Scan:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise TES5Error("TES5 plugin must be a regular file")
    length = path.stat().st_size
    if not 24 <= length <= MAX_SCAN or max_records < 1:
        raise TES5Error("TES5 file size or record count limit exceeded")
    statics: dict[int, Static] = {}
    cells: dict[int, str] = {}
    refs: list[Reference] = []
    # Group scopes: (end, cell_form_id), retaining the active cell through nested groups.
    stack: list[tuple[int, int]] = [(length, 0)]
    count = 0
    with path.open("rb") as f:
        if f.read(4) != b"TES4":
            raise TES5Error("Expected a Skyrim TES4 plugin header")
        f.seek(0)
        while f.tell() < length:
            pos = f.tell()
            while len(stack) > 1 and pos == stack[-1][0]:
                stack.pop()
            if pos > stack[-1][0] or stack[-1][0] - pos < 24:
                raise TES5Error("Record crosses GRUP boundary")
            raw = f.read(24)
            if len(raw) != 24:
                raise TES5Error("Truncated record header")
            tag, size, flags, form_id, rev, ver = REC_HDR.unpack(raw)
            if tag == b"GRUP":
                end = pos + size
                if size < 24 or end > stack[-1][0] or len(stack) >= 64:
                    raise TES5Error("Invalid GRUP size or depth")
                group_type = form_id
                cell = stack[-1][1]
                if group_type == 6:
                    cell = flags  # GRUP label (cell FormID) at offset +8.
                stack.append((end, cell))
                continue
            end = pos + 24 + size
            if size > MAX_RECORD or end > stack[-1][0]:
                raise TES5Error("Invalid record extent")
            count += 1
            if count > max_records:
                raise TES5Error("Record count budget exceeded")
            if tag not in (b"STAT", b"REFR", b"CELL"):
                f.seek(end)
                continue
            payload = f.read(size)
            if len(payload) != size:
                raise TES5Error("Truncated TES5 payload")
            if flags & 0x00040000:
                payload = _inflate(payload)
            fields = dict(_fields(payload))
            if tag == b"STAT":
                path_raw = fields.get(b"MODL", b"")
                if path_raw:
                    statics[form_id] = Static(form_id, _string(fields.get(b"EDID", b"")),
                                              _string(path_raw))
            elif tag == b"CELL":
                cells[form_id] = _string(fields.get(b"EDID", b""))
            elif b"NAME" in fields and b"DATA" in fields:
                if len(fields[b"NAME"]) != 4 or len(fields[b"DATA"]) != 24:
                    raise TES5Error("Invalid REFR NAME/DATA size")
                base = struct.unpack("<I", fields[b"NAME"])[0]
                values = struct.unpack("<6f", fields[b"DATA"])
                scale_raw = fields.get(b"XSCL")
                if scale_raw is not None and len(scale_raw) != 4:
                    raise TES5Error("Invalid reference scale")
                scale = struct.unpack("<f", scale_raw)[0] if scale_raw else 1.0
                if not all(math.isfinite(v) for v in (*values, scale)) or scale <= 0:
                    raise TES5Error("Non-finite transform or invalid scale")
                refs.append(Reference(form_id, base, stack[-1][1],
                                      values[:3], values[3:], scale))
        if f.tell() != length:
            raise TES5Error("TES5 file not fully indexed")
    return Scan(statics, cells, tuple(refs), count)


def inspect_plugin(path: str | Path) -> dict:
    scan = scan_plugin(path)
    return {"format": "TES5 plugin", "scanned_records": scan.scanned_records,
            "static_models": len(scan.statics), "placed_references": len(scan.references),
            "cells": len(scan.cells),
            "unsupported": ["NIF geometry", "Papyrus", "Havok", "animation",
                            "quests", "full cell/world streaming"]}
