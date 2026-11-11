#ifndef PP_DUAL_SCREEN_UI_H
#define PP_DUAL_SCREEN_UI_H
#include <stdint.h>

#define PP_TOP_WIDTH 400
#define PP_TOP_HEIGHT 240
#define PP_BOTTOM_WIDTH 320
#define PP_BOTTOM_HEIGHT 240

/* Hardware-independent UI state and input, reusable across game engines. */
typedef enum {
    PP_PAGE_HUD=0, PP_PAGE_MAP=1, PP_PAGE_INVENTORY=2,
    PP_PAGE_HELP=3, PP_PAGE_PAUSE=4, PP_PAGE_ERROR=5
} PPUIPage;

enum {
    PP_UI_KEY_A=1u<<0, PP_UI_KEY_B=1u<<1,
    PP_UI_KEY_X=1u<<2, PP_UI_KEY_Y=1u<<3,
    PP_UI_KEY_LEFT=1u<<4, PP_UI_KEY_RIGHT=1u<<5,
    PP_UI_KEY_UP=1u<<6, PP_UI_KEY_DOWN=1u<<7,
    PP_UI_KEY_L=1u<<8, PP_UI_KEY_R=1u<<9
};
enum {
    PP_UI_ACTION_NONE=0u,
    PP_UI_ACTION_RESTART=1u<<0,
    PP_UI_ACTION_RESUME=1u<<1
};
enum {
    PP_UI_ALLOW_HUD=1u<<PP_PAGE_HUD,
    PP_UI_ALLOW_MAP=1u<<PP_PAGE_MAP,
    PP_UI_ALLOW_INVENTORY=1u<<PP_PAGE_INVENTORY,
    PP_UI_ALLOW_HELP=1u<<PP_PAGE_HELP,
    PP_UI_ALLOW_PAUSE=1u<<PP_PAGE_PAUSE
};
#define PP_UI_DEFAULT_PAGES (PP_UI_ALLOW_HUD | PP_UI_ALLOW_MAP | PP_UI_ALLOW_INVENTORY | PP_UI_ALLOW_HELP | PP_UI_ALLOW_PAUSE)
typedef struct {
    uint32_t pressed;
    uint32_t held;
    int touch_active;
    int touch_x, touch_y;  /* bottom-screen *logical* pixels */
    int pad_x, pad_y;
} PPUIInput;
typedef struct {
    int x, y, width, height;
} PPUIRect;
typedef struct {
    uint32_t pause, help, back, next_page, previous_page, confirm;
} PPUIBindings;
typedef struct {
    PPUIPage page;
    PPUIPage return_page;
    PPUIPage help_return; /* nested HELP can return to PAUSE */
    unsigned enabled_pages;
    PPUIBindings bindings;
    unsigned selected;    /* pause selection 0..2 */
    int touch_previous;    /* rising edge => one action; hold => none */
    unsigned event_frames;
    char event_text[48];   /* only app-owned, bounded messages */
} PPUIState;
typedef struct {
    unsigned actions;
    int gameplay_allowed;
    int page_changed;
} PPUIResult;

int pp_ui_hit(PPUIRect rect, int x, int y);
int pp_ui_rect_valid(PPUIRect rect);
void pp_ui_init(PPUIState *state, unsigned enabled_pages, PPUIPage initial);
int pp_ui_set_bindings(PPUIState *state, PPUIBindings bindings);
PPUIResult pp_ui_step(PPUIState *state, const PPUIInput *input);
void pp_ui_message(PPUIState *state, const char *message, unsigned frames);
void pp_ui_tick(PPUIState *state);
int pp_ui_is_paused(const PPUIState *state);
const char *pp_ui_page_name(PPUIPage page);
/* Rectangles are shared with native renderer: no visually mismatched hits. */
PPUIRect pp_ui_tab_rect(unsigned index);
PPUIRect pp_ui_footer_rect(unsigned index);
PPUIRect pp_ui_pause_rect(unsigned index);
#endif
