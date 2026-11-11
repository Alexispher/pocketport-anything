/* Original Nintendo 3DS input + rendering + RomFS sample (not a game port). */
#include <3ds.h>
#include <citro2d.h>
#include <stdio.h>

int main(int argc, char **argv) {
    (void)argc; (void)argv;
    gfxInitDefault();
    consoleInit(GFX_BOTTOM, NULL);
    if (!C3D_Init(C3D_DEFAULT_CMDBUF_SIZE)) { gfxExit(); return 1; }
    if (!C2D_Init(C2D_DEFAULT_MAX_OBJECTS)) { C3D_Fini(); gfxExit(); return 1; }
    C2D_Prepare();
    C3D_RenderTarget *top = C2D_CreateScreenTarget(GFX_TOP, GFX_LEFT);
    if (!top) { C2D_Fini(); C3D_Fini(); gfxExit(); return 1; }
    int x = 170, y = 100;
    printf("PocketPort native example\nA: change color; Circle Pad: move\nSTART: exit\n");
    if (R_SUCCEEDED(romfsInit())) {
        FILE *file = fopen("romfs:/message.txt", "r");
        if (file) {
            char line[100];
            if (fgets(line, sizeof(line), file)) printf("RomFS: %s", line);
            fclose(file);
        } else puts("RomFS: message not found");
        romfsExit();
    } else puts("RomFS unavailable");
    u32 color = C2D_Color32(88, 208, 252, 255);
    while (aptMainLoop()) {
        hidScanInput();
        u32 down = hidKeysDown();
        circlePosition circle;
        hidCircleRead(&circle);
        if (down & KEY_START) break;
        if (down & KEY_A) color = C2D_Color32(255, 202, 69, 255);
        if (circle.dx > 35 && x < 355) x += 2;
        if (circle.dx < -35 && x > 0) x -= 2;
        if (circle.dy > 35 && y > 0) y -= 2;
        if (circle.dy < -35 && y < 205) y += 2;
        C3D_FrameBegin(C3D_FRAME_SYNCDRAW);
        C2D_TargetClear(top, C2D_Color32(16, 22, 43, 255));
        C2D_SceneBegin(top);
        C2D_DrawRectSolid((float)x, (float)y, 0, 44, 36, color);
        C3D_FrameEnd(0);
    }
    C2D_Fini(); C3D_Fini(); gfxExit();
    return 0;
}
