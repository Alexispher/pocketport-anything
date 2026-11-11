---
name: pocketport-anything
description: Investigate, port, optimize, cross-compile, and validate authorized games for Nintendo 3DS using evidence-gated routes and reusable source/runtime components.
license: MIT
compatibility: Python >=3.10; optional Pillow, devkitPro devkitARM/libctru/citro2d, REA MCP and Azahar
---

# PocketPort Anything agent skill

Activate for game-to-Nintendo-3DS porting, adapting an existing game engine, ARM11/PICA200 compatibility, scoped static recompilation or 3DS asset optimization. Do not activate for ordinary piracy requests or claims that merely renaming a Switch executable works.

1. Read `AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/HARDWARE.md`, `docs/PORTING_STRATEGIES.md`, `docs/TRANSLATION_RUNTIME.md` and `docs/VALIDATION.md`.
2. Audit existing code, git changes and tests. Preserve user work. Create a separate branch for changes.
3. Identify the game/version/hash and isolate authorized inputs. Never publish ROMs, firmware, keys or proprietary assets.
4. Research existing official 3DS releases, homebrew ports, source/decompilation projects and legal availability **before** proposing new translation.
5. Run `python -m pocketport doctor`, `inspect`, and `plan` using independently sourced JSON evidence. Record target memory budgets and unsupported subsystems.
6. If source is available, extend the tested C game/runtime pipeline. If binary-only, use REA only with verified provider/architecture. Never pretend PocketPort IR decodes machine code.
7. Implement a minimal real vertical slice and tests. Translate known IR functions, generate C, compile and compare to a reference (`verify-ir`). Reject unsupported constructs.
8. Prepare image assets with `optimize` and `--encode-3ds` **only** if `tex3ds` is available; otherwise report intermediate PNGs. Other converters need separate validated code.
9. Build using devkitARM on supported hardware target; test in Azahar, profile, fix, and then test on real console when possible.
10. Produce manifests, command logs, checksums and evidence levels L0-L7. Never claim a 3DS build or hardware success from GCC-only tests.

Reusable examples: `examples/source-port`, `examples/translation-demo`, `templates/3ds-homebrew`, `examples/asset-pipeline`. The coordinator integrates changes and verifies claims.


## Current reusable dual-screen workflow

Before choosing a porting strategy, read docs/DUAL_SCREEN.md and docs/AGENT_DEBUGGING.md.
The hardware top viewport is 400x240 per eye; the bottom touch viewport is 320x240.
Inspect the actual source game's viewports and control dependencies. Choose a versioned
layout in examples/source-port/display-profile.json and run:

    python -m pocketport screen-assess examples/source-port/display-profile.json
    python -m pocketport screen-header examples/source-port/display-profile.json --out /tmp/pp_profile.h

If evidence is unknown, retain unknown status, including application RAM. The native
Star Catcher demonstration shares the portable PPGame core between host and 3DS,
with upper gameplay, lower Citro2D HUD/MAP/BAG/PAUSE/HELP, touch and physical alternatives.
New ports should reuse runtime/ui/pp_ui and runtime/platform/pp_display_3ds rather
than grafting extra game-specific code into the native viewer.

In each failure class (graphics, shader, depth, touch, UI state, audio, save, memory,
input, conversion), inspect -> reproduce -> isolate -> write regression -> repair ->
cross-compile -> emulator screenshot -> hardware validation. Never collapse statuses:
HOST_TESTED is not CROSS_COMPILED; CROSS_COMPILED is not INTERACTIVE.
Native Star Catcher requires real libctru, Citro3D and Citro2D. The Skyrim viewer
is separate and must remain working. Keep GPU resource ownership and cleanup bounded.

## Actual source-engine inspection (new reusable workflow)

When provided a C/C++ game source tree, use the supported source audit before
guessing which platform adapters are needed:

    python -m pocketport source-audit /path/to/authorized/game-source --target old3ds

Or call the read-only MCP `source_audit` tool with workspace-relative
`path` and explicit `target`. Study the resulting `findings`, which include
exact file/line evidence for potential renderer, audio, input, threading,
filesystem and architecture boundaries. See docs/SOURCE_PROJECT_AUDIT.md.

Do NOT treat pattern matches as proven incompatibilities. Trace the actual
interfaces and preserve existing gameplay before writing replacement code.
Implement necessary missing adapters instead of declaring them categorically
impossible, then verify on host, devkitARM and a runtime in that order.
Source inspection alone cannot establish playability. Add each verified
reusable adapter and its tests to the framework.

This root skill is the SINGLE authoritative instruction body; other Agent Skills
discovery entries only point here. Read the focused documentation as necessary,
not all internals at once.
