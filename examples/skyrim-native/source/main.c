/*
 * PocketPort Skyrim — Native Citro3D 3D scene viewer for Nintendo 3DS.
 *
 * Renders converted Skyrim static-record placements or the built-in
 * original 3D test scene (a ground plane and three cubes).
 * No commercial game data is shipped.
 *
 * Root-cause fix for the "purple rectangle" rendering bug:
 *   1. Camera was at origin looking down -Z, straight at the floor → flat fill.
 *   2. Vertex positions were baked in clip-space with no view matrix.
 *   3. Scale factor 0.01 compressed geometry into a tiny cluster.
 *   4. Depth test used GPU_GEQUAL with depth-clear 0, inverting Z-order.
 *   5. Vertex colors for the floor normal (0,0,1) produced purple (0.45,0.40,1.0).
 *
 * This version implements a proper Model-View-Projection camera with:
 *   - Elevated, angled starting position showing all three cubes and floor.
 *   - Circle Pad: move horizontally (strafe + forward/back).
 *   - D-pad: look around (yaw + pitch).
 *   - L/R shoulders: move up/down.
 *   - A button: nearest scene reference diagnostic.
 *   - START: exit.
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

#define CLEAR_COLOR 0x404858FFu
#define TRANSFER (GX_TRANSFER_FLIP_VERT(0)|GX_TRANSFER_OUT_TILED(0)| \
                  GX_TRANSFER_RAW_COPY(0)|GX_TRANSFER_IN_FORMAT(GX_TRANSFER_FMT_RGBA8)| \
                  GX_TRANSFER_OUT_FORMAT(GX_TRANSFER_FMT_RGB8)|GX_TRANSFER_SCALING(GX_TRANSFER_SCALE_NO))
#define MAX_MARKERS 128u
#define MAX_DRAW_TRIANGLES 2048u

/* Interleaved vertex: position(3) + texcoord(2) + color(3) = 8 floats, 32 bytes */
typedef struct { float x,y,z, u,v, r,g,b; } Vertex;

static PPScene scene;
static PPMesh *model;
static bool has_scene = false;
static bool has_model = false;
static bool built_in  = false;
static bool scene_found = false, mesh_found = false;
static bool scene_invalid = false, mesh_invalid = false;
static bool has_texture = false;
static C3D_Tex gpu_texture;
static Vertex *vertices;
static DVLB_s *dvlb;
static shaderProgram_s shader;
static C3D_RenderTarget *target;
static int uniform_projection;
static int initialized_program = 0;

/* Camera state – the fixture scene uses Z-up; coordinates are in world units */
static float cam_x = 0.0f, cam_y = -250.0f, cam_z = 120.0f;
static float cam_yaw = 0.0f;   /* radians around Z axis (left-right) */
static float cam_pitch = -0.35f; /* radians tilt (looking slightly down) */

static u32 drawn = 0;

/* ===== Math helpers for view matrix ===== */

static void mtx_identity(C3D_Mtx *m) {
    Mtx_Identity(m);
}

/* Build a look-direction view matrix from position + yaw + pitch.
   Convention: Y-forward, X-right, Z-up (Skyrim/fixture convention).
   The PICA200 projection (Mtx_PerspTilt) expects camera -Z forward in
   eye space, so we construct the view matrix accordingly. */
static void build_view_matrix(C3D_Mtx *view) {
    float cy = cosf(cam_yaw),   sy = sinf(cam_yaw);
    float cp = cosf(cam_pitch), sp = sinf(cam_pitch);

    /* Forward direction in world space (yaw around Z, pitch around right) */
    float fx = sy * cp;
    float fy = cy * cp;
    float fz = sp;

    /* Right vector = forward × world_up (0,0,1), then normalize */
    float rx =  cy;
    float ry = -sy;
    float rz =  0.0f;

    /* Up vector = right × forward */
    float ux = ry * fz - rz * fy;
    float uy = rz * fx - rx * fz;
    float uz = rx * fy - ry * fx;

    /* View matrix: rows are right/up/(-forward) dotted with -position */
    mtx_identity(view);
    /* Row 0: right */
    view->r[0].x = rx;   view->r[0].y = ry;   view->r[0].z = rz;
    view->r[0].w = -(rx * cam_x + ry * cam_y + rz * cam_z);
    /* Row 1: up */
    view->r[1].x = ux;   view->r[1].y = uy;   view->r[1].z = uz;
    view->r[1].w = -(ux * cam_x + uy * cam_y + uz * cam_z);
    /* Row 2: -forward (camera looks down -Z in eye space) */
    view->r[2].x = -fx;  view->r[2].y = -fy;  view->r[2].z = -fz;
    view->r[2].w = -(-fx * cam_x + (-fy) * cam_y + (-fz) * cam_z);
    /* Row 3: 0 0 0 1 (already from identity) */
}

