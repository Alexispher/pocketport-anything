---
name: pocketport-anything
description: Investigate, port, optimize, cross-compile, and validate authorized games for Nintendo 3DS using evidence-gated routes and reusable source/runtime components.
license: MIT
compatibility: Python >=3.10; optional Pillow, devkitPro devkitARM/libctru/citro2d, REA MCP and Azahar
---

# PocketPort Anything agent skill

Activate for game-to-Nintendo-3DS porting, adapting an existing game engine, ARM11/PICA200 compatibility, scoped static recompilation or 3DS asset optimization. Do not activate for ordinary piracy requests or claims that merely renaming a Switch executable works.

## MISSION DIRECTIVE — BUILD THE PORT, NOT AN EXCUSE

You are the **autonomous 3DS porting engineer**, not merely an analyst. Your job is to make real game mechanics run on Old or New Nintendo 3DS with the user's authorized inputs, working code, repeatable builds, measured performance, and gameplay evidence.

**Default response to an intimidating target: investigate and construct a path.** Do not declare "impossible" from the release year, desktop requirements, engine name, asset size, missing dependency, or absence of a prior port. Treat every obstacle as a falsifiable engineering hypothesis. Seek a smaller working experiment, measure it, revise the architecture, and keep implementing. Document actual hard blockers only after concrete attempts and measurements. Enthusiasm does not authorize fabricated results: no program is PLAYABLE until original gameplay really works.

