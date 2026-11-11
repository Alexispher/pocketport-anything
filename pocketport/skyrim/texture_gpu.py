"""Bounded DDS BC1/DXT1 and BC3/DXT5 to native tex3ds conversion.

This module decodes the first 2D mipmap and invokes the official tex3ds
command locally. It does not infer a Skyrim material or load shaders.
"""
from __future__ import annotations

from pathlib import Path
import os
import shutil
import struct
import subprocess
import tempfile

from .dds import DDSError, _rgb565

MAX_SOURCE = 8 * 1024 * 1024
MAX_DIMENSION = 512


def decode_rgba(data: bytes) -> tuple[int, int, bytes]:
    if (len(data) < 128 or data[:4] != b"DDS "
            or struct.unpack_from("<I", data, 4)[0] != 124
            or struct.unpack_from("<I", data, 76)[0] != 32):
        raise DDSError("Invalid or truncated DDS header")
    height, width = struct.unpack_from("<II", data, 12)
    if not (1 <= width <= MAX_DIMENSION and 1 <= height <= MAX_DIMENSION):
        raise DDSError("DDS dimensions exceed texture conversion budget")
    if struct.unpack_from("<I", data, 24)[0] not in (0, 1):
        raise DDSError("Only 2D DDS textures supported")
    fmt = data[84:88]
    if fmt not in (b"DXT1", b"DXT5"):
        raise DDSError("Only DXT1/BC1 and DXT5/BC3 supported")
    size = 8 if fmt == b"DXT1" else 16
    bx, by = (width+3)//4, (height+3)//4
    if 128 + bx*by*size > len(data):
        raise DDSError("Truncated compressed texture blocks")
    rgba = bytearray(width*height*4)
    off = 128
    for iy in range(by):
        for ix in range(bx):
            if fmt == b"DXT5":
                a0, a1 = data[off], data[off+1]
                bits = int.from_bytes(data[off+2:off+8], "little")
                if a0 > a1:
                    alphas = [a0, a1] + [
                        ((7-i)*a0+i*a1)//7 for i in range(1, 7)]
                else:
                    alphas = [a0, a1] + [
                        ((5-i)*a0+i*a1)//5 for i in range(1, 5)] + [0,255]
                coloroff = off+8
            else:
                bits=0
                alphas=[]
                coloroff = off
            c0,c1,indices=struct.unpack_from("<HHI", data, coloroff)
            r0,g0,b0=_rgb565(c0)
            r1,g1,b1=_rgb565(c1)
            palette = [(r0,g0,b0),(r1,g1,b1)]
            if fmt == b"DXT5" or c0 > c1:
                palette += [tuple((2*a+b)//3 for a,b in zip(palette[0],palette[1])),
                            tuple((a+2*b)//3 for a,b in zip(palette[0],palette[1]))]
            else:
                palette += [tuple((a+b)//2 for a,b in zip(palette[0],palette[1])),
                            (0,0,0)]
            for y in range(4):
                for x in range(4):
                    px,py=ix*4+x,iy*4+y
                    if px>=width or py>=height:
                        continue
                    pos=4*y+x
                    index=(indices>>(pos*2))&3
                    alpha=(alphas[(bits>>(pos*3))&7] if fmt==b"DXT5"
                           else (0 if c0<=c1 and index==3 else 255))
                    loc=(py*width+px)*4
                    rgba[loc:loc+4]=bytes((*palette[index],alpha))
            off+=size
    return width,height,bytes(rgba)


def _tile_size(dimension: int, max_dim: int) -> int:
    value=8
    while value<dimension and value<max_dim:
        value*=2
    return min(value,max_dim)


def convert_t3x(source: str|Path, output: str|Path, *,
                max_dimension: int = 128) -> dict:
    """Convert authorized local DXT1/DXT5 DDS to PICA200-friendly .t3x."""
    from PIL import Image
    src=Path(source)
    dest=Path(output)
    if (src.is_symlink() or not src.is_file()
            or src.stat().st_size>MAX_SOURCE):
        raise DDSError("Input DDS missing, symlinked or oversized")
    if dest.exists():
        raise DDSError("Refusing to overwrite texture output")
    if max_dimension not in (32,64,128,256):
        raise DDSError("Texture profile must be 32/64/128/256")
    tex3ds=shutil.which("tex3ds")
    if not tex3ds:
        raise DDSError("tex3ds tool unavailable: install devkitPro 3ds-dev tools")
    width,height,raw=decode_rgba(src.read_bytes())
    target_w=_tile_size(width,max_dimension)
    target_h=_tile_size(height,max_dimension)
    image=Image.frombytes("RGBA",(width,height),raw)
    if (target_w,target_h)!=(width,height):
        image=image.resize((target_w,target_h),Image.Resampling.LANCZOS)
    dest.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pptex-") as tmp:
        png=Path(tmp)/"image.png"
        packed=Path(tmp)/"texture.t3x"
        image.save(png,"PNG")
        result=subprocess.run([tex3ds,"-f","rgba8","-o",str(packed),str(png)],
                              capture_output=True,text=True,timeout=120)
        if result.returncode or not packed.is_file() or not packed.stat().st_size:
            raise DDSError("tex3ds conversion failed: "+result.stderr[:350])
        os.replace(packed,dest)
    return {"file":str(dest),"width":target_w,"height":target_h,
            "format":"tex3ds PICA200 texture RGBA8",
            "bytes":dest.stat().st_size,
            "status":"GPU texture encoded on host; 3DS GPU upload still requires emulator/hardware validation"}
