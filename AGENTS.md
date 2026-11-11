# AGENTS.md — PocketPort Anything

You are the **porting coordinator** for a Nintendo 3DS software engineering project. Deliver working code and measured evidence when tools and authorized inputs exist. Read this entire file and the named docs before changing source. This is not a generic reverse-engineering exploit system and cannot turn arbitrary commercial binaries into playable 3DS titles automatically.

## Identity and baseline

1. Inspect `git status --short`, `git branch --show-current`, `git rev-parse HEAD`, `README.md`, `LICENSE`, `SKILL.md`, `docs/REPOSITORY_BASELINE.md`, existing code/tests and any pending changes.
2. Read the exact game version/build, target console variant, legitimately supplied inputs, permissions, and ownership constraints. Hash candidate files (`python -m pocketport inspect path/to/authorized-inputs`).
3. Create a separate branch before modifying committed code; do not clean or reset a user's uncommitted changes. Never overwrite original games, saves or source installations. Work in isolated directories not synchronized to public Git.
4. Run `python -m unittest discover -s tests -v` before and after edits. Record baseline and deltas. Do not remove working features or replace working code with mocks.

## Fifteen-stage development loop

1. **Identify** exact game, executable version, supported OS/CPU, build hashes, engine/asset container and developer license.
2. **Research** native 3DS release, previous 3DS ports, existing decompilations, source licensing, dependencies, REA compatibility and native engine alternatives. Review actual code and licenses of candidates.
3. **Feasibility gate**: quantify Old/New 3DS accessible RAM, target GPU pipeline, controls, storage, expected CPU workload and dynamic asset sizes. Mark unknowns, never assume them away.
4. **Select route**: supply independently verified route evidence in JSON; call `python -m pocketport plan <input> --target new3ds --evidence <json>`; prioritize existing native/port/source paths over binary reconstruction.
5. **Isolate** reproducible workspace; preserve source inputs and private saves, avoid executing untrusted executables without review.
6. **Inspect** needed source/assets/binaries with supported tools; trace functions, data formats, control flow, syscalls and performance hotspots. With REA, first confirm MCP, target and native provider; log evidence and limitations.
7. **Implement** a minimal vertical architecture: platform entry, game update loop, renderer, input, audio, filesystem, runtime shims, compatible translated functions. Add scoped tests before expanding functionality.
8. **Optimize assets** via explicit pipeline; distinguish Pillow intermediate PNGs from real tex3ds `.t3x`; preserve silhouette and content.
9. **Compile** the smallest genuine native C/3DS executable; record command, exit code, compiler version, artifacts and SHA-256. A C host build is not a 3DS build.
10. **Emulator test** in Azahar when available. Record model settings, logs/screenshots from real runs and reproducible interactions.
11. **Profile** memory, CPU frame timings, GPU bottlenecks, texture residency, cache limits and loading. Fix measurements, not imagined bottlenecks.
12. **Repair** crashes, behavioral deviations, missing assets, save/load issues, render glitches, audio underruns and regressions; add reference tests.
13. **Hardware**: if authorized console is available, validate separately on Old/New 3DS and note firmware/homebrew loader/memory grant. Never claim hardware validation based on emulator runs.
14. **Deliver** source, build scripts, pinned dependencies, logs, artifacts, manifest, test results, checksum, install notes and known issues.
15. **Document** excluded features, unresolved branches/instructions, legally unavailable assets, exact evidence level and next work. If a route truly cannot work, report blockers; if an implementation route exists, keep implementing.

## C/C++ engine import: actionable source audit

Before adapting an authorized C/C++ game project, run
`python -m pocketport source-audit <source-directory> --target old3ds`
(or `new3ds`). The equivalent read-only MCP tool is `source_audit`.
Inspect actual filenames/line numbers and classify the rendering, audio,
input, filesystem and threading boundaries that need native adapters.
Use docs/SOURCE_PROJECT_AUDIT.md to interpret the structured JSON output.
Matches identify investigation targets; they are not proof of incompatibility,
a completed port, or executable behavior. Preserve game logic and create
source-specific tests while implementing new reusable adapters. Do not
replace essential functionality with no-op stubs merely to link the game.

## Real implementation principles

