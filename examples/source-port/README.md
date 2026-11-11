# Star Catcher: portable source-port demonstration

Original minigame: catch falling stars by moving left/right. Miss three stars and lose. B restarts. Its deterministic C core is `../../runtime/core/pp_game.c`; scoring comes from `generated/score.c`, translated from the original PocketPort IR input `../translation-demo/score.ppir`. The **same game core** links with both the host runner and the 3DS citro2d frontend. No proprietary assets or third-party game code are used.

Build and run host:

```bash
python -m pocketport build examples/source-port/project.json --host
./examples/source-port/build-host/star-catcher-host --script RRRLLLLNNNN
python -m pocketport test examples/source-port/project.json --host
```

3DS build (requires devkitPro, devkitARM, libctru, citro2d):

```bash
python -m pocketport build examples/source-port/project.json --console
```

Host output is deterministic and is tested; an installed toolchain, emulator or hardware is required to verify a 3DS binary's build/startup/gameplay. Do not equate native C host tests with 3DS hardware validation.


## Native dual-screen UI

Native Star Catcher now draws **upper gameplay** and an independent
**lower 320x240 graphics-rendered interface**. Bottom tabs provide
HUD/MAP/BAG, PAUSE/HELP footer and a physical-only navigation path.
B restarts gameplay, START exits, X pauses, Y opens HELP, L/R cycles
views; Circle Pad/D-pad still move. Bottom touchscreen presses are
debounced on edge, and gameplay ticks stop when menus are open.

The validated profile examples/source-port/display-profile.json drives
the start page, page mask and touch enablement. Run:

    python -m pocketport screen-assess examples/source-port/display-profile.json
    make -C examples/source-port

No active Azahar/console visual test is inferred from source or CI alone.
See docs/DUAL_SCREEN.md.

The JSON profile also compiles actual native UI bindings for pause, help, back,
next/previous page and confirm; source movement controls remain game-specific.
