#include "pp_display_3ds.h"
#include <stdio.h>
#include <string.h>

#define TOP_BG C2D_Color32(12,18,38,255)
#define BOT_BG C2D_Color32(11,20,36,255)
#define TEXT_COLOR C2D_Color32(236,242,250,255)
#define MUTED C2D_Color32(144,168,190,255)
#define ACCENT C2D_Color32(64,188,227,255)

static void rect(PPUIRect r,u32 col) {
    if(pp_ui_rect_valid(r)) C2D_DrawRectSolid((float)r.x,(float)r.y,0.0f,
                                              (float)r.width,(float)r.height,col);
}
static void bar(float x,float y,float w,float h,u32 col) {
    C2D_DrawRectSolid(x,y,0.0f,w,h,col);
}
static void label(PPDisplay *d,float x,float y,float scale,const char *raw,u32 col) {
    C2D_Text text;
    char safe[80];
    if(!raw || !d->text_buffer)return;
    snprintf(safe,sizeof(safe),"%s",raw);
    if(!C2D_TextParse(&text,d->text_buffer,safe))return;
    C2D_TextOptimize(&text);
    C2D_DrawText(&text,C2D_WithColor,x,y,0.0f,scale,scale,col);
}
static void action(PPDisplay *d,PPUIRect box,const char *name,int selected) {
    rect(box,selected?C2D_Color32(33,101,143,255):C2D_Color32(28,47,73,255));
    label(d,(float)box.x+12,(float)box.y+8,0.48f,name,TEXT_COLOR);
}
static void bottom_ui(PPDisplay *d,const PPUIState *ui,const PPHUD *hud) {
    unsigned k;
    char tmp[72];
    if(!ui || !hud)return;
    C2D_TextBufClear(d->text_buffer);
    if(ui->page==PP_PAGE_PAUSE) {
        label(d,16,10,0.70f,"PAUSED",TEXT_COLOR);
        label(d,16,40,0.40f,"D-Pad + A or touch",MUTED);
        action(d,pp_ui_pause_rect(0),"RESUME",ui->selected==0);
        action(d,pp_ui_pause_rect(1),"RESTART",ui->selected==1);
        action(d,pp_ui_pause_rect(2),"HELP",ui->selected==2);
        return;
    }
    if(ui->page==PP_PAGE_HELP || ui->page==PP_PAGE_ERROR) {
        label(d,14,12,0.70f,ui->page==PP_PAGE_HELP?"HELP / CONTROLS":"ERROR",TEXT_COLOR);
        label(d,14,58,0.44f,"D-Pad / Circle Pad: move",MUTED);
        label(d,14,85,0.44f,"Mapped buttons: back / pause",MUTED);
        label(d,14,112,0.44f,"Use mapped page cycle buttons",MUTED);
        label(d,14,139,0.44f,"START exits this demo",MUTED);
        action(d,pp_ui_footer_rect(0),"BACK",1);
        return;
    }
    const char *names[]={"HUD","MAP","BAG"};
    const PPUIPage pages[]={PP_PAGE_HUD,PP_PAGE_MAP,PP_PAGE_INVENTORY};
    for(k=0;k<3;k++) {
        PPUIRect r=pp_ui_tab_rect(k);
        if(ui->enabled_pages&(1u<<pages[k]))action(d,r,names[k],ui->page==pages[k]);
    }
    bar(10,63,300,117,C2D_Color32(24,41,65,255));
    if(ui->page==PP_PAGE_HUD) {
        snprintf(tmp,sizeof(tmp),"SCORE  %lu",(unsigned long)hud->primary_value);
        label(d,20,74,0.70f,tmp,TEXT_COLOR);
        snprintf(tmp,sizeof(tmp),"MISSES  %u / %u",hud->secondary_value,hud->secondary_max);
        label(d,20,110,0.55f,tmp,MUTED);
        bar(20,146,275,10,C2D_Color32(50,64,82,255));
        if(hud->secondary_max) {
            float fraction=(float)hud->secondary_value/(float)hud->secondary_max;
            if(fraction>1.0f)fraction=1.0f;
            bar(20,146,275.0f*fraction,10,ACCENT);
        }
        if(hud->game_over)label(d,20,162,0.42f,"GAME OVER - B to restart",TEXT_COLOR);
    } else if(ui->page==PP_PAGE_MAP) {
        label(d,20,67,0.50f,"LIVE GAME MAP",TEXT_COLOR);
        if(hud->grid_w>0 && hud->grid_h>0) {
            float cellw=200.0f/(float)hud->grid_w;
            float cellh=80.0f/(float)hud->grid_h;
            bar(37,93,200,80,C2D_Color32(40,67,78,255));
            if(hud->player_x>=0 && hud->player_x<hud->grid_w)
                bar(37+(float)hud->player_x*cellw,165,cellw>3?cellw:3,7,ACCENT);
            if(hud->item_x>=0 && hud->item_x<hud->grid_w &&
               hud->item_y>=0 && hud->item_y<hud->grid_h)
                bar(37+(float)hud->item_x*cellw,93+(float)hud->item_y*cellh,6,6,
                    C2D_Color32(255,209,80,255));
        }
    } else {
        label(d,20,80,0.55f,"COLLECTION",TEXT_COLOR);
        snprintf(tmp,sizeof(tmp),"Stars: %lu",(unsigned long)hud->primary_value/3u);
        label(d,20,114,0.56f,tmp,MUTED);
        label(d,20,148,0.36f,"Original game, no inventory engine",MUTED);
    }
    action(d,pp_ui_footer_rect(0),"PAUSE",0);
    action(d,pp_ui_footer_rect(1),"HELP",0);
    if(ui->event_frames && ui->event_text[0]) {
        label(d,20,169,0.36f,ui->event_text,ACCENT);
    }
}
void pp_display_shutdown(PPDisplay *d) {
    if(!d)return;
    if(d->text_buffer) {
        C2D_TextBufDelete(d->text_buffer);
        d->text_buffer=NULL;
    }
    if(d->top) {C3D_RenderTargetDelete(d->top);d->top=NULL;}
    if(d->bottom) {C3D_RenderTargetDelete(d->bottom);d->bottom=NULL;}
    if(d->c2d_started) {C2D_Fini();d->c2d_started=0;}
    if(d->c3d_started) {C3D_Fini();d->c3d_started=0;}
    if(d->gfx_started) {gfxExit();d->gfx_started=0;}
    d->ready=0;
}
int pp_display_init(PPDisplay *d) {
    if(!d)return 0;
    memset(d,0,sizeof(*d));
    gfxInitDefault();
    d->gfx_started=1;
    if(!C3D_Init(C3D_DEFAULT_CMDBUF_SIZE))goto fail;
    d->c3d_started=1;
    if(!C2D_Init(C2D_DEFAULT_MAX_OBJECTS))goto fail;
    d->c2d_started=1;
    C2D_Prepare();
    d->top=C2D_CreateScreenTarget(GFX_TOP,GFX_LEFT);
    if(!d->top)goto fail;
    d->bottom=C2D_CreateScreenTarget(GFX_BOTTOM,GFX_LEFT);
    if(!d->bottom)goto fail;
    d->text_buffer=C2D_TextBufNew(768);
    if(!d->text_buffer)goto fail;
    d->ready=1;
    return 1;
fail:
    pp_display_shutdown(d);
    return 0;
}
int pp_display_begin(PPDisplay *d) {
    return d && d->ready && C3D_FrameBegin(C3D_FRAME_SYNCDRAW);
}
void pp_display_top(PPDisplay *d) {
    if(!d||!d->ready)return;
    C2D_TargetClear(d->top,TOP_BG);
    C2D_SceneBegin(d->top);
}
void pp_display_bottom(PPDisplay *d,const PPUIState *ui,const PPHUD *hud) {
    if(!d||!d->ready)return;
    C2D_TargetClear(d->bottom,BOT_BG);
    C2D_SceneBegin(d->bottom);
    bottom_ui(d,ui,hud);
}
void pp_display_end(PPDisplay *d) {
    if(d&&d->ready)C3D_FrameEnd(0);
}
PPUIInput pp_input_3ds(u32 down,u32 held,touchPosition touch,circlePosition circle) {
    PPUIInput result={0};
    const struct {u32 native;uint32_t portable;} keys[]={
        {KEY_A,PP_UI_KEY_A},{KEY_B,PP_UI_KEY_B},{KEY_X,PP_UI_KEY_X},
        {KEY_Y,PP_UI_KEY_Y},{KEY_DLEFT,PP_UI_KEY_LEFT},{KEY_DRIGHT,PP_UI_KEY_RIGHT},
        {KEY_DUP,PP_UI_KEY_UP},{KEY_DDOWN,PP_UI_KEY_DOWN},
        {KEY_L,PP_UI_KEY_L},{KEY_R,PP_UI_KEY_R}};
    unsigned i;
    for(i=0;i<sizeof(keys)/sizeof(keys[0]);i++) {
        if(down&keys[i].native)result.pressed|=keys[i].portable;
        if(held&keys[i].native)result.held|=keys[i].portable;
    }
    result.touch_active=(held & KEY_TOUCH)!=0;
    result.touch_x=(int)touch.px;
    result.touch_y=(int)touch.py;
    result.pad_x=circle.dx;
    result.pad_y=circle.dy;
    return result;
}
