#ifndef PP_DUAL_DISPLAY_3DS_H
#define PP_DUAL_DISPLAY_3DS_H

#include <3ds.h>
#include <citro2d.h>
#include "pp_ui.h"

typedef struct {
    C3D_RenderTarget *top;
    C3D_RenderTarget *bottom;
    C2D_TextBuf text_buffer;
    int gfx_started, c3d_started, c2d_started;
    int ready;
} PPDisplay;

typedef struct {
    const char *title;
    unsigned primary_value;    /* game-defined score */
    unsigned secondary_value;  /* game-defined misses */
    unsigned secondary_max;
    unsigned ticks;
    int game_over;
    int player_x, item_x, item_y;
    int grid_w, grid_h;
} PPHUD;

int pp_display_init(PPDisplay *display);
void pp_display_shutdown(PPDisplay *display);
int pp_display_begin(PPDisplay *display);
void pp_display_top(PPDisplay *display);
void pp_display_bottom(PPDisplay *display, const PPUIState *state, const PPHUD *hud);
void pp_display_end(PPDisplay *display);
/* Maps libctru key snapshots to portable UI keys without hardware coupling. */
PPUIInput pp_input_3ds(u32 down, u32 held, touchPosition touch,
                      circlePosition circle);
#endif
