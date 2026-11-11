/* Original Star Catcher gameplay with reusable dual-screen native UI.
   Top: original gameplay; bottom: independent Citro2D UI and touch controls. */
#include <3ds.h>
#include <citro2d.h>
#include <stdint.h>
#include <stdio.h>
#include "pp_game.h"
#include "pp_runtime.h"
#include "pp_ui.h"
#include "pp_display_3ds.h"
#include "pp_display_profile_generated.h"

#define CELL 16.0f
static void rectangle(float x,float y,float w,float h,u32 color) {
    C2D_DrawRectSolid(x,y,0.0f,w,h,color);
}

static void draw_game(const PPGame *game) {
    rectangle(35,15,330,205,C2D_Color32(24,33,63,255));
    rectangle(36+(float)game->player_x*CELL,15+(PP_GAME_H-1)*CELL,
              14,12,C2D_Color32(80,224,245,255));
    rectangle(36+(float)game->star_x*CELL,15+(float)game->star_y*CELL,
              12,12,C2D_Color32(255,212,59,255));
    if(game->game_over)
        rectangle(35,15,330,12,C2D_Color32(239,83,93,255));
}

int main(int argc,char **argv) {
    PPDisplay display;
    PPUIState ui;
    PPGame game;
    unsigned old_score=0u;
    (void)argc;(void)argv;
    if(!pp_display_init(&display)) {
        /* pp_display_init releases all partial graphics allocations. */
        return 1;
    }
    pp_game_init(&game,2026u);
    pp_ui_init(&ui,PP_PROFILE_ENABLED_PAGES,PP_PROFILE_INITIAL_PAGE);
    pp_ui_message(&ui,"Collect falling stars",180);
    while(aptMainLoop()) {
        u32 down,held;
        circlePosition circle={0};
        touchPosition touch={0};
        PPUIInput input;
        PPUIResult result;
        PPHUD hud;
        hidScanInput();
        down=hidKeysDown();
        held=hidKeysHeld();
        if(down & KEY_START)break; /* preserve original 3DS exit mapping */
        hidCircleRead(&circle);
        if(held & KEY_TOUCH)hidTouchRead(&touch);
        input=pp_input_3ds(down,held,touch,circle);
        if(!PP_PROFILE_TOUCH_ENABLED)input.touch_active=0;
        result=pp_ui_step(&ui,&input);
        if(result.actions & PP_UI_ACTION_RESTART)
            pp_game_init(&game,game.rng);
        else if(result.gameplay_allowed) {
            unsigned move=0u;
            if((held & KEY_DLEFT) || circle.dx < -40)move|=PP_INPUT_LEFT;
            if((held & KEY_DRIGHT) || circle.dx > 40)move|=PP_INPUT_RIGHT;
            pp_game_step(&game,move);
        }
        if(game.score>old_score)pp_ui_message(&ui,"Star collected!",150);
        old_score=game.score;
        hud.title="Star Catcher";
        hud.primary_value=game.score;
        hud.secondary_value=game.missed;
        hud.secondary_max=3;
        hud.ticks=game.ticks;
        hud.game_over=game.game_over;
        hud.player_x=game.player_x;
        hud.item_x=game.star_x;
        hud.item_y=game.star_y;
        hud.grid_w=PP_GAME_W;
        hud.grid_h=PP_GAME_H;
        if(!pp_display_begin(&display))break;
        pp_display_top(&display);
        draw_game(&game);
        pp_display_bottom(&display,&ui,&hud);
        pp_display_end(&display);
    }
    pp_display_shutdown(&display);
    return 0;
}
