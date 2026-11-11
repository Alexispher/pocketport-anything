/*
 * PocketPort Skyrim 2011 REFR placement visualizer for Nintendo 3DS.
 * Reads converted Skyrim static-record placements from SD, no game data shipped.
 * This displays diagnostic marker triangles, NOT original Skyrim meshes/gameplay.
 */
#include <3ds.h>
#include <citro3d.h>
#include <tex3ds.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../../../runtime/skyrim/pp_scene.h"
#include "../../../runtime/skyrim/pp_mesh.h"
#include "builtin_mesh.h"

extern const unsigned char pp_vshader[];
extern const uint32_t pp_vshader_size;

#define CLEAR_COLOR 0x182431FFu
#define TRANSFER (GX_TRANSFER_FLIP_VERT(0)|GX_TRANSFER_OUT_TILED(0)| \
                  GX_TRANSFER_RAW_COPY(0)|GX_TRANSFER_IN_FORMAT(GX_TRANSFER_FMT_RGBA8)| \
                  GX_TRANSFER_OUT_FORMAT(GX_TRANSFER_FMT_RGB8)|GX_TRANSFER_SCALING(GX_TRANSFER_SCALE_NO))
#define MAX_MARKERS 128u
#define MAX_DRAW_TRIANGLES 1024u
typedef struct {float x,y,z,u,v,r,g,b;} Vertex;
static PPScene scene;
static PPMesh *model;
static bool has_scene=false;
static bool has_model=false;
static bool built_in=false;
static bool scene_found=false, mesh_found=false;
static bool scene_invalid=false, mesh_invalid=false;
static bool has_texture=false;
static C3D_Tex gpu_texture;
static Vertex *vertices;
static DVLB_s *dvlb;
static shaderProgram_s shader;
static C3D_RenderTarget *target;
static int uniform_projection;
static int initialized_program=0;
static float camera_x=0.0f, camera_y=0.0f;
static float camera_z=0.0f;
static u32 drawn=0;

static void shutdown_scene(void) {
    if (vertices) {linearFree(vertices); vertices=NULL;}
    if (initialized_program) {shaderProgramFree(&shader); initialized_program=0;}
    if (dvlb) {DVLB_Free(dvlb); dvlb=NULL;}
    if (model) {free(model); model=NULL;}
    if (has_texture) {C3D_TexDelete(&gpu_texture);has_texture=false;}
    C3D_Fini();
    gfxExit();
}

static bool load_scene(void) {
    FILE *f=fopen("sdmc:/3ds/pocketport/skyrim/scene.ppsc","rb");
    scene_found=f!=NULL;
    if (!f) return false;
    int ok=pp_scene_read(f,&scene);
    fclose(f);
    scene_invalid=ok==0;
    return ok!=0;
}

static bool load_mesh(void) {
    FILE *f=fopen("sdmc:/3ds/pocketport/skyrim/mesh.ppmg","rb");
    mesh_found=f!=NULL;
    if(!f) return false;
    model=(PPMesh*)malloc(sizeof(PPMesh));
    if(!model){fclose(f);return false;}
    int valid=pp_mesh_read(f,model);
    fclose(f);
    if(!valid){free(model);model=NULL;mesh_invalid=true;return false;}
    return true;
}

static bool load_builtin_mesh(void) {
    if(PP_BUILTIN_VERTICES>PP_MAX_MESH_VERTICES || PP_BUILTIN_TRIANGLES>PP_MAX_MESH_TRIANGLES) return false;
    model=(PPMesh*)malloc(sizeof(PPMesh));
    if(!model)return false;
    memset(model,0,sizeof(*model));
    model->vertex_count=PP_BUILTIN_VERTICES;
    model->triangle_count=PP_BUILTIN_TRIANGLES;
    memcpy(model->vertices,pp_builtin_vertices,sizeof(pp_builtin_vertices));
    memcpy(model->triangles,pp_builtin_triangles,sizeof(pp_builtin_triangles));
    built_in=true;
    has_model=true;
    return true;
}