/* Multiply two 4x4 matrices: out = a * b. Can alias. */
static void mtx_multiply(C3D_Mtx *out, const C3D_Mtx *a, const C3D_Mtx *b) {
    C3D_Mtx tmp;
    Mtx_Multiply(&tmp, a, b);
    *out = tmp;
}

/* ===== Resource loading ===== */

static void shutdown_scene(void) {
    if (vertices) { linearFree(vertices); vertices = NULL; }
    if (initialized_program) { shaderProgramFree(&shader); initialized_program = 0; }
    if (dvlb) { DVLB_Free(dvlb); dvlb = NULL; }
    if (model) { free(model); model = NULL; }
    if (has_texture) { C3D_TexDelete(&gpu_texture); has_texture = false; }
    C3D_Fini();
    gfxExit();
}

static bool load_scene(void) {
    FILE *f = fopen("sdmc:/3ds/pocketport/skyrim/scene.ppsc", "rb");
    scene_found = f != NULL;
    if (!f) return false;
    int ok = pp_scene_read(f, &scene);
    fclose(f);
    scene_invalid = ok == 0;
    return ok != 0;
}

static bool load_mesh(void) {
    FILE *f = fopen("sdmc:/3ds/pocketport/skyrim/mesh.ppmg", "rb");
    mesh_found = f != NULL;
    if (!f) return false;
    model = (PPMesh*)malloc(sizeof(PPMesh));
    if (!model) { fclose(f); return false; }
    int valid = pp_mesh_read(f, model);
    fclose(f);
    if (!valid) { free(model); model = NULL; mesh_invalid = true; return false; }
    return true;
}

static bool load_builtin_mesh(void) {
    if (PP_BUILTIN_VERTICES > PP_MAX_MESH_VERTICES || PP_BUILTIN_TRIANGLES > PP_MAX_MESH_TRIANGLES)
        return false;
    model = (PPMesh*)malloc(sizeof(PPMesh));
    if (!model) return false;
    memset(model, 0, sizeof(*model));
    model->vertex_count   = PP_BUILTIN_VERTICES;
    model->triangle_count = PP_BUILTIN_TRIANGLES;
    memcpy(model->vertices,  pp_builtin_vertices,  sizeof(pp_builtin_vertices));
    memcpy(model->triangles, pp_builtin_triangles, sizeof(pp_builtin_triangles));
    built_in  = true;
    has_model = true;
    return true;
}

static bool load_texture(void) {
    FILE *f = fopen("sdmc:/3ds/pocketport/skyrim/texture.t3x", "rb");
    if (!f) return false;
    Tex3DS_Texture packed = Tex3DS_TextureImportStdio(f, &gpu_texture, NULL, false);
    fclose(f);
    if (!packed) return false;
    Tex3DS_TextureFree(packed);
    C3D_TexSetFilter(&gpu_texture, GPU_LINEAR, GPU_NEAREST);
    C3D_TexBind(0, &gpu_texture);
    return true;
}

/* ===== GPU initialization ===== */

