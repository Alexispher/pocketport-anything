#include "pp_mesh.h"
#include <math.h>
#include <string.h>

static int take(FILE *f, unsigned char *ptr, size_t n) {
    return fread(ptr,1,n,f)==n;
}
static uint16_t rd16(const unsigned char *p) {
    return (uint16_t)((uint16_t)p[0]|((uint16_t)p[1]<<8));
}
static uint32_t rd32(const unsigned char *p) {
    return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
static float rdfloat(const unsigned char *p) {
    uint32_t bits=rd32(p);
    float value;
    memcpy(&value,&bits,4);
    return value;
}
int pp_mesh_read(FILE *f, PPMesh *out) {
    unsigned char header[16], row[32], tri[6];
    uint32_t i,j,nv,nt;
    if (!f || !out || sizeof(float)!=4) return 0;
    memset(out,0,sizeof(*out));
    if (!take(f,header,sizeof(header)) || memcmp(header,"PPMG",4)
        || rd16(header+4)!=1 || rd16(header+6)!=0) return 0;
    nv=rd32(header+8);
    nt=rd32(header+12);
    if (nv<3 || nv>PP_MAX_MESH_VERTICES || nt<1 || nt>PP_MAX_MESH_TRIANGLES) return 0;
    for (i=0;i<nv;i++) {
        if (!take(f,row,sizeof(row))) goto fail;
        for(j=0;j<3;j++) {
            out->vertices[i].xyz[j]=rdfloat(row+j*4);
            out->vertices[i].normal[j]=rdfloat(row+12+j*4);
            if(!isfinite(out->vertices[i].xyz[j]) || !isfinite(out->vertices[i].normal[j])) goto fail;
        }
        for(j=0;j<2;j++) {
            out->vertices[i].uv[j]=rdfloat(row+24+j*4);
            if(!isfinite(out->vertices[i].uv[j])) goto fail;
        }
    }
    for(i=0;i<nt;i++) {
        if (!take(f,tri,sizeof(tri))) goto fail;
        for(j=0;j<3;j++) {
            uint16_t index=rd16(tri+2*j);
            if(index>=nv) goto fail;
            out->triangles[i].v[j]=index;
        }
    }
    if(fgetc(f)!=EOF || ferror(f)) goto fail;
    out->vertex_count=nv;
    out->triangle_count=nt;
    return 1;
fail:
    out->vertex_count=0;
    out->triangle_count=0;
    return 0;
}
