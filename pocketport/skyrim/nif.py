"""Original bounded Skyrim BSTriShape vertex/triangle reader (NIF 20.2.0.7).

Handles a static unskinned subset of Bethesda stream 100 (LE) and 130
(SE); unknown layouts fail closed. Not a complete NIF scene graph.
No source from third-party GPL implementations is copied.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import math
import struct

MAX_NIF = 16 * 1024 * 1024
MAX_BLOCKS = 4096
MAX_VERTS = 4096
MAX_TRIANGLES = 4096
NIF_VERSION = 0x14020007


class NIFError(ValueError):
    pass


class Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.off = 0

    def take(self, size: int) -> bytes:
        if size < 0 or size > len(self.data) - self.off:
            raise NIFError("Truncated NIF field or invalid declared length")
        result = self.data[self.off:self.off + size]
        self.off += size
        return result

    def u8(self) -> int:
        return self.take(1)[0]

    def u16(self) -> int:
        return struct.unpack("<H", self.take(2))[0]

    def u32(self) -> int:
        return struct.unpack("<I", self.take(4))[0]

    def string(self, max_length: int = 2048) -> str:
        size = self.u32()
        if size > max_length:
            raise NIFError("NIF string exceeds budget")
        return self.take(size).decode("utf-8", "replace")

    def floats(self, n: int) -> tuple[float, ...]:
        values = struct.unpack("<" + "f" * n, self.take(n * 4))
        if not all(math.isfinite(v) for v in values):
            raise NIFError("Non-finite NIF coordinate")
        return values


@dataclass(frozen=True)
class Mesh:
    vertices: tuple[tuple[float, ...], ...]  # x/y/z, nx/ny/nz, u/v
    triangles: tuple[tuple[int, int, int], ...]
    bethesda_version: int
    block_index: int


def _shape(block: bytes, stream: int, index: int, *,
           counted: bool, extra_bounds: int) -> Mesh:
    r = Reader(block)
    r.u32()  # NiAVObject name table index
    if counted:
        extras = r.u32()
        if extras > 16:
            raise NIFError("Unbounded NiAVObject extra-data references")
        r.take(4 * extras)
    else:
        r.u32()  # compact extra-data pointer
    r.u32()  # controller
    r.u32()  # object flags
    translation = r.floats(3)
    rotation = r.floats(9)
    scale, = r.floats(1)
    if abs(scale) < 1e-6:
        raise NIFError("Degenerate NIF object scale")
    r.u32()  # collision pointer
    r.take(16 + extra_bounds)  # bounds, occasionally extended in SE
    r.take(12)  # skin, shader and alpha references
    desc = struct.unpack("<Q", r.take(8))[0]
    stride = (desc & 15) * 4
    flags = (desc >> 44) & 0xfff
    if not (flags & 1) or flags & ~0x3b:
        raise NIFError("Unsupported or skinned BSTriShape vertex flags")
    ntri, nvert, declared_size = struct.unpack("<HHI", r.take(8))
    if not (1 <= ntri <= MAX_TRIANGLES and 3 <= nvert <= MAX_VERTS):
        raise NIFError("BSTriShape exceeds triangle/vertex budget")
    expected_size = nvert * stride + ntri * 6
    if declared_size != expected_size or stride < 16 or stride > 60:
        raise NIFError("BSTriShape geometry size/stride mismatch")
    if declared_size > len(block) - r.off:
        raise NIFError("Truncated BSTriShape geometry")
    vertices = []
    for _ in range(nvert):
        raw = Reader(r.take(stride))
        xyz = raw.floats(3)
        raw.take(4)  # bitangent X
        uv = struct.unpack("<ee", raw.take(4)) if flags & 2 else (0., 0.)
        normal = (0., 0., 1.)
        if flags & 8:
            n = raw.take(4)
            normal = tuple(v / 127.5 - 1. for v in n[:3])
            if flags & 16:
                raw.take(4)
        if flags & 32:
            raw.take(4)
        if not all(math.isfinite(v) for v in uv):
            raise NIFError("Non-finite UV")
        transformed = tuple(translation[i] + scale * sum(
            rotation[i * 3 + j] * xyz[j] for j in range(3)) for i in range(3))
        rotated = tuple(sum(rotation[i * 3 + j] * normal[j]
                            for j in range(3)) for i in range(3))
        nlen = math.sqrt(sum(v * v for v in rotated))
        if not nlen or not math.isfinite(nlen):
            raise NIFError("Invalid NIF normal")
        values = (*transformed, *(v / nlen for v in rotated), *uv)
        if not all(math.isfinite(v) for v in values):
            raise NIFError("Invalid NIF transformed vertex")
        vertices.append(values)
    triangles = []
    for _ in range(ntri):
        a, b, c = struct.unpack("<HHH", r.take(6))
        if max(a, b, c) >= nvert:
            raise NIFError("Triangle index outside vertex buffer")
        triangles.append((a, b, c))
    if r.off < len(block):
        if len(block) - r.off < 4:
            raise NIFError("Unrecognized BSTriShape trailing data")
        extra = r.u32()
        if extra * 2 != len(block) - r.off:
            raise NIFError("Unsupported trailing BSTriShape particle payload")
        r.take(extra * 2)
    if r.off != len(block):
        raise NIFError("Unconsumed BSTriShape bytes")
    return Mesh(tuple(vertices), tuple(triangles), stream, index)


def read_nif(source: bytes | str | Path) -> Mesh:
    if isinstance(source, (str, Path)):
        path = Path(source)
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_NIF:
            raise NIFError("NIF path missing, symlinked or too large")
        data = path.read_bytes()
    else:
        data = source
    if not isinstance(data, bytes) or len(data) > MAX_NIF:
        raise NIFError("Invalid or excessive NIF input")
    line_end = data.find(b"\n", 0, 120)
    if line_end < 0 or not data.startswith((
            b"Gamebryo File Format, Version ", b"NetImmerse File Format, Version ")):
        raise NIFError("Unrecognized NIF header signature")
    r = Reader(data)
    r.take(line_end + 1)
    version = r.u32()
    if version != NIF_VERSION or r.u8() != 1 or r.u32() != 12:
        raise NIFError("Expected little-endian NIF 20.2.0.7 user-version 12")
    block_count = r.u32()
    stream = r.u32()
    if not 1 <= block_count <= MAX_BLOCKS or stream not in (100, 130):
        raise NIFError("Unsupported NIF block count or Bethesda stream version")
    for _ in range(3):  # author, process script, export script
        n = r.u8()
        if n > 128:
            raise NIFError("Invalid NIF metadata string")
        r.take(n)
    if stream >= 103:
        n = r.u8()
        r.take(n)
    num_types = r.u16()
    if not 1 <= num_types <= 256:
        raise NIFError("Invalid NIF type table size")
    types = tuple(r.string(128) for _ in range(num_types))
    indices = [r.u16() for _ in range(block_count)]
    if any(idx >= num_types for idx in indices):
        raise NIFError("Invalid NIF block type index")
    sizes = [r.u32() for _ in range(block_count)]
    if sum(sizes) > MAX_NIF:
        raise NIFError("NIF block payload exceeds budget")
    string_count, string_max = r.u32(), r.u32()
    if string_count > 4096 or string_max > 8192:
        raise NIFError("NIF string-table limits exceeded")
    for _ in range(string_count):
        r.string(min(string_max, 8192))
    group_count = r.u32()
    if group_count > 4096:
        raise NIFError("NIF group count too large")
    r.take(group_count * 4)
    found = []
    for i, size in enumerate(sizes):
        block = r.take(size)
        if types[indices[i]] != "BSTriShape":
            continue
        for counted in (True, False):
            for extension in (0, 8):
                try:
                    found.append(_shape(block, stream, i,
                                        counted=counted, extra_bounds=extension))
                    break
                except NIFError:
                    continue
            if found and found[-1].block_index == i:
                break
        else:
            raise NIFError(f"Unsupported BSTriShape block {i} layout")
    if not found:
        raise NIFError("No supported static BSTriShape was found")
    if len(found) != 1:
        raise NIFError("Only single-BSTriShape static models supported")
    return found[0]


_MESH_HEADER = struct.Struct("<4sHHII")
_VERTEX = struct.Struct("<8f")
_TRI = struct.Struct("<3H")


def encode_mesh(mesh: Mesh) -> bytes:
    if not (3 <= len(mesh.vertices) <= MAX_VERTS
            and 1 <= len(mesh.triangles) <= MAX_TRIANGLES):
        raise NIFError("Mesh exceeds 3DS runtime geometry budget")
    data = bytearray(_MESH_HEADER.pack(
        b"PPMG", 1, 0, len(mesh.vertices), len(mesh.triangles)))
    for vertex in mesh.vertices:
        if len(vertex) != 8 or not all(math.isfinite(v) for v in vertex):
            raise NIFError("Invalid NIF vertex")
        data.extend(_VERTEX.pack(*vertex))
    for tri in mesh.triangles:
        if len(tri) != 3 or min(tri) < 0 or max(tri) >= len(mesh.vertices):
            raise NIFError("Invalid triangle index")
        data.extend(_TRI.pack(*tri))
    return bytes(data)


def decode_mesh(data: bytes) -> Mesh:
    if len(data) < _MESH_HEADER.size:
        raise NIFError("Truncated PPMG header")
    magic, ver, flags, nv, nt = _MESH_HEADER.unpack_from(data)
    if (magic != b"PPMG" or ver != 1 or flags != 0
            or not (3 <= nv <= MAX_VERTS) or not (1 <= nt <= MAX_TRIANGLES)):
        raise NIFError("Invalid PPMG header")
    expected = _MESH_HEADER.size + nv * _VERTEX.size + nt * _TRI.size
    if len(data) != expected:
        raise NIFError("Truncated or excessive PPMG data")
    vertices = tuple(_VERTEX.unpack_from(
        data, _MESH_HEADER.size + i * _VERTEX.size) for i in range(nv))
    triangles = tuple(_TRI.unpack_from(
        data, _MESH_HEADER.size + nv * _VERTEX.size + i * _TRI.size)
                      for i in range(nt))
    if any(not all(math.isfinite(x) for x in v) for v in vertices):
        raise NIFError("Non-finite PPMG vertex")
    if any(max(t) >= nv for t in triangles):
        raise NIFError("PPMG triangle index outside vertex buffer")
    return Mesh(vertices, triangles, 0, 0)


def convert_nif(source: str | Path, destination: str | Path) -> dict:
    mesh = read_nif(source)
    output = Path(destination)
    if output.exists():
        raise NIFError("Refusing to overwrite existing mesh package")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(encode_mesh(mesh))
    return {"file": str(output), "vertices": len(mesh.vertices),
            "triangles": len(mesh.triangles), "format": "PPMG v1",
            "bethesda_stream": mesh.bethesda_version,
            "status": "BSTriShape geometry converted; shader/material/skin unsupported"}
