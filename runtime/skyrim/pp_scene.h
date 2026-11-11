#ifndef POCKETPORT_SKYRIM_SCENE_H
#define POCKETPORT_SKYRIM_SCENE_H
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>

#define PP_SKYRIM_MAX_REFS 1024u
typedef struct {
    uint32_t form_id, base_id, cell_id;
    float offset[3];
    float rotation[3];
    float scale;
} PPSceneRef;
typedef struct {
    float origin[3];
    uint32_t count;
    PPSceneRef refs[PP_SKYRIM_MAX_REFS];
} PPScene;

/* Returns 1 only for a complete validated little-endian PPSC v1 file.
   Caller owns scene; no allocations occur inside pp_scene_read. */
int pp_scene_read(FILE *stream, PPScene *scene);
/* Nearest reference within radius, or -1; diagnostic interaction only. */
int pp_scene_nearest(const PPScene *scene, float x, float y, float z, float radius);
#endif
