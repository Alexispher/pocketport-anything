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
