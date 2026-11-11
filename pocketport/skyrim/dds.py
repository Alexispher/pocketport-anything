"""Small verified Skyrim LE DDS DXT1 decoder to portable RGB565 intermediate.

No GPU-native tiled PICA200 texture encoding; conversion remains an
intermediate asset format until a real tex3ds/renderer texture upload is added.
"""
from __future__ import annotations
import struct
from pathlib import Path

class DDSError(ValueError):
    pass

def _rgb565(value: int) -> tuple[int,int,int]:
    return (((value >> 11) & 31) * 255 // 31,
            ((value >> 5) & 63) * 255 // 63,
            (value & 31) * 255 // 31)

def _pack565(rgb: tuple[int,int,int]) -> int:
    r,g,b = rgb
    return ((r * 31 // 255) << 11) | ((g * 63 // 255) << 5) | (b * 31 // 255)

def decode_dxt1(data: bytes) -> tuple[int,int,bytes]:
    """Accept a single 2D DXT1 DDS first mip, up to 512x512 pixels."""
    if len(data) < 128 or data[:4] != b"DDS ":
        raise DDSError("Missing complete DDS header")
    if struct.unpack_from("<I",data,4)[0] != 124 or struct.unpack_from("<I",data,76)[0] != 32:
        raise DDSError("Invalid DDS header structure")
    height,width = struct.unpack_from("<II",data,12)
    if not (1 <= width <= 512 and 1 <= height <= 512):
        raise DDSError("Texture dimensions outside decoder limit")
    depth = struct.unpack_from("<I",data,24)[0]
    if depth not in (0,1):
        raise DDSError("Only 2D DDS textures are supported")
    if data[84:88] != b"DXT1":
        raise DDSError("Only DXT1 FourCC is supported")
    blocks_x=(width+3)//4
    blocks_y=(height+3)//4
    required=128+blocks_x*blocks_y*8
    if len(data) < required:
        raise DDSError("Truncated DXT1 pixel blocks")
    # RGB565 row-major intermediate, no GPU tiling.
    pixels=bytearray(width*height*2)
    offset=128
    for by in range(blocks_y):
        for bx in range(blocks_x):
            c0,c1,mask=struct.unpack_from("<HHI",data,offset)
            offset+=8
            p0,p1=_rgb565(c0),_rgb565(c1)
            if c0>c1:
                colors=[p0,p1,tuple((2*a+b)//3 for a,b in zip(p0,p1)),
                        tuple((a+2*b)//3 for a,b in zip(p0,p1))]
            else:
                colors=[p0,p1,tuple((a+b)//2 for a,b in zip(p0,p1)),None]
            for y in range(4):
                for x in range(4):
                    tx,ty=bx*4+x,by*4+y
                    ix=(mask>>(2*(y*4+x)))&3
                    if tx>=width or ty>=height:
                        continue
                    color=colors[ix]
                    if color is None:
                        raise DDSError("DXT1 transparent blocks require an alpha-capable format")
                    struct.pack_into("<H",pixels,2*(ty*width+tx),_pack565(color))
    return width,height,bytes(pixels)

def pack_texture(width: int,height: int,raw: bytes) -> bytes:
    if not 1<=width<=512 or not 1<=height<=512 or len(raw)!=width*height*2:
        raise DDSError("Invalid RGB565 texture size")
    return struct.pack("<4sHHI",b"PPTR",width,height,len(raw))+raw

def convert_dds(path: str|Path, destination: str|Path) -> dict:
    src=Path(path)
    if src.is_symlink() or not src.is_file() or src.stat().st_size>8*1024*1024:
        raise DDSError("Invalid or excessive DDS input")
    width,height,pixels=decode_dxt1(src.read_bytes())
    dest=Path(destination)
    if dest.exists():
        raise DDSError("Refusing to overwrite existing converted texture")
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(pack_texture(width,height,pixels))
    return {"width":width,"height":height,"format":"RGB565 row-major intermediate (not PICA200 tiled)",
            "file":str(dest),"bytes":dest.stat().st_size}
