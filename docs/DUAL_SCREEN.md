# Reusable Nintendo 3DS dual-screen runtime

## Measured and logical display geometry

The upper screen is 400x240 logical pixels **per eye**. The lower screen is
320x240 logical pixels and handles touch. GPU framebuffer storage may be
rotated; do not use its storage dimensions for UI positions or touch mapping.

| Target | Ownership | Demo |
| --- | --- | --- |
| Top GFX_LEFT | PPDisplay.top | Star Catcher playfield, game state |
| Bottom GFX_LEFT | PPDisplay.bottom | HUD, map, inventory, help, pause |

Runtime UI state is portable C in runtime/ui/pp_ui.h and pp_ui.c.
The optional native adapter in runtime/platform/pp_display_3ds.h and .c
owns both Citro2D targets. Only one C3D frame is begun/end per loop.
Within it, the adapter calls C2D_SceneBegin for the two independent
render targets, so one framebuffer is not stretched onto both screens.
A text buffer is allocated once; graphics libraries are initialized
once and released on failure or exit. Do not initialize a bottom
debug console at the same time as the graphical bottom HUD.

## Implemented original game integration

The original portable PPGame core, generated scoring C, top graphics
and D-pad/Circle Pad movement remain intact. The bottom now includes:
- HUD: live score, misses, game status, bar indicator.
- MAP: live player and star coordinates.
- BAG: simple original-game collected-stars count.
- PAUSE: resume, restart or help.
- HELP: on-device control instructions.

START exits; B restarts from gameplay; X pauses, Y opens help; L/R cycles
HUD, MAP and BAG. D-pad UP/DOWN and A navigate pause without touching
the screen. Bottom tabs/footer/buttons also respond to touch.
Touch activation occurs once per physical press, not once per held
frame, including dragging away from the touched area. Non-gameplay
UI pages suppress gameplay updates and unintended controls.

PPUIInput is platform-independent. PPUIResult determines when the game
may update. PPUIState holds the current page, return page and bounded
notification/event lifetime. The bottom renderer uses the *same*
bounded hit rectangles as the state machine.

## Validated screen profile (version 1)

The original game's configuration is in
examples/source-port/display-profile.json. It declares:
source viewport/touch needs and whether source analysis was verified;
target Old/New family; separate top/bottom roles; pages;
touch policy and physical fallbacks; button bindings;
graphics/stereo mode; measured/unknown memory; excluded features.

Run:

    python -m pocketport screen-assess examples/source-port/display-profile.json
    python -m pocketport screen-header examples/source-port/display-profile.json --out /tmp/pp_profile.h
    make -C examples/source-port

The native Makefile regenerates the C header from this JSON on changes.
Starting page, enabled UI pages and touch enablement affect the native
example. All listed bindings are used for planning; Star Catcher native
controls currently remain B/X/Y/L/R in code. Other bindings require
a tested adapter before claiming user-configurable native key mapping.

Unknown fields, wrong schema, duplicate pages, invalid controls, missing
physical fallback, unsupported stereo in generated native code, guessed
application-RAM grants and oversized input are rejected. Hardware
physical FCRAM is not equal to application memory.

## CI vs visual evidence

Portable C UI state and configuration are tested with GCC and Python.
The native Star Catcher and existing Skyrim viewer compile with devkitARM
in GitHub Actions; exact run artifacts and SHA are published by the CI.
These results do not prove emulator or hardware rendering, touch,
frame rates, or memory performance.

Testing in Azahar: confirm original top gameplay, bottom graphics,
touch tabs, L/R alternatives, X pause (star freezes), A menu actions,
B restart, long-press debounce, correct 320x240 hit locations,
return from HELP, START exit. Record screenshots and the same binary SHA.
Test on physical Old and New 3DS only when available.
