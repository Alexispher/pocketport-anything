#include "pp_scene.h"
#include <math.h>
#include <string.h>

static int take(FILE *f, unsigned char *out, size_t size) {
    return fread(out, 1, size, f) == size;
}
static uint16_t get16(const unsigned char *p) {
    return (uint16_t)((uint16_t)p[0] | ((uint16_t)p[1] << 8));
}
static uint32_t get32(const unsigned char *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}
static float getfloat(const unsigned char *p) {
    uint32_t raw = get32(p);
    float v;
    memcpy(&v, &raw, sizeof(v));
    return v;
}
int pp_scene_read(FILE *f, PPScene *scene) {
    unsigned char header[24], row[40];
    uint32_t count, i, j;
    int trailing;
    if (!f || !scene || sizeof(float) != 4) return 0;
    memset(scene, 0, sizeof(*scene));
    if (!take(f, header, sizeof(header))) return 0;
    if (memcmp(header, "PPSC", 4) || get16(header+4) != 1 ||
        get16(header+6) != 0) return 0;
    count = get32(header+8);
    if (count == 0 || count > PP_SKYRIM_MAX_REFS) return 0;
    for (j = 0; j < 3; ++j) {
        scene->origin[j] = getfloat(header + 12 + j*4);
        if (!isfinite(scene->origin[j])) return 0;
    }
    for (i = 0; i < count; ++i) {
        PPSceneRef *v = &scene->refs[i];
        if (!take(f, row, sizeof(row))) goto fail;
        v->form_id = get32(row);
        v->base_id = get32(row+4);
        v->cell_id = get32(row+8);
        for (j = 0; j < 3; ++j) {
            v->offset[j] = getfloat(row+12+4*j);
            v->rotation[j] = getfloat(row+24+4*j);
            if (!isfinite(v->offset[j]) || !isfinite(v->rotation[j])) goto fail;
        }
        v->scale = getfloat(row+36);
        if (!isfinite(v->scale) || v->scale <= 0.0f) goto fail;
    }
    trailing = fgetc(f);
    if (trailing != EOF || ferror(f)) goto fail;
    scene->count = count;
    return 1;
fail:
    memset(scene, 0, sizeof(*scene));
    return 0;
}
int pp_scene_nearest(const PPScene *scene, float x, float y, float z, float radius) {
    uint32_t i;
    float best, distance;
    int selected = -1;
    if (!scene || !isfinite(radius) || radius <= 0 || !isfinite(x)
        || !isfinite(y) || !isfinite(z)) return -1;
    best = radius * radius;
    if (!isfinite(best)) return -1;
    for (i = 0; i < scene->count && i < PP_SKYRIM_MAX_REFS; ++i) {
        float dx = scene->refs[i].offset[0] - x;
        float dy = scene->refs[i].offset[1] - y;
        float dz = scene->refs[i].offset[2] - z;
        distance = dx*dx + dy*dy + dz*dz;
        if (distance < best) {
            best = distance;
            selected = (int)i;
        }
    }
    return selected;
}
