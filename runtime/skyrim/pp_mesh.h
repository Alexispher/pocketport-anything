#ifndef PP_SKYRIM_MESH_H
#define PP_SKYRIM_MESH_H
#include <stdio.h>
#include <stdint.h>
#define PP_MAX_MESH_VERTICES 4096u
#define PP_MAX_MESH_TRIANGLES 4096u
typedef struct { float xyz[3]; float normal[3]; float uv[2]; } PPMeshVertex;
typedef struct { uint16_t v[3]; } PPMeshTri;
typedef struct {
    uint32_t vertex_count, triangle_count;
    PPMeshVertex vertices[PP_MAX_MESH_VERTICES];
    PPMeshTri triangles[PP_MAX_MESH_TRIANGLES];
} PPMesh;
/* Validate PPMG v1, bounded vertex counts, indices and finite values. */
int pp_mesh_read(FILE *stream, PPMesh *output);
#endif