static bool load_texture(void) {
    FILE *f=fopen("sdmc:/3ds/pocketport/skyrim/texture.t3x","rb");
    if(!f) return false;
    Tex3DS_Texture packed=Tex3DS_TextureImportStdio(f,&gpu_texture,NULL,false);
    fclose(f);
    if(!packed) return false;
    Tex3DS_TextureFree(packed);
    C3D_TexSetFilter(&gpu_texture,GPU_LINEAR,GPU_NEAREST);
    C3D_TexBind(0,&gpu_texture);
    return true;
}

static bool begin_scene(void) {
    if (!C3D_Init(C3D_DEFAULT_CMDBUF_SIZE)) return false;
    target=C3D_RenderTargetCreate(240,400,GPU_RB_RGBA8,GPU_RB_DEPTH24_STENCIL8);
    if (!target) return false;
    C3D_RenderTargetSetOutput(target,GFX_TOP,GFX_LEFT,TRANSFER);
    if (pp_vshader_size < 4) return false;
    dvlb=DVLB_ParseFile((u32*)pp_vshader,pp_vshader_size);
    if (!dvlb) return false;
    shaderProgramInit(&shader);
    initialized_program=1;
    if (shaderProgramSetVsh(&shader,&dvlb->DVLE[0])!=0) return false;
    C3D_BindProgram(&shader);
    uniform_projection=shaderInstanceGetUniformLocation(shader.vertexShader,"projection");
    if (uniform_projection<0) return false;
    C3D_AttrInfo *attr=C3D_GetAttrInfo();
    AttrInfo_Init(attr);
    AttrInfo_AddLoader(attr,0,GPU_FLOAT,3);
    AttrInfo_AddLoader(attr,1,GPU_FLOAT,2);
    AttrInfo_AddLoader(attr,2,GPU_FLOAT,3);
    C3D_BufInfo *buffer=C3D_GetBufInfo();
    BufInfo_Init(buffer);
    vertices=(Vertex*)linearAlloc(MAX_DRAW_TRIANGLES*3*sizeof(Vertex));
    if (!vertices) return false;
    BufInfo_Add(buffer,vertices,sizeof(Vertex),3,0x210);
    C3D_TexEnv *env=C3D_GetTexEnv(0);
    C3D_TexEnvInit(env);
    if(has_model && !built_in) has_texture=load_texture();
    C3D_TexEnvSrc(env,C3D_Both,has_texture?GPU_TEXTURE0:GPU_PRIMARY_COLOR,GPU_PRIMARY_COLOR,0);
    C3D_TexEnvFunc(env,C3D_Both,has_texture?GPU_MODULATE:GPU_REPLACE);
    C3D_FixedAttribSet(1,1.0f,1.0f,1.0f,1.0f);
    return true;
}
static void redraw_mesh(void) {
    drawn=model->triangle_count<MAX_DRAW_TRIANGLES?
          model->triangle_count:MAX_DRAW_TRIANGLES;
    for(u32 i=0;i<drawn;i++) {
        for(u32 j=0;j<3;j++) {
            const PPMeshVertex *v=&model->vertices[model->triangles[i].v[j]];
            vertices[i*3+j]=(Vertex){
                v->xyz[0]*0.01f-camera_x*0.01f,
                v->xyz[1]*0.01f-camera_y*0.01f,
                -4.0f-v->xyz[2]*0.01f+camera_z*0.01f,
                v->uv[0], v->uv[1],
                0.45f + fabsf(v->normal[0])*0.5f,
                0.40f + fabsf(v->normal[1])*0.5f,
                0.50f + fabsf(v->normal[2])*0.5f};
        }
    }
    GSPGPU_FlushDataCache(vertices,drawn*3*sizeof(Vertex));
}
static void redraw_markers(void) {
    drawn=scene.count<MAX_MARKERS?scene.count:MAX_MARKERS;
    for(u32 i=0;i<drawn;i++){
        const PPSceneRef *r=&scene.refs[i];
        /* Skyrim reference coordinates, scaled to fit a small debug viewport.
           Coordinates are not mesh geometry. */
        float x=(r->offset[0]-camera_x)*0.01f;
        float y=(r->offset[1]-camera_y)*0.01f;
        float z=-4.0f-(r->offset[2]-camera_z)*0.01f;
        float size=0.08f;
        vertices[i*3+0]=(Vertex){x-size,y-size,z,0,0,0.9f,0.6f,0.3f};
        vertices[i*3+1]=(Vertex){x+size,y-size,z,0,0,0.9f,0.6f,0.3f};
        vertices[i*3+2]=(Vertex){x,y+size,z,0,0,0.9f,0.6f,0.3f};
    }
    GSPGPU_FlushDataCache(vertices, drawn*3*sizeof(Vertex));
}
int main(void) {
    gfxInitDefault();
    consoleInit(GFX_BOTTOM,NULL);
    printf("PocketPort Skyrim model viewer\n");
    printf("BSTriShape and placement diagnostics\n");
    has_scene=load_scene();
    has_model=load_mesh();
    printf("PPSC: %s\n",!scene_found?"not found":(scene_invalid?"invalid":"valid"));
    printf("PPMG: %s\n",!mesh_found?"not found":(mesh_invalid?"invalid":"valid"));
    if(!has_model){
        if(!load_builtin_mesh()){
            printf("Out of RAM: builtin scene unavailable\n");
            gfxExit();
            return 2;
        }
        printf("PocketPort - Built-in 3D Test Scene\n");
        printf("Original fixture: ground and 3 cubes\n");
    }
    if(has_model){
        printf("Geometry: %lu vertices, %lu triangles\n",
               (unsigned long)model->vertex_count,(unsigned long)model->triangle_count);
    }
    printf("Validated references: %lu\n",(unsigned long)scene.count);
    if(has_model)printf("Actual mesh triangles: %lu\n",(unsigned long)model->triangle_count);
    if(!has_model)printf("Showing PPSC markers only\n");
    if(!begin_scene()){
        printf("Citro3D initialization failed\n");
        shutdown_scene();
        return 2;
    }
    printf("Circle Pad/D-pad move camera\n");
    printf("START exits\n");
    printf("GPU texture loaded: %s\n",has_texture?"yes":"no");
    printf("A: nearest static reference\n");
    C3D_Mtx projection;
    Mtx_PerspTilt(&projection,C3D_AngleFromDegrees(65.0f),
                  C3D_AspectRatioTop,0.05f,2000.0f,false);
    C3D_CullFace(GPU_CULL_NONE);
    C3D_DepthTest(true,GPU_GEQUAL,GPU_WRITE_ALL);
    while(aptMainLoop()){
        hidScanInput();
        u32 down=hidKeysDown(),held=hidKeysHeld();
        if(down&KEY_START)break;
        circlePosition pad={0};
        hidCircleRead(&pad);
        camera_x += (float)pad.dx*0.02f;
        camera_y += (float)pad.dy*0.02f;
        if(held&KEY_LEFT)camera_x-=1.5f;
        if(held&KEY_RIGHT)camera_x+=1.5f;
        if(held&KEY_UP)camera_y+=1.5f;
        if(held&KEY_DOWN)camera_y-=1.5f;
        if(down&KEY_A){
            int idx=pp_scene_nearest(&scene,camera_x,camera_y,camera_z,500.0f);
            printf("Nearest reference index: %d\n",idx);
        }
        if(has_model)redraw_mesh(); else redraw_markers();
        C3D_FrameBegin(C3D_FRAME_SYNCDRAW);
        C3D_RenderTargetClear(target,C3D_CLEAR_ALL,CLEAR_COLOR,0);
        C3D_FrameDrawOn(target);
        C3D_FVUnifMtx4x4(GPU_VERTEX_SHADER,uniform_projection,&projection);
        C3D_DrawArrays(GPU_TRIANGLES,0,drawn*3);
        C3D_FrameEnd(0);
    }
    shutdown_scene();
    return 0;
}
