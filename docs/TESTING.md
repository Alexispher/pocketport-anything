# Host tests, emulator tests, hardware tests and reproducible reporting

## Tests that can be run on a general PC

```bash
python -m unittest discover -s tests -v
python -m compileall -q pocketport
python -m pocketport verify-ir examples/translation-demo/score.ppir
python -m pocketport build examples/source-port/project.json --host
python -m pocketport test examples/source-port/project.json --host
python -m pocketport optimize examples/asset-pipeline/manifest.json --out /tmp/pocketport-test-assets --profile balanced
python -m pocketport report examples/source-port/project.json --out /tmp/pocketport-evidence.json
```

The Python tests exercise inventory, SHA, symlink security, license/route decisions, parse rejection, C/IR differential testing, generated file reproducibility, runtime memory and input behavior, a real native GCC build and deterministic gameplay (including catching a star), intermediary PNG processing and explicit failure when `tex3ds` is absent. The C test compiles and executes `tests/native_runtime_test.c` with `pp_game.c` and `pp_runtime.c`.

Host build/test evidence is recorded in ignored `examples/source-port/build-host/*-evidence.json`. Commands include return codes/stdout/stderr, artifact hashes and a clear statement that host C build != console test. These logs are environment-specific, so they are not committed as universal "passed" proof.

## Actual 3DS build gate

Required: devkitPro, devkitARM, libctru/citro3d/citro2d, appropriate `3ds_rules`, `3dsxtool`, `make`.

```bash
python -m pocketport doctor
make -C templates/3ds-homebrew
python -m pocketport build examples/source-port/project.json --console
```

Record toolchain version, build output, exit code, ELF/3DSX SHA-256, targeted model. A cross-compilation alone corresponds to L2 (not L3-L7). The Makefiles for Star Catcher and the separate Skyrim viewer have now been cross-compiled with genuine devkitARM in GitHub Actions. Rebuild and record a new hash for each change; a successful cross-compile is not emulator or physical-console validation.

## Emulator and physical console

Use [Azahar](https://github.com/azahar-emu/azahar) with authorized homebrew images. Check startup, correct viewport and colors, D-pad/Circle Pad, score advance, restart, START exit, RomFS text, frame time, resource activity and clean shutdown. Save emulator logs and real screenshots with actual software version and settings. Then repeat on Old/New real 3DS if accessible, recording firmware, Luma3DS version, memory mode, deployment method, and test case results. Do not generate or simulate screenshots as evidence.

## Evidence levels

| Level | Required objective evidence |
| --- | --- |
| L0 Identified | Exact title/build, hash, authorized asset/source details |
| L1 Analyzed | Inspected functions/assets/container plus evidence and limits |
| L2 Buildable | Actual 3DS toolchain successful build and output hash |
| L3 Launches | Emulator/on-console startup test observation |
| L4 Interactive | Console UI/input and update loop tested |
| L5 Playable vertical slice | Representative gameplay and behavior tests on a 3DS runtime |
| L6 Hardware validated | Real 3DS observed results and logs |
| L7 Full game validated | Whole game progression, save/load and compatibility coverage |

Report precise missing prerequisites; do not interpolate. The report generator currently establishes L0 for the original game manifest and exposes host evidence separately; it intentionally does not auto-promote 3DS levels.


## Dual-screen regression and CI gate

    python -m unittest discover -s tests -q
    python -m pytest -q
    python -m pocketport screen-assess examples/source-port/display-profile.json
    python -m pocketport screen-header examples/source-port/display-profile.json --out /tmp/pp_profile.h
    python -m pocketport test examples/source-port/project.json --host

The suite compiles runtime/ui/pp_ui.c with a host GCC/Clang C compiler
using -Wall -Wextra -Werror -pedantic; it checks top/bottom coordinates,
touch press-vs-held, invalid hitboxes, keyboard navigation, pause gating,
resume/restart, notification bounds and selected-menu state. Profile
tests cover malformed JSON, unsupported schema, hardware layouts,
touch fallback, unverified memory budgets and unsupported stereo build.

The existing .github/workflows/skyrim.yml now cross-compiles **both**
the original Star Catcher dual-screen example and Skyrim Citro3D viewer
in a real devkitPro devkitARM container and uploads the actual binaries.
No fake .3dsx or emulator success is inferred.

Azahar manual regression: confirm upper game remains visible, lower
graphics-rendered HUD changes pages, touch and D-pad alternatives,
pause freezes game, release prevents double click, START exit and
no text clipping. Preserve screenshots and link to exact binary SHA.
Old/New 3DS hardware verification must be recorded separately.
