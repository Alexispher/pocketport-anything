# Architecture and implementation boundaries

PocketPort Anything is an **orchestrator with a small, tested portable runtime and precisely limited translation backend**. It does not emulate a Nintendo Switch system, reverse engineer every proprietary game format, or perform general ARM64-to-ARM11 recompilation.

```text
authorized game input --inspect/SHA256--> evidence manifest
         |                                  |
         +--> existing port/source research +--> route planner (7 routes)
                    |                              |
               source code                     unsupported => explain
                    |
          original game core + PocketPort IR v1
                    |                |
            portable C             C99 generator / host interpreter comparison
                    |                |
                    +----- shared lib/runtime core
                               |          |
                           host CC     devkitARM + libctru/citro2d
                               |          |
                           host QA     .3dsx build if toolchain installed
                               |          |
                          diagnostics  emulator/hardware QA (manual, unclaimed)
```

## Implemented modules

- `pocketport.inventory`: bounded read-only signature and hash inspection, symlink avoidance, JSON provenance. It is **not** encrypted format extraction.
- `pocketport.planning`: explainable route preference gated by **manually verified** evidence flags, avoiding false automatic inference.
- `pocketport.translation`: PocketPort IR v1 parser/interpreter/C generator with exact uint32 semantics, SSA variables, unknown-op errors and compiled host differential tests.
- `pocketport.assets`: optional Pillow conversion of known image formats into size-bounded/power-of-two intermediate PNGs; optional real `tex3ds` `.t3x` encoding.
- `pocketport.environment`: dependency discovery without changing the host.
- `pocketport.build`: real GCC invocation, optional devkitARM build, command/result/artifact evidence, deterministic host game tests.
- `runtime/core/pp_runtime.{h,c}`: memory budget accounting, explicit button mapping and safe relative packaged asset path validation; no OS-level emulation.
- `runtime/core/pp_game.{h,c}`: original deterministic portable C mini-game logic. It links generated scoring code and supports a reusable host frontend and 3DS citro2d frontend.
- `templates/3ds-homebrew/`: original 3DS startup, rendering, Circle Pad, RomFS and shutdown sample.

## Hard architectural gates

Game discovery is a **research task**, not file-extension inference. A 3DSX build does not mean gameplay works. A verified host `score.c` or `pp_game.c` proves only that those pieces behave on the host. `pocketport report` reports host evidence separately rather than upgrading console levels. Integration with REA is through an **externally configured** MCP server: no undocumented REA API coupling or claim of built-in console loaders.

## Planned, not implemented

Full CPU ISA decoders and lifting, target ABI emulation, direct ARM64-to-ARM11 recompilation, arbitrary PC graphics shader translation, complete 3D scene format converters, low-latency NDSP streaming, automatic Azahar input/screenshot automation, and on-device allocation/VRAM profiling require additional native engineering and rigorous validation. They are not represented by fake placeholder modules.
