/*
 * PocketPort Skyrim 2011 REFR placement visualizer for Nintendo 3DS.
 * Reads converted Skyrim static-record placements from SD, no game data shipped.
 * This displays diagnostic marker triangles, NOT original Skyrim meshes/gameplay.
 */
#include <3ds.h>
#include <citro3d.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../../../runtime/skyrim/pp_scene.h"

extern const unsigned char pp_vshader[];
extern const uint32_t pp_vshader_size;

#define CLEAR_COLOR 0x182431FFu
#define TRANSFER (GX_TRANSFER_FLIP_VERT(0)|GX_TRANSFER_OUT_TILED(0)| \
                  GX_TRANSFER_RAW_COPY(0)|GX_TRANSFER_IN_FORMAT(GX_TRANSFER_FMT_RGBA8)| \
                  GX_TRANSFER_OUT_FORMAT(GX_TRANSFER_FMT_RGB8)|GX_TRANSFER_SCALING(GX_TRANSFER_SCALE_NO))
#define MAX_MARKERS 128u
typedef struct {float x,y,z;} Vertex;
static PPScene scene;
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
    C3D_Fini();
    gfxExit();
}

static bool load_scene(void) {
    FILE *f=fopen("sdmc:/3ds/pocketport/skyrim/scene.ppsc","rb");
    if (!f) return false;
    int ok=pp_scene_read(f,&scene);
    fclose(f);
    return ok!=0;
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
    C3D_BufInfo *buffer=C3D_GetBufInfo();
    BufInfo_Init(buffer);
    vertices=(Vertex*)linearAlloc(MAX_MARKERS*3*sizeof(Vertex));
    if (!vertices) return false;
    BufInfo_Add(buffer,vertices,sizeof(Vertex),1,0x0);
    C3D_TexEnv *env=C3D_GetTexEnv(0);
    C3D_TexEnvInit(env);
    C3D_TexEnvSrc(env,C3D_Both,GPU_PRIMARY_COLOR,0,0);
    C3D_TexEnvFunc(env,C3D_Both,GPU_REPLACE);
    C3D_FixedAttribSet(1,1.0f,1.0f,1.0f,1.0f);
    return true;
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
        vertices[i*3+0]=(Vertex){x-size,y-size,z};
        vertices[i*3+1]=(Vertex){x+size,y-size,z};
        vertices[i*3+2]=(Vertex){x,y+size,z};
    }
    GSPGPU_FlushDataCache(vertices, drawn*3*sizeof(Vertex));
}
int main(void) {
    gfxInitDefault();
    consoleInit(GFX_BOTTOM,NULL);
    printf("PocketPort Skyrim 2011\n");
    printf("Static placements diagnostic\n");
    printf("No NIF mesh support yet\n");
    if (!load_scene()) {
        printf("Missing/invalid scene.ppsc\n");
        printf("Use converter on PC; put file at\n");
        printf("/3ds/pocketport/skyrim/\n");
        printf("START to exit\n");
        while(aptMainLoop()){
            hidScanInput();
            if(hidKeysDown()&KEY_START)break;
            gspWaitForVBlank();
        }
        gfxExit();
        return 1;
    }
    printf("Validated references: %lu\n",(unsigned long)scene.count);
    if(!begin_scene()){
        printf("Citro3D initialization failed\n");
        shutdown_scene();
        return 2;
    }
    printf("D-pad: move camera / START: exit\n");
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
        if(held&KEY_LEFT)camera_x-=1.5f;
        if(held&KEY_RIGHT)camera_x+=1.5f;
        if(held&KEY_UP)camera_y+=1.5f;
        if(held&KEY_DOWN)camera_y-=1.5f;
        if(down&KEY_A){
            int idx=pp_scene_nearest(&scene,camera_x,camera_y,camera_z,500.0f);
            printf("Nearest reference index: %d\n",idx);
        }
        redraw_markers();
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