static bool begin_scene(void) {
    if (!C3D_Init(C3D_DEFAULT_CMDBUF_SIZE)) return false;
    target = C3D_RenderTargetCreate(240, 400, GPU_RB_RGBA8, GPU_RB_DEPTH24_STENCIL8);
    if (!target) return false;
    C3D_RenderTargetSetOutput(target, GFX_TOP, GFX_LEFT, TRANSFER);

    if (pp_vshader_size < 4) return false;
    dvlb = DVLB_ParseFile((u32*)pp_vshader, pp_vshader_size);
    if (!dvlb) return false;
    shaderProgramInit(&shader);
    initialized_program = 1;
    if (shaderProgramSetVsh(&shader, &dvlb->DVLE[0]) != 0) return false;
    C3D_BindProgram(&shader);

    uniform_projection = shaderInstanceGetUniformLocation(shader.vertexShader, "projection");
    if (uniform_projection < 0) return false;

    /* Vertex attributes: pos(3f), uv(2f), color(3f) */
    C3D_AttrInfo *attr = C3D_GetAttrInfo();
    AttrInfo_Init(attr);
    AttrInfo_AddLoader(attr, 0, GPU_FLOAT, 3);  /* v0: position */
    AttrInfo_AddLoader(attr, 1, GPU_FLOAT, 2);  /* v1: texcoord */
    AttrInfo_AddLoader(attr, 2, GPU_FLOAT, 3);  /* v2: color    */

    /* Vertex buffer */
    C3D_BufInfo *buffer = C3D_GetBufInfo();
    BufInfo_Init(buffer);
    vertices = (Vertex*)linearAlloc(MAX_DRAW_TRIANGLES * 3 * sizeof(Vertex));
    if (!vertices) return false;
    BufInfo_Add(buffer, vertices, sizeof(Vertex), 3, 0x210);

    /* Texture environment: use vertex color (or modulate with texture) */
    C3D_TexEnv *env = C3D_GetTexEnv(0);
    C3D_TexEnvInit(env);
    if (has_model && !built_in)
        has_texture = load_texture();
    C3D_TexEnvSrc(env, C3D_Both, has_texture ? GPU_TEXTURE0 : GPU_PRIMARY_COLOR,
                  GPU_PRIMARY_COLOR, 0);
    C3D_TexEnvFunc(env, C3D_Both, has_texture ? GPU_MODULATE : GPU_REPLACE);
    C3D_FixedAttribSet(1, 1.0f, 1.0f, 1.0f, 1.0f);

    return true;
}

/* ===== Per-object vertex colors ===== */

/* Distinct bright colors for the floor and each cube so geometry is recognizable. */
static void object_color(float normal[3], int tri_index, float *r, float *g, float *b) {
    /* floor: tri 0..1 (normal Z up), cubes start at tri 2 */
    /* The fixture has: floor=2 tris, cube1=12 tris (idx 2-13),
       cube2=12 tris (idx 14-25), cube3=12 tris (idx 26-37) */
    if (tri_index < 2) {
        /* Floor: earthy green */
        *r = 0.25f; *g = 0.55f; *b = 0.20f;
    } else if (tri_index < 14) {
        /* Cube 1: red-ish with normal shading */
        *r = 0.85f + fabsf(normal[0]) * 0.15f;
        *g = 0.20f + fabsf(normal[1]) * 0.15f;
        *b = 0.15f + fabsf(normal[2]) * 0.15f;
    } else if (tri_index < 26) {
        /* Cube 2: blue with normal shading */
        *r = 0.15f + fabsf(normal[0]) * 0.15f;
        *g = 0.30f + fabsf(normal[1]) * 0.15f;
        *b = 0.85f + fabsf(normal[2]) * 0.15f;
    } else {
        /* Cube 3: yellow/gold with normal shading */
        *r = 0.90f + fabsf(normal[0]) * 0.10f;
        *g = 0.75f + fabsf(normal[1]) * 0.10f;
        *b = 0.10f + fabsf(normal[2]) * 0.10f;
    }

    /* Apply simple directional lighting: dot(normal, light_dir) */
    /* Light from upper-right-front */
    float lx = 0.4f, ly = -0.6f, lz = 0.7f;
    float dot = normal[0]*lx + normal[1]*ly + normal[2]*lz;
    float ambient = 0.45f;
    float diffuse = dot > 0.0f ? dot * 0.55f : 0.0f;
    float shade = ambient + diffuse;
    if (shade > 1.0f) shade = 1.0f;
    *r *= shade;
    *g *= shade;
    *b *= shade;
}

/* ===== Geometry upload (world-space positions, GPU transforms via MVP) ===== */

