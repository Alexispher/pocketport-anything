"""Deterministic original geometry fixture using production PPMG/PPSC serializers.

The tiny scene is redistributable and contains NO Bethesda game content.
Its .ppmg can also be compiled as a static in-memory fallback on 3DS.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from .nif import Mesh, decode_mesh, encode_mesh
from .scene import create_scene, read_scene
from .tes5 import Scan, Static, Reference


def fixture_mesh() -> Mesh:
    vertices = []
    triangles = []

    def face(points, normal):
        start = len(vertices)
        for (x,y,z), (u,v) in zip(points, ((0,0),(1,0),(1,1),(0,1))):
            vertices.append((float(x),float(y),float(z),*normal,float(u),float(v)))
        triangles.extend(((start,start+1,start+2),(start,start+2,start+3)))

    # A floor and three differently proportioned solid objects; Z is up.
    face(((-160,-160,-2),(160,-160,-2),(160,160,-2),(-160,160,-2)),(0,0,1))
    def box(cx,cy,sx,sy,height):
        x0,x1=cx-sx/2,cx+sx/2
        y0,y1=cy-sy/2,cy+sy/2
        z0,z1=0,height
        face(((x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)),(0,0,1))
        face(((x0,y0,z0),(x0,y1,z0),(x1,y1,z0),(x1,y0,z0)),(0,0,-1))
        face(((x0,y0,z0),(x1,y0,z0),(x1,y0,z1),(x0,y0,z1)),(0,-1,0))
        face(((x1,y0,z0),(x1,y1,z0),(x1,y1,z1),(x1,y0,z1)),(1,0,0))
        face(((x1,y1,z0),(x0,y1,z0),(x0,y1,z1),(x1,y1,z1)),(0,1,0))
        face(((x0,y1,z0),(x0,y0,z0),(x0,y0,z1),(x0,y1,z1)),(-1,0,0))
    box(-75,30,36,36,55)
    box(5,55,48,36,95)
    box(82,10,42,58,70)
    return Mesh(tuple(vertices),tuple(triangles),0,0)


def fixture_scene() -> bytes:
    static = Static(0x100,"PocketPortOriginalFixture","meshes/pocketport_original.nif")
    placements = (
        Reference(0x201,0x100,0x300,(-75.,30.,0.),(0.,0.,0.),1.),
        Reference(0x202,0x100,0x300,(5.,55.,0.),(0.,0.,0.),1.),
        Reference(0x203,0x100,0x300,(82.,10.,0.),(0.,0.,0.),1.),
    )
    scan=Scan({0x100:static},{0x300:"PocketPort Test Cell"},placements,5)
    data,_=create_scene(scan,cell_id=0x300)
    return data


def _c_header(mesh: Mesh) -> str:
    # Generates native vertex/index tables *from the same PPMG serialized bytes*.
    # No FILE* and no SD access are needed to run this builtin fallback.
    lines=["/* Generated from original fixture PPMG v1; do not edit. */",
           "#ifndef PP_BUILTIN_SCENE_H","#define PP_BUILTIN_SCENE_H",
           f"#define PP_BUILTIN_VERTICES {len(mesh.vertices)}u",
           f"#define PP_BUILTIN_TRIANGLES {len(mesh.triangles)}u",
           "static const PPMeshVertex pp_builtin_vertices[] = {"]
    for v in mesh.vertices:
        fields=",".join(format(float(x),".9g")+"f" if "." in format(float(x),".9g") else format(float(x),".9g")+".0f" for x in v)
        xyz,normal,uv=fields.split(",")[:3],fields.split(",")[3:6],fields.split(",")[6:]
        lines.append("{{"+",".join(xyz)+"},{"+",".join(normal)+"},{"+",".join(uv)+"}},")
    lines.extend(["};","static const PPMeshTri pp_builtin_triangles[] = {"])
    for tri in mesh.triangles:
        lines.append("{{"+",".join(str(i) for i in tri)+"}},")
    lines.extend(["};","#endif",""])
    return "\n".join(lines)


def generate(output: str | Path, *, header: str | Path | None = None) -> dict:
    root=Path(output)
    sd=root/"3ds"/"pocketport"/"skyrim"
    vertices=fixture_mesh()
    mesh=encode_mesh(vertices)
    scene=fixture_scene()
    checked=decode_mesh(mesh)
    if checked.triangles!=vertices.triangles or read_scene(scene)["count"]!=3:
        raise ValueError("Fixture failed production format roundtrip")
    sd.mkdir(parents=True,exist_ok=True)
    for filename,blob in (("mesh.ppmg",mesh),("scene.ppsc",scene)):
        path=sd/filename
        if path.is_symlink():
            raise ValueError("Refusing to overwrite symlink fixture asset")
        path.write_bytes(blob)
    if header is not None:
        h=Path(header)
        h.parent.mkdir(parents=True,exist_ok=True)
        h.write_text(_c_header(checked),encoding="utf-8")
    return {"kind":"original-fixture-not-Skyrim",
            "mesh_vertices":len(checked.vertices),
            "mesh_triangles":len(checked.triangles),
            "scene_instances":3,
            "scene_sha256":sha256(scene).hexdigest(),
            "mesh_sha256":sha256(mesh).hexdigest(),
            "sd_directory":str(sd)}


def main():
    parser=argparse.ArgumentParser(description="Generate an original 3D scene and SD-card package")
    parser.add_argument("--output",required=True)
    parser.add_argument("--header")
    args=parser.parse_args()
    print(json.dumps(generate(args.output,header=args.header),indent=2))


if __name__=="__main__":
    main()