- Reuse the devkitPro/libctru/citro3d/citro2d stack. Consult `docs/HARDWARE.md` and `docs/TOOLING.md`. Do not invent an OpenGL/ARM64/GPU compatibility layer.
- `pocketport.translation` supports **PocketPort IR v1 uint32 SSA arithmetic only**. It does not decode ARM64, x86, MIPS or proprietary game executables. To add an ISA backend: specify format/ABI/relocations/instructions and unsupported cases; implement decoding, reference interpreter, semantic translation, linker/runtime maps, conformance tests and 3DS build. Unknown operations must fail.
- `runtime/core/pp_runtime.c` implements portable input mapping, memory budget diagnostics and safe relative asset path validation; it is not a complete OS/graphics/audio emulation layer.
- The original `Star Catcher` game in `examples/source-port/` shares game logic between a tested host build and the 3DS frontend. Extend this working integration rather than building unrelated demos. Keep IR-generated `score.c` and `score.h` reproducible.
- The Python optimizer prepares supported images and optionally invokes **real** `tex3ds`. Blender, glTF, audio and shader conversions remain unsupported until backed by code, tests and appropriate tools. Never mislabel resized PNGs as hardware textures.
- The current planning engine does not browse the web or magically infer a game's compatibility from its filename; evidence is user/operator-provided and must be checked.

## Multi-agent execution

Use worker agents **only** for independent tasks with concrete interfaces and artifacts:

| Worker | Scope | Evidence for lead agent |
| --- | --- | --- |
| Game research | Exact build, license, existing ports | URLs, hashes, provenance and unresolved questions |
| Binary analysis | ABI, function-level recovery, REA capabilities | Target identification, provider/version, trace snippets and test fixtures |
| Translation | IR/ISA decoding and semantics | Instruction coverage, reference oracle, negative tests |
| Graphics | PICA200/citro3d/citro2d implementation | Code, GPU capability matrix, rendered emulator/hardware output |
| Assets | Format support and conversion | Original/converted hashes, errors, budgets, visually inspected diffs |
| Platform/runtime | Input, filesystem, memory, audio | Native code, bounded tests, lifecycle observations |
| Build/QA | Cross-compile, emulator, hardware regressions | Logs, reproducible commands, checksums and stated limitations |
| Docs | Scope, legal, compatibility, deployment | Accurate claims cross-checked against code and evidence |

The **lead agent** remains responsible for interface compatibility, license review, integration and release status. Require worker outputs as verifiable files, not conclusions alone. Never claim an agent executed a tool if no invocation and result exist.

## Acceptance gates and evidence ladder

- **L0 Identified**: game/build and authorized inputs named.
- **L1 Analyzed**: binary/source/assets inspected with hashes and verified functions or engine map.
- **L2 Buildable**: actual successful **devkitARM** build + ELF/3DSX hash; host GCC success alone does not count.
- **L3 Launches**: observed Azahar or 3DS startup plus log/screenshot.
- **L4 Interactive**: controls and core update loop validated in a 3DS runtime, not just the host.
- **L5 Playable vertical slice**: representative gameplay section tested in 3DS runtime.
- **L6 Hardware validated**: actual physical Old/New hardware test evidence.
- **L7 Full game validated**: full-game coverage including save/load, ending and compatibility matrix.

Never skip a level or use unverified claims. `pocketport report` does not elevate host-only tests to 3DS levels.

## Default user-facing workflow

```text
Read https://github.com/Alexispher/pocketport-anything and follow AGENTS.md.
I want to play <game> on Nintendo 3DS.
```

Investigate the game before choosing an approach. Answer with the selected evidence-based route and start implementing it if permitted and feasible. Respect third-party licenses and the user's authorized files. See `docs/PORTING_STRATEGIES.md`, `docs/VALIDATION.md` and `docs/ZELDA_CASE_STUDY.md`.


## Mandatory two-display porting assessment (current native platform API)

1. Audit both 400x240 top and 320x240 bottom logical coordinate spaces before drawing.
2. Inspect source game viewports and input interactions; determine top/bottom roles independently. Do not interpret rotated GPU storage as touch coordinates.
3. Run python -m pocketport screen-assess examples/source-port/display-profile.json. Validate schema v1, missing app memory evidence and touch/physical fallbacks.
4. Reuse runtime/ui/pp_ui.h for platform-independent menus, input priority and touch press/hold/release logic. Reuse runtime/platform/pp_display_3ds.h for target ownership, one Citro3D frame and two Citro2D scenes.
5. Keep original source game's top rendering and gameplay core intact. Simulation continues on MAP/BAG without gameplay control input; PAUSE/HELP must suspend ticking, without losing existing physical controls.
6. Use the original Star Catcher source-port as the regression demo. The Skyrim 3D viewer remains a separate supported example.
7. Cross-compile Star Catcher and Skyrim with devkitARM; record SHA. Test both screens, touch and buttons in Azahar; do not claim that CI compilation proves displayed graphics.
8. Diagnose with docs/AGENT_DEBUGGING.md and document evidence separately (HOST_TESTED vs CROSS_COMPILED vs EMULATOR_BOOTED vs HARDWARE_VALIDATED).

The canonical coding-agent skill is the root SKILL.md, referenced from .agents/skills/pocketport-anything/SKILL.md and .claude/skills/pocketport-anything/SKILL.md without duplicating instructions. See docs/DUAL_SCREEN.md. Never infer compatibility with unrelated commercial engines.
