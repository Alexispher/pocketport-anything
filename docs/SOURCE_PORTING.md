# Real C/C++ game porting workflow (first implemented stage)

## Native 3DS game adapter pipeline

The new source porting system is **not** a hypothetical "Anything" binary
translator and does not replace gameplay with a demonstration. It
inspects a real C/C++ project and copies source and permitted assets into
an isolated workspace. Existing game logic, original license documents,
maps, enemies, animation code, music and saves remain in place.

1. Inspect an **authorized** local source tree:

       python -m pocketport inspect-source /path/to/game --out /tmp/game-analysis.json

   The inspector walks files without following symlinks, enforces count
   and size budgets, finds known Make/CMake/Meson files, C/C++ entrypoint
   candidates, include relationships, library/backend API calls, and
   source-level interoperability issues. Results have exact filenames and
   line numbers. This is conservative TOKEN inspection, **not** an AST,
   complete type analysis or proof of successful native linkage.

2. Create a **new, isolated** source port directory:

       python -m pocketport port /path/to/game --target new3ds --out /tmp/game-3ds
       python -m pocketport verify-port /tmp/game-3ds

   The original directory is never changed. The output has the original
   source under `source/`, a versioned `port.json` listing every
   SHA-256, `inspection.json`, and a reviewable `review.patch`.
   Destination must not exist; symlinks, path traversal, huge files and
   unsupported targets fail closed. `--copy-assets` is an explicit
   opt-in for legitimate game files and respects input limits.

3. Apply a scoped, existing adapter **only if the exact source matches**:

       python -m pocketport port /private/edgar --adapter edgar-sdl2 --copy-assets --out /tmp/edgar-3ds
       python -m pocketport verify-port /tmp/edgar-3ds

   The Legend of Edgar adapter changes ONLY its `src/init.c`
   SDL2 renderer-selection expression: when compiling on __3DS__, request
   SDL_RENDERER_SOFTWARE instead of accelerated. Desktop behavior is
   unchanged. Other engine code is copied intact. This adaptation by
   itself **does not** make the game compile or run on 3DS.

4. Build ONLY a previously authorized external native Makefile:

       python -m pocketport port-build /tmp/game-3ds --execute-trusted-build --timeout 300

   This operation can execute arbitrary game build scripts. There is NO
   automatic execution during `inspect-source`, `port` or
   `verify-port`. It requires devkitARM/libctru and real `3ds_rules`,
   picasso and 3dsxtool. It records the raw `native-build.log`,
   command, return code, failures, time and SHA-256 for a newly created,
   magic-valid 3DSX. A missing toolchain, unsupported build system,
   compiler error or absent new binary returns an explicit failure.
   C99 host builds are never mislabeled as 3DS artifacts.

5. If native compilation succeeds and legal redistribution has been
   reviewed and explicitly authorized:

       python -m pocketport port-package /tmp/game-3ds --out /tmp/game-release.zip --redistribution-authorized

   The output bundles the exact native binary, all corresponding imported
   original source and accompanying license files, assets, original patch,
   manifests and build evidence. It intentionally does not infer
   redistribution rights for proprietary music, textures or other data.

## Pinned external game research (real, not generated fixtures)

### The Legend of Edgar — true desktop C/SDL2 source adaptation

Source: https://github.com/riksweeney/edgar
Revision: `94d76ebe6a1533caefc89d9201ac3fc4ee974703`
Code license: GPL-2.0-or-later; music/sounds have additional original
credits and compatible Creative Commons licenses. The upstream game
contains real title/game states, NPCs/enemies, collision, interactive
items, maps, inventory, music and persistent saves.

Inspection of real source shows actual files:
`src/main.c` controls its game status loop; `src/game.c` updates
gameplay; `src/init.c` creates an SDL renderer;
`src/audio/audio.c` handles Mix_* audio; and
`src/system/load_save.c` accesses POSIX user home and saves.

The pinned upstream CI integration imports **8,308 actual files**,
preserves the original gameplay/audio/save modules byte-for-byte,
applies one reviewed SDL2 renderer fallback and verifies adapted SHA-256.
This is SOURCE_ADAPTED, not CROSS_COMPILED. Unresolved dependencies:
SDL2_image/ttf/mixer, software rendering on 3DS, filesystem/PAK paths,
controller coverage, level streaming, memory, actual game startup and
save/load. The source is GPL and is NOT copied into the MIT repository.

### L'Abbaye des Morts — existing genuine 3DS native port build route

Upstream game: https://github.com/nevat/abbayedesmorts-gpl
Existing GPLv3 Citro3D source port:
https://github.com/JeffRuLz/abbayedesmorts-3ds
Pinned source revision: `86caabf56dc3d8f26a181e3cf93b298d11cd4d18`.

This is an **existing port by others**, not an invention or
ground-up PocketPort reimplementation. Its original port has:
- true multi-state title, story, gameplay, game-over and ending paths;
- original player and enemy logic in `src/game.c`, `src/enemies.c`,
  `src/jean.c`;
- genuine native Citro3D renderer in `src/3ds/graphics.c`;
- native audio in `src/3ds/audio.c`, actual input and RomFS assets;
- GPLv3 code and CC-BY-3.0 original graphics/audio credits.

The `abbaye-native-3ds` adapter is a narrow build-repair patch:
the historical `src/history.c` and `src/startscreen.c` mistakenly pass a Music pointer
to `aud_StopMusic(music)`, although the native function takes no
argument and stops its channel itself. The patch uses the existing
zero-argument function and retains game progression. Any additional
compiler/linker failures must be examined and fixed individually.

The selected game cannot be marked PLAYABLE by a CI cross-compile.
Correct output must be launched, title/story/game/enemy/ending paths
observed and input/audio tested in Azahar or hardware. A build produced
from someone else's existing native port is evidence of reusable
import/build orchestration, not evidence that arbitrary SDL2 games
can now be automatically ported.

### Other evaluated candidate: C-Dogs SDL

The GPL-2.0 C run-and-gun game includes real campaigns, enemies, missions,
weapons, audio, persistence and SDL2-based rendering. Its game data uses
a mix of CC0/CC-BY/CC-BY-SA licenses. It is an attractive future
independent adaptation target, but full native engine integration,
dependency testing and licensed asset conversion have not been performed.
Source: https://github.com/cxong/cdogs-sdl

## What is NOT implemented by this release

No universal C AST rewrite engine, EGL/OpenGL backend, SDL2 3DS game
runtime importer, general audio/animation translation, netplay, 3DS
emulator capture, external game save compatibility or genuine arbitrary
commercial-game executable compatibility. File-based findings can have
false positives and must be crosschecked against source and build logs.
External code execution requires explicit trust and no file handling
should escape a bounded private work directory.

## Required game acceptance testing

On the *same* 3DS executable and revision, record real startup,
title/new game selection, movement, combat/interactions, original
objectives, scene/level transition, game-over/retry, native sound
and music together, pause/resume, save/load if present, memory high-water
marks, and clean exit. Capture logs and real screenshots; do not invent
hardware FPS or claim PLAYABLE from a host-only test.