static void redraw_mesh(void) {
    drawn = model->triangle_count < MAX_DRAW_TRIANGLES ?
            model->triangle_count : MAX_DRAW_TRIANGLES;
    for (u32 i = 0; i < drawn; i++) {
        for (u32 j = 0; j < 3; j++) {
            const PPMeshVertex *v = &model->vertices[model->triangles[i].v[j]];
            float cr, cg, cb;
            if (built_in || model->triangle_count <= 38) {
                float n[3] = { v->normal[0], v->normal[1], v->normal[2] };
                object_color(n, (int)i, &cr, &cg, &cb);
            } else {
                /* Generic directional lighting for arbitrary meshes */
                float lx = 0.4f, ly = -0.6f, lz = 0.7f;
                float dot = v->normal[0]*lx + v->normal[1]*ly + v->normal[2]*lz;
                float ambient = 0.35f;
                float diffuse = dot > 0.0f ? dot * 0.65f : 0.0f;
                float shade = ambient + diffuse;
                if (shade > 1.0f) shade = 1.0f;
                cr = (0.50f + fabsf(v->normal[0]) * 0.45f) * shade;
                cg = (0.45f + fabsf(v->normal[1]) * 0.45f) * shade;
                cb = (0.55f + fabsf(v->normal[2]) * 0.40f) * shade;
            }
            /* Write world-space position; MVP transform happens on GPU */
            vertices[i*3+j] = (Vertex){
                v->xyz[0], v->xyz[1], v->xyz[2],
                v->uv[0], v->uv[1],
                cr, cg, cb
            };
        }
    }
    GSPGPU_FlushDataCache(vertices, drawn * 3 * sizeof(Vertex));
}

static void redraw_markers(void) {
    drawn = scene.count < MAX_MARKERS ? scene.count : MAX_MARKERS;
    for (u32 i = 0; i < drawn; i++) {
        const PPSceneRef *r = &scene.refs[i];
        float x = r->offset[0];
        float y = r->offset[1];
        float z = r->offset[2];
        float size = 8.0f;
        vertices[i*3+0] = (Vertex){ x - size, y,        z,        0, 0, 0.9f, 0.6f, 0.3f };
        vertices[i*3+1] = (Vertex){ x + size, y,        z,        0, 0, 0.9f, 0.6f, 0.3f };
        vertices[i*3+2] = (Vertex){ x,        y + size, z + size, 0, 0, 0.9f, 0.6f, 0.3f };
    }
    GSPGPU_FlushDataCache(vertices, drawn * 3 * sizeof(Vertex));
}

/* ===== Main loop ===== */