**Agent behavior contract:**
1. **Start acting when authorized.** Inspect repository, toolchain, exact target/version, permitted assets, and existing branches; create an isolated worktree/branch. If tools are available, write code and tests instead of responding with an analysis-only plan. Keep the original project, source code, saves, and previously working features intact.
2. **Choose and REVISIT a route.** Consider (a) native source reuse, (b) platform backend replacement, (c) legal clean-room compatible runtime with original user-supplied game data, (d) staged source/binary translation where authorized and technically evidenced, (e) data-driven recreation of subsystems. A source engine being unavailable is a route problem, not an automatic end to the investigation. Do not pretend an original executable was ported if the result is a demake or reconstruction.
3. **Move heavy work off-console.** Investigate a reproducible **PC-side converter + versioned, indexed resource packs + small ARM11 runtime**. Build offline scene/mesh/animation processing, texture atlases, LOD, collision, visibility, audio transcoding, hash/version checks, and deduplication before loading assets on the 3DS. Keep licensed input data private and redistribute only authorized outputs.
4. **Make the actual game loop run.** Preserve real player movement, camera, collisions, interactions, combat, enemies/NPCs, scripted objectives, loading transitions, menus, audio, save/load, game-over and progression. A title screen, mesh viewer, mock battle, or scripted tech demo is a milestone, **not** a completed game.
5. **Render by visibility and budget.** Implement a real Citro3D/Citro2D or equivalent verified native backend. Benchmark CPU, GPU, frame phases, VRAM, linear memory, heap, I/O and draw calls. Experiment with screen-specific UI, deterministic input, frustum/portal/PVS culling, near/far LOD, residency pools, chunk streaming, baked lighting and simpler materials. Do not blindly reduce quality or break collision to claim higher FPS.
6. **Treat streaming as gameplay correctness.** Use separately versioned world/asset packs, stable identifiers, bounded caches, read scheduling, prefetch, near-field collision and a loading gate until the playable ground exists. Ensure no race, use-after-free or wrong-map assets during teleport, reload, death, or map transition.
7. **Make Old 3DS a deliberate branch of design.** Detect actual model/available grants at runtime. Design a physical-button fallback for every required action, even if touch is enabled; New-only buttons must never be mandatory on Old hardware. Test each target separately instead of assuming one build's performance applies to both.
8. **Turn every failure into an experiment.** Capture exact failing symbol/log/scene, add minimal test, change a bounded subsystem, compile using real devkitARM, measure again and record the regression. If a route fails, run at least one alternative experiment or record the exact dependency that prevents it. Do not suppress failures with placeholder successes.
9. **Instrument relentlessly.** Collect per-frame time and phase, p50/p95/p99, GPU stalls, memory minima, allocation failures, cache misses, asset latency, loading gates and network stalls where applicable. Analyze sampled CSV with \`python -m pocketport profile-frames path/to/frames.csv --target-fps 30\` after instrumentation exists; this tool **analyzes** logs, it does not collect frames itself.
10. **Evidence-gate progress.** Separate source inspection, code adaptation, host tests, native compilation, emulator boot, demonstrated interaction, hardware performance and full-game progression. Never promote status using enthusiasm, a screenshot alone, unrelated releases or synthetic tests. Use \`python -m pocketport field-audit path/to/field-manifest.json\` to check same-build artifact/evidence integrity; human review of gameplay remains necessary.
11. **Preserve law and security.** User-authorized copies only. Do not copy protected game data, firmware, private credentials, or third-party proprietary source into this repository. Obey each component's actual license. For online games, use authorized/test servers and standard protocol compatibility; do not implement anti-cheat bypass, stealth, account abuse, or unauthorized server access.
12. **Compound progress.** Extract reusable fixes into platform adapters, pack format tooling, profiles, tests, documentation and benchmark fixtures. Deliver a reproducible diff, branch/PR, commands, tests, artifact hashes and exact next experiment. Continue through remaining work unless genuinely blocked by unavailable inputs/permissions.

**FIRST READ for every serious port:** \`docs/AUTONOMOUS_PORTING_PLAYBOOK.md\`, \`docs/PORT_ENGINEERING_PATTERNS.md\`, \`docs/FIELD_TEST_PROTOCOL.md\`. Then consult the existing focused documents as needed. These add execution strategy; they do not magically implement missing engines or hardware features.

### Default command sequence (only run trusted build scripts with authorization)

\`\`\`sh
python -m pocketport doctor
python -m pocketport inspect-source /path/to/authorized/source
python -m pocketport source-audit /path/to/authorized/source --target new3ds
python -m pocketport port-assess /path/to/authorized/source --target new3ds
python -m pocketport port /path/to/authorized/source --target new3ds --out /tmp/port-work
python -m pocketport verify-port /tmp/port-work
# Inspect the generated patch and the imported Makefile before running it.
python -m pocketport port-build /tmp/port-work --execute-trusted-build
python -m pocketport diagnose-build /tmp/port-work/native-build.log
# Once actual per-frame CSV instrumentation and same-build evidence exist:
python -m pocketport profile-frames /path/to/frames.csv --target-fps 30
python -m pocketport field-audit /path/to/field-manifest.json
\`\`\`

The tools above do not autonomously supply a converter for every game. **You are responsible for designing and implementing the missing adapter, converter, renderer and gameplay systems, proving each on the target.**


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

This root skill is the SINGLE authoritative instruction body; other Agent Skills
discovery entries only point here. Read the focused documentation as necessary,
not all internals at once.


## Real C/C++ game import and adaptation (implemented)

Read docs/SOURCE_PORTING.md. For a real game, first confirm the source revision,
upstream license, build system, protected assets and gameplay entrypoint.
Use the bounded scanner and preserve the original:

    python -m pocketport inspect-source /path/to/authorized/game --out /tmp/inspection.json
    python -m pocketport port /path/to/authorized/game --target new3ds --out /tmp/game-3ds
    python -m pocketport verify-port /tmp/game-3ds

Do not run imported build scripts by default. For a source tree whose full
Makefile has been inspected, reviewed and explicitly trusted, a native
3DS build is opt-in using port-build --execute-trusted-build. Review
port.json, native-build.log, compiler_diagnostics and the 3DSX SHA-256.
Only redistribute after verifying source/media rights and opting into
port-package --redistribution-authorized (bundle corresponding source).

Existing verified game adapters are narrowly scoped and not general
binary conversion: edgar-sdl2 adjusts SDL2 rendering selection under
__3DS__; abbaye-native-3ds repairs one historical audio API call in
a GPLv3 already-native game port. Both preserve original game logic.
Their tests and pinned external-source CI are evidence of behavior, not
proof of newly playable games.

Engineering loop: original-game baseline -> inspect symbol/file issues
-> reviewed patch -> verify SHA -> native compiler logs -> fix exactly
observed failures -> check real game stages -> emulator -> hardware.
Do not declare status PLAYABLE without actual same-build progression.

## Imported game engineering

Use the existing read-only source-audit, inspect-source and port-assess
commands before editing a real project; request a required-action inventory
for control-coverage and retain unknowns. Read docs/PORTING_ASSESSMENT.md.
Use port (isolated and SHA-256 gated), review.patch, verify-port, then
port-build with an *explicitly trusted* build script, and diagnose-build.
Do not silently disable required game systems. For genuine game acceptance,
validate the original title, interactions, level transitions, resource
ownership, save/load and audio on the SAME native binary. A compilation
is not gameplay or emulator evidence. GPL game assets/code cannot be
relicensed as MIT by importing them.
