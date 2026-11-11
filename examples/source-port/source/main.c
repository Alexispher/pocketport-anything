/* Star Catcher: playable 3DS frontend for the same core tested on the host. */
#include <3ds.h>
#include <citro2d.h>
#include <stdio.h>
#include "pp_game.h"
#include "pp_runtime.h"

#define WIDTH 400
#define HEIGHT 240
#define CELL 16.0f

static void rectangle(float x, float y, float w, float h, u32 color) {
    C2D_DrawRectSolid(x, y, 0.0f, w, h, color);
}

int main(int argc, char **argv) {
    (void)argc; (void)argv;
    gfxInitDefault();
    consoleInit(GFX_BOTTOM, NULL);
    if (!C3D_Init(C3D_DEFAULT_CMDBUF_SIZE)) { gfxExit(); return 1; }
    if (!C2D_Init(C2D_DEFAULT_MAX_OBJECTS)) { C3D_Fini(); gfxExit(); return 1; }
    C2D_Prepare();
    C3D_RenderTarget *top = C2D_CreateScreenTarget(GFX_TOP, GFX_LEFT);
    if (!top) { C2D_Fini(); C3D_Fini(); gfxExit(); return 1; }
    PPInputBindings bindings = {KEY_DLEFT, KEY_DRIGHT, KEY_B, KEY_START};
    PPGame game;
    pp_game_init(&game, 2026u);
    puts("Star Catcher (original game)");
    puts("D-pad or Circle Pad: move");
    puts("B: restart  START: exit");
    puts("Collect stars; three misses end run.");
    while (aptMainLoop()) {
        hidScanInput();
        u32 held = hidKeysHeld();
        u32 down = hidKeysDown();
        circlePosition circle;
        hidCircleRead(&circle);
        if (down & KEY_START) break;
        unsigned mapped = pp_map_input((held & (KEY_DLEFT | KEY_DRIGHT)) | (down & (KEY_B | KEY_START)), &bindings);
        unsigned input = 0;
        if ((mapped & PP_BUTTON_LEFT) || circle.dx < -40) input |= PP_INPUT_LEFT;
        if ((mapped & PP_BUTTON_RIGHT) || circle.dx > 40) input |= PP_INPUT_RIGHT;
        if (mapped & PP_BUTTON_ACTION) input |= PP_INPUT_RESTART;
        pp_game_step(&game, input);
        C3D_FrameBegin(C3D_FRAME_SYNCDRAW);
        C2D_TargetClear(top, C2D_Color32(12, 18, 38, 255));
        C2D_SceneBegin(top);
        rectangle(35, 15, 330, 205, C2D_Color32(24, 33, 63, 255));
        rectangle(36 + (float)game.player_x * CELL, 15 + (PP_GAME_H - 1) * CELL,
                  14, 12, C2D_Color32(80, 224, 245, 255));
        rectangle(36 + (float)game.star_x * CELL, 15 + (float)game.star_y * CELL,
                  12, 12, C2D_Color32(255, 212, 59, 255));
        if (game.game_over) rectangle(35, 15, 330, 12, C2D_Color32(239, 83, 93, 255));
        C3D_FrameEnd(0);
        /* Status console updates only once per second to avoid per-frame output. */
        if (game.ticks % 60u == 0u) {
            printf("\x1b[6;1HScore: %-8lu Missed: %u/3   ",
                   (unsigned long)game.score, game.missed);
        }
    }
    C2D_Fini();
    C3D_Fini();
    gfxExit();
    return 0;
}