int main(void) {
    gfxInitDefault();
    consoleDebugInit(debugDevice_SVC);
    consoleInit(GFX_BOTTOM, NULL);
    fprintf(stderr, "[PocketPort] Skyrim native Citro3D runtime starting\n");
    printf("PocketPort Skyrim model viewer\n");
    printf("BSTriShape and placement diagnostics\n");

    has_scene = load_scene();
    has_model = load_mesh();

    fprintf(stderr, "[PocketPort] PPSC: %s, PPMG: %s\n",
            !scene_found ? "not found" : (scene_invalid ? "invalid" : "valid"),
            !mesh_found ? "not found" : (mesh_invalid ? "invalid" : "valid"));
    printf("PPSC: %s\n", !scene_found ? "not found" : (scene_invalid ? "invalid" : "valid"));
    printf("PPMG: %s\n", !mesh_found ? "not found" : (mesh_invalid ? "invalid" : "valid"));

    if (!has_model) {
        if (!load_builtin_mesh()) {
            fprintf(stderr, "[PocketPort] FATAL: Out of RAM: builtin scene unavailable\n");
            printf("Out of RAM: builtin scene unavailable\n");
            gfxExit();
            return 2;
        }
        fprintf(stderr, "[PocketPort] Built-in 3D Test Scene loaded (%u verts, %u tris)\n",
                (unsigned)model->vertex_count, (unsigned)model->triangle_count);
        printf("PocketPort - Built-in 3D Test Scene\n");
        printf("Original fixture: ground and 3 cubes\n");
    }
    if (has_model) {
        fprintf(stderr, "[PocketPort] Geometry loaded: %lu vertices, %lu triangles\n",
                (unsigned long)model->vertex_count, (unsigned long)model->triangle_count);
        printf("Geometry: %lu vertices, %lu triangles\n",
               (unsigned long)model->vertex_count, (unsigned long)model->triangle_count);
    }
    printf("Validated references: %lu\n", (unsigned long)scene.count);
    if (has_model)
        printf("Actual mesh triangles: %lu\n", (unsigned long)model->triangle_count);
    if (!has_model)
        printf("Showing PPSC markers only\n");

    if (!begin_scene()) {
        fprintf(stderr, "[PocketPort] FATAL: Citro3D initialization failed\n");
        printf("Citro3D initialization failed\n");
        shutdown_scene();
        return 2;
    }
    fprintf(stderr, "[PocketPort] Citro3D initialized successfully. Camera: (%.1f, %.1f, %.1f), pitch: %.2f\n",
            cam_x, cam_y, cam_z, cam_pitch);

    printf("Circle Pad: move | D-pad: look\n");
    printf("L/R: up/down | START: exit\n");
    printf("GPU texture loaded: %s\n", has_texture ? "yes" : "no");
    printf("A: nearest static reference\n");
    printf("Camera: %.0f, %.0f, %.0f\n", cam_x, cam_y, cam_z);

    /* Projection matrix — perspective with correct 3DS aspect and tilt */
    C3D_Mtx projection;
    Mtx_PerspTilt(&projection, C3D_AngleFromDegrees(65.0f),
                  C3D_AspectRatioTop, 1.0f, 5000.0f, false);

    /* Disable backface culling so both sides of triangles are visible */
    C3D_CullFace(GPU_CULL_NONE);

    /* Depth test: PICA200/citro3d clears depth to 0 (far plane) with Mtx_PerspTilt(false).
       Incoming closer geometry has higher depth, so GPU_GREATER is required. */
    C3D_DepthTest(true, GPU_GREATER, GPU_WRITE_ALL);

    while (aptMainLoop()) {
        hidScanInput();
        u32 down = hidKeysDown(), held = hidKeysHeld();
        if (down & KEY_START) break;

        /* Circle pad → movement in the horizontal plane */
        circlePosition pad = {0};
        hidCircleRead(&pad);
        float move_speed = 3.0f;
        float look_speed = 0.03f;

        /* Forward/back (pad Y) and strafe (pad X) */
        float fwd_x = sinf(cam_yaw);
        float fwd_y = cosf(cam_yaw);
        float right_x = cosf(cam_yaw);
        float right_y = -sinf(cam_yaw);

        cam_x += (fwd_x * (float)pad.dy + right_x * (float)pad.dx) * move_speed * 0.02f;
        cam_y += (fwd_y * (float)pad.dy + right_y * (float)pad.dx) * move_speed * 0.02f;

        /* D-pad → look around */
        if (held & KEY_LEFT)  cam_yaw   += look_speed;
        if (held & KEY_RIGHT) cam_yaw   -= look_speed;
        if (held & KEY_UP)    cam_pitch += look_speed * 0.7f;
        if (held & KEY_DOWN)  cam_pitch -= look_speed * 0.7f;

        /* Clamp pitch to avoid gimbal issues */
        if (cam_pitch >  1.4f) cam_pitch =  1.4f;
        if (cam_pitch < -1.4f) cam_pitch = -1.4f;

        /* Shoulder buttons → vertical movement */
        if (held & KEY_R) cam_z += move_speed;
        if (held & KEY_L) cam_z -= move_speed;

        /* A → nearest reference */
        if (down & KEY_A) {
            int idx = pp_scene_nearest(&scene, cam_x, cam_y, cam_z, 500.0f);
            printf("Nearest ref: %d  Cam: %.0f,%.0f,%.0f\n", idx, cam_x, cam_y, cam_z);
        }

        /* Upload geometry in world-space coordinates */
        if (has_model) redraw_mesh();
        else           redraw_markers();

        /* Build model-view-projection matrix */
        C3D_Mtx view, mvp;
        build_view_matrix(&view);
        mtx_multiply(&mvp, &projection, &view);

        /* Render */
        C3D_FrameBegin(C3D_FRAME_SYNCDRAW);
        C3D_RenderTargetClear(target, C3D_CLEAR_ALL, CLEAR_COLOR, 0);
        C3D_FrameDrawOn(target);
        C3D_FVUnifMtx4x4(GPU_VERTEX_SHADER, uniform_projection, &mvp);
        C3D_DrawArrays(GPU_TRIANGLES, 0, drawn * 3);
        C3D_FrameEnd(0);
    }

    shutdown_scene();
    return 0;
}
