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
