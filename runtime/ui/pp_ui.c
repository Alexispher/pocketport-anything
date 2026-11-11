#include "pp_ui.h"
#include <stddef.h>
#include <string.h>

int pp_ui_rect_valid(PPUIRect rect) {
    return rect.x>=0 && rect.y>=0 && rect.width>0 && rect.height>0 &&
           rect.x<=PP_BOTTOM_WIDTH-rect.width &&
           rect.y<=PP_BOTTOM_HEIGHT-rect.height;
}
int pp_ui_hit(PPUIRect r,int x,int y) {
    return pp_ui_rect_valid(r) && x>=r.x && y>=r.y &&
           x<r.x+r.width && y<r.y+r.height;
}
PPUIRect pp_ui_tab_rect(unsigned i) {
    const PPUIRect tabs[]={{8,10,96,42},{112,10,96,42},{216,10,96,42}};
    return i<3 ? tabs[i] : (PPUIRect){0,0,0,0};
}
PPUIRect pp_ui_footer_rect(unsigned i) {
    const PPUIRect regions[]={{12,190,140,42},{168,190,140,42}};
    return i<2 ? regions[i] : (PPUIRect){0,0,0,0};
}
PPUIRect pp_ui_pause_rect(unsigned i) {
    const PPUIRect options[]={{24,62,272,45},{24,117,272,45},{24,172,272,45}};
    return i<3 ? options[i] : (PPUIRect){0,0,0,0};
}
const char* pp_ui_page_name(PPUIPage p) {
    switch(p) {
        case PP_PAGE_HUD:return "HUD";
        case PP_PAGE_MAP:return "MAP";
        case PP_PAGE_INVENTORY:return "INVENTORY";
        case PP_PAGE_HELP:return "HELP";
        case PP_PAGE_PAUSE:return "PAUSE";
        case PP_PAGE_ERROR:return "ERROR";
        default:return "UNKNOWN";
    }
}
void pp_ui_init(PPUIState *s,unsigned enabled_pages,PPUIPage initial) {
    if(!s) return;
    memset(s,0,sizeof(*s));
    s->enabled_pages=enabled_pages & PP_UI_DEFAULT_PAGES;
    s->enabled_pages|=PP_UI_ALLOW_HUD | PP_UI_ALLOW_PAUSE | PP_UI_ALLOW_HELP;
    if(initial>PP_PAGE_INVENTORY ||
       !(s->enabled_pages&(1u<<initial))) initial=PP_PAGE_HUD;
    s->page=initial;
    s->return_page=initial;
}
void pp_ui_message(PPUIState *s,const char *message,unsigned frames) {
    size_t i=0;
    if(!s)return;
    s->event_text[0]='\0';
    s->event_frames=0;
    if(!message || !frames)return;
    while(i<sizeof(s->event_text)-1 && message[i] && (unsigned char)message[i]>=32) {
        s->event_text[i]=message[i];i++;
    }
    s->event_text[i]='\0';
    s->event_frames=frames>600?600:frames;
}
void pp_ui_tick(PPUIState *s) {
    if(!s)return;
    if(s->event_frames) {
        --s->event_frames;
        if(!s->event_frames)s->event_text[0]='\0';
    }
}
int pp_ui_is_paused(const PPUIState *s) {
    return !s || s->page!=PP_PAGE_HUD;
}
static PPUIPage next_visible(PPUIState *s,int direction) {
    const PPUIPage tabs[]={PP_PAGE_HUD,PP_PAGE_MAP,PP_PAGE_INVENTORY};
    int current=0,i;
    for(i=0;i<3;i++)if(s->page==tabs[i])current=i;
    for(i=1;i<=3;i++) {
        int idx=(current+direction*i+12)%3;
        if(s->enabled_pages & (1u<<tabs[idx]))return tabs[idx];
    }
    return PP_PAGE_HUD;
}
static void open_page(PPUIState *s,PPUIPage page) {
    if(page<=PP_PAGE_ERROR &&
       (page==PP_PAGE_ERROR || (s->enabled_pages&(1u<<page)))) {
        s->page=page;
    }
}
static unsigned pause_selection(PPUIState *s,unsigned choice) {
    if(choice==0) {
        s->page=s->return_page;
        return PP_UI_ACTION_RESUME;
    }
    if(choice==1) {
        s->page=PP_PAGE_HUD;
        return PP_UI_ACTION_RESTART;
    }
    if(choice==2) {
        s->page=PP_PAGE_HELP;
        return PP_UI_ACTION_NONE;
    }
    return PP_UI_ACTION_NONE;
}
PPUIResult pp_ui_step(PPUIState *s,const PPUIInput *i) {
    PPUIResult result={0,0,0};
    PPUIPage before;
    int new_touch,hit=-1;
    unsigned j;
    if(!s || !i)return result;
    before=s->page;
    new_touch=i->touch_active && !s->touch_previous;
    /* Suppress reactivation until physical touch release, including invalid hits. */
    s->touch_previous=!!i->touch_active;
    if(new_touch) {
        if(s->page==PP_PAGE_PAUSE) {
            for(j=0;j<3;j++)if(pp_ui_hit(pp_ui_pause_rect(j),i->touch_x,i->touch_y))hit=(int)j;
            if(hit>=0)result.actions=pause_selection(s,(unsigned)hit);
        } else if(s->page==PP_PAGE_HELP || s->page==PP_PAGE_ERROR) {
            if(pp_ui_hit(pp_ui_footer_rect(0),i->touch_x,i->touch_y)) {
                s->page=s->return_page;
            }
        } else {
            for(j=0;j<3;j++)if(pp_ui_hit(pp_ui_tab_rect(j),i->touch_x,i->touch_y))hit=(int)j;
            if(hit>=0) {
                const PPUIPage pages[]={PP_PAGE_HUD,PP_PAGE_MAP,PP_PAGE_INVENTORY};
                open_page(s,pages[hit]);
            } else if(pp_ui_hit(pp_ui_footer_rect(0),i->touch_x,i->touch_y)) {
                s->return_page=s->page;
                s->selected=0;
                open_page(s,PP_PAGE_PAUSE);
            } else if(pp_ui_hit(pp_ui_footer_rect(1),i->touch_x,i->touch_y)) {
                s->return_page=s->page;
                open_page(s,PP_PAGE_HELP);
            }
        }
    } else if(!i->touch_active) {
        if(i->pressed & PP_UI_KEY_X) {
            if(s->page==PP_PAGE_PAUSE) {
                s->page=s->return_page;
                result.actions=PP_UI_ACTION_RESUME;
            } else {
                s->return_page=s->page;
                s->selected=0;
                open_page(s,PP_PAGE_PAUSE);
            }
        } else if(i->pressed & PP_UI_KEY_Y) {
            if(s->page==PP_PAGE_HELP) s->page=s->return_page;
            else {
                if(s->page!=PP_PAGE_PAUSE)s->return_page=s->page;
                open_page(s,PP_PAGE_HELP);
            }
        } else if(s->page==PP_PAGE_PAUSE) {
            if(i->pressed & PP_UI_KEY_DOWN)s->selected=(s->selected+1)%3;
            if(i->pressed & PP_UI_KEY_UP)s->selected=(s->selected+2)%3;
            if(i->pressed & PP_UI_KEY_A)result.actions=pause_selection(s,s->selected);
            if(i->pressed & PP_UI_KEY_B) {
                s->page=s->return_page;
                result.actions=PP_UI_ACTION_RESUME;
            }
        } else if(s->page==PP_PAGE_HELP || s->page==PP_PAGE_ERROR) {
            if(i->pressed & (PP_UI_KEY_B|PP_UI_KEY_A))s->page=s->return_page;
        } else if(i->pressed & (PP_UI_KEY_L|PP_UI_KEY_R)) {
            s->page=next_visible(s,(i->pressed & PP_UI_KEY_R)?1:-1);
        } else if(i->pressed & PP_UI_KEY_B) {
            if(s->page!=PP_PAGE_HUD)open_page(s,PP_PAGE_HUD);
            else result.actions=PP_UI_ACTION_RESTART;
        }
    }
    result.page_changed=s->page!=before;
    result.gameplay_allowed=s->page==PP_PAGE_HUD && !i->touch_active &&
        !(i->pressed & (PP_UI_KEY_A|PP_UI_KEY_B|PP_UI_KEY_X|PP_UI_KEY_Y|
                        PP_UI_KEY_L|PP_UI_KEY_R));
    pp_ui_tick(s);
    return result;
}
