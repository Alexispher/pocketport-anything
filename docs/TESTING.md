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

Record toolchain version, build output, exit code, ELF/3DSX SHA-256, targeted model. A cross-compilation alone corresponds to L2 (not L3-L7). The Makefiles were authored for devkitPro but need toolchain-available verification; do not claim them compiled without a real run.

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
