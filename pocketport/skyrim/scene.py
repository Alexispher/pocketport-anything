"""Compact PPSC v1 package: Skyrim REFR transforms -> native C scene reader.

Scene data contains transforms and FormIDs only. No NIF model geometry, textures
or scripts are claimed to be reconstructed; 3DS renders diagnostic markers.
"""
from __future__ import annotations
import math
import struct
from pathlib import Path
from .tes5 import Scan, Reference, scan_plugin

_HEADER = struct.Struct("<4sHHIfff")
_ROW = struct.Struct("<III7f")
MAX_INSTANCES=1024

class SceneError(ValueError):
    pass

def create_scene(scan: Scan, *, cell_id: int | None = None,
                 max_instances: int = MAX_INSTANCES) -> tuple[bytes,dict]:
    if not 1 <= max_instances <= MAX_INSTANCES:
        raise SceneError("Scene instance budget must be 1..1024")
    matches=[r for r in scan.references
             if r.base_id in scan.statics and (cell_id is None or r.cell_id==cell_id)]
    missing=sum(r.base_id not in scan.statics
                for r in scan.references if cell_id is None or r.cell_id==cell_id)
    if not matches:
        raise SceneError("No static mesh REFR records could be resolved")
    if len(matches)>max_instances:
        raise SceneError("Scene exceeds instance budget; select a single cell")
    ox,oy,oz=matches[0].position
    data=bytearray(_HEADER.pack(b"PPSC",1,0,len(matches),ox,oy,oz))
    for r in matches:
        coords=tuple(p-o for p,o in zip(r.position,(ox,oy,oz)))
        if not all(math.isfinite(v) for v in (*coords,*r.rotation,r.scale)):
            raise SceneError("Invalid instance transform")
        data.extend(_ROW.pack(r.form_id,r.base_id,r.cell_id,*coords,*r.rotation,r.scale))
    return bytes(data), {"references":len(matches),"unresolved":missing,
                         "origin":[ox,oy,oz],"cell_id":cell_id,
                         "status":"Skyrim static REFR placements serialized; NIF models NOT converted"}

def read_scene(data: bytes) -> dict:
    if len(data)<_HEADER.size:
        raise SceneError("Truncated scene header")
    magic,version,flags,count,ox,oy,oz=_HEADER.unpack_from(data)
    if magic!=b"PPSC" or version!=1 or flags!=0 or not 1<=count<=MAX_INSTANCES:
        raise SceneError("Unsupported or malformed PPSC header")
    if len(data)!=_HEADER.size+count*_ROW.size:
        raise SceneError("Incorrect scene payload length")
    rows=[]
    for i in range(count):
        values=_ROW.unpack_from(data,_HEADER.size+i*_ROW.size)
        if not all(math.isfinite(v) for v in values[3:]) or values[-1]<=0:
            raise SceneError("Non-finite scene transform or invalid scale")
        rows.append({"form_id":values[0],"base_id":values[1],"cell_id":values[2],
                     "offset":values[3:6],"rotation":values[6:9],"scale":values[9]})
    return {"origin":(ox,oy,oz),"count":count,"instances":rows}

def convert_plugin(path: str|Path,destination: str|Path, *,
                   cell_id: int|None=None) -> dict:
    scan=scan_plugin(path)
    data,report=create_scene(scan,cell_id=cell_id)
    target=Path(destination)
    if target.exists():
        raise SceneError("Refusing to overwrite existing scene output")
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(data)
    read_scene(target.read_bytes())
    report.update({"file":str(target),"package_bytes":len(data),
                   "source":"Authorized local TES5 plugin, no commercial data included in git"})
    return report
