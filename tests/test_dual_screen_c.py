"""Compile the production portable C UI with GCC and assert real state transitions."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


@unittest.skipUnless(shutil.which("cc") or shutil.which("gcc"),
                     "Host C compiler not available")
class PortableUIScreenTests(unittest.TestCase):
    def test_full_state_machine_and_input_edges(self):
        root=Path(__file__).resolve().parents[1]
        program=r"""
#include <assert.h>
#include <stdint.h>
#include <string.h>
#include "pp_ui.h"
#define S(q) do {assert(q);} while(0)
int main(void) {
    PPUIState u;
    PPUIInput i={0};
    PPUIResult r;
    PPUIRect tab=pp_ui_tab_rect(0);
    S(PP_TOP_WIDTH==400 && PP_TOP_HEIGHT==240);
    S(PP_BOTTOM_WIDTH==320 && PP_BOTTOM_HEIGHT==240);
    S(pp_ui_rect_valid(tab));
    S(pp_ui_hit(tab,8,10) && !pp_ui_hit(tab,104,10));
    S(!pp_ui_hit(tab,-1,10) && !pp_ui_hit(tab,999,10));
    S(!pp_ui_rect_valid((PPUIRect){310,0,30,30}));
    pp_ui_init(&u,PP_UI_DEFAULT_PAGES,PP_PAGE_HUD);
    S(u.page==PP_PAGE_HUD);
    S(!pp_ui_set_bindings(&u,(PPUIBindings){0}));
    S(!pp_ui_set_bindings(&u,(PPUIBindings){
        PP_UI_KEY_X, PP_UI_KEY_X, PP_UI_KEY_B, PP_UI_KEY_R, PP_UI_KEY_L, PP_UI_KEY_A}));
    S(pp_ui_set_bindings(&u,(PPUIBindings){
        PP_UI_KEY_X, PP_UI_KEY_Y, PP_UI_KEY_B, PP_UI_KEY_R, PP_UI_KEY_L, PP_UI_KEY_A}));
    r=pp_ui_step(&u,&i);
    S(r.gameplay_allowed);
    /* Physical X pauses and prevents game update. */
    i.pressed=PP_UI_KEY_X;
    r=pp_ui_step(&u,&i);
    S(u.page==PP_PAGE_PAUSE && !r.gameplay_allowed && r.page_changed);
    i.pressed=PP_UI_KEY_DOWN; pp_ui_step(&u,&i);
    S(u.selected==1);
    i.pressed=PP_UI_KEY_A;
    r=pp_ui_step(&u,&i);
    S(u.page==PP_PAGE_HUD && (r.actions & PP_UI_ACTION_RESTART));
    /* Touch on MAP tab is edge triggered: no second activation while held. */
    i.pressed=0;i.touch_active=1;i.touch_x=125;i.touch_y=20;
    r=pp_ui_step(&u,&i);
    S(u.page==PP_PAGE_MAP && !r.gameplay_allowed);
    i.touch_x=238;i.touch_y=25;
    r=pp_ui_step(&u,&i);
    S(u.page==PP_PAGE_MAP && !r.page_changed);
    i.touch_active=0;pp_ui_step(&u,&i);
    i.touch_active=1;r=pp_ui_step(&u,&i);
    S(u.page==PP_PAGE_INVENTORY);
    /* Pause button touch -> help touch -> back -> resume. */
    i.touch_active=0;pp_ui_step(&u,&i);
    i.touch_active=1;i.touch_x=40;i.touch_y=206;
    pp_ui_step(&u,&i);
    S(u.page==PP_PAGE_PAUSE);
    i.touch_active=0;pp_ui_step(&u,&i);
    i.touch_active=1;i.touch_x=48;i.touch_y=198;
    pp_ui_step(&u,&i);
    S(u.page==PP_PAGE_HELP);
    i.touch_active=0;pp_ui_step(&u,&i);
    i.pressed=PP_UI_KEY_B;
    pp_ui_step(&u,&i);
    S(u.page==PP_PAGE_PAUSE);
    i.pressed=PP_UI_KEY_B;
    pp_ui_step(&u,&i);
    S(u.page==PP_PAGE_INVENTORY);
    i.pressed=PP_UI_KEY_X;
    pp_ui_step(&u,&i);
    S(u.page==PP_PAGE_PAUSE);
    i.pressed=PP_UI_KEY_X;
    pp_ui_step(&u,&i);
    S(u.page==PP_PAGE_INVENTORY);
    /* Keyboard alternative to touch: L/R switches screens. */
    i.pressed=PP_UI_KEY_R;
    pp_ui_step(&u,&i);
    S(u.page==PP_PAGE_HUD);
    /* Invalid touch cannot click into UI */
    i.pressed=0;i.touch_active=1;i.touch_x=-5;i.touch_y=500;
    pp_ui_step(&u,&i);
    S(u.page==PP_PAGE_HUD);
    /* A source-port event is bounded and expires. */
    pp_ui_message(&u,"Star collected!",2);
    S(u.event_frames==2 && u.event_text[0]);
    pp_ui_tick(&u);S(u.event_frames==1);
    pp_ui_tick(&u);S(!u.event_frames && !u.event_text[0]);
    pp_ui_message(&u,"hello",999);
    S(u.event_frames==600);
    /* Alternate physical profile controls really affect native state. */
    S(pp_ui_set_bindings(&u,(PPUIBindings){
        PP_UI_KEY_Y, PP_UI_KEY_X, PP_UI_KEY_B, PP_UI_KEY_L, PP_UI_KEY_R, PP_UI_KEY_A}));
    i.touch_active=0;i.pressed=PP_UI_KEY_Y;
    pp_ui_step(&u,&i);
    S(u.page==PP_PAGE_PAUSE);
    i.pressed=PP_UI_KEY_X;
    pp_ui_step(&u,&i);
    S(u.page==PP_PAGE_HELP);
    i.pressed=PP_UI_KEY_B;
    pp_ui_step(&u,&i);
    S(u.page==PP_PAGE_PAUSE);
    return 0;
}
"""
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            source=p/"ui_test.c"
            source.write_text(program,encoding="utf-8")
            binary=p/"ui_test"
            cc=shutil.which("cc") or shutil.which("gcc")
            compile=subprocess.run(
                [cc,"-std=c99","-O2","-Wall","-Wextra","-Werror","-pedantic",
                 "-I",str(root/"runtime"/"ui"),str(source),
                 str(root/"runtime"/"ui"/"pp_ui.c"),"-o",str(binary)],
                capture_output=True,text=True
            )
            self.assertEqual(compile.returncode,0,compile.stderr)
            run=subprocess.run([str(binary)],capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)


if __name__=="__main__":
    unittest.main()
