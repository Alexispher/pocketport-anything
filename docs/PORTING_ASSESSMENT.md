# Integrated source-to-3DS compatibility and build feedback

This extends the existing source project isolation and genuine devkitARM build
paths; it does not create a fictional universal native port converter.

## Real code paths

The following commands are implemented, each with explicit evidence boundaries:

    python -m pocketport inspect-source /path/to/authorized/game
    python -m pocketport source-audit /path/to/authorized/game --target old3ds
    python -m pocketport port-assess /path/to/authorized/game --target new3ds
    python -m pocketport port-assess /path/to/game --controls controls.json --target old3ds
    python -m pocketport control-coverage controls.json --target old3ds

The first two tools scan C/C++ source and build entrypoints without running
the game's scripts. The third combines evidence from independent bounded
scanners and produces per-file, line/symbol-specific issues and actionable
adapter tasks. The output explicitly says SOURCE_INSPECTED only: it is not
a completed platform migration, native build, or gameplay observation.

The optional controls.json is an authoritative, user-provided inventory of
original actions, not machine-inferred game semantics:

    {
      "schema_version": 1,
      "required": ["move","attack","pause","back"],
      "bindings": {
        "move": ["circle_left","dpad_left"],
        "attack": ["a"], "pause": ["start"], "back": ["b"]
      }
    }

The checker refuses malformed controls, unknown action names and unknown
buttons. It detects missing actions, touch-only essential menu actions
and New 3DS buttons without Old 3DS alternatives. It cannot prove
that the source game's action contexts, saved control settings or analog
sensitivity work on actual hardware; those require source adapters and
runtime tests.

## Isolated migration, genuine game source and build

    python -m pocketport port /path/to/authorized/game --out /tmp/game-3ds --target new3ds
    python -m pocketport verify-port /tmp/game-3ds
    python -m pocketport port-build /tmp/game-3ds --execute-trusted-build
    python -m pocketport diagnose-build /tmp/game-3ds/native-build.log

The port command makes an isolated copy, creates SHA-256 file mappings and a
reviewable unified patch. Specific vetted adaptations are opt-in, including
edgar-sdl2 and abbaye-native-3ds. No arbitrary source changes are silently
performed. Verify-port confirms source integrity. Imported build scripts
can execute arbitrary local code, so they are never run by assessment/import.
The trusted-build flag is an **explicit permission boundary**. Native build
requires a real Makefile and devkitARM/3dsxtool/picasso; no fallback fake
3DSX is produced.

Native builds now include structured diagnoses with observed log lines,
source-linked subsystem categories when available, suggested fixes and an
explicit correction_verified=false until the build is rerun. Typical
classifications: missing header, linker symbol, unsupported architecture,
shader error, missing assets, missing library, memory exhaustion.
Raw logs remain available. A clean unmatched log is not success evidence.

Packaging checks an actual 3DSX file header, SHA-256, evidence status,
a bounded set of safe source-relative artifact paths, and explicit
user-authorized distribution rights. Importing GPL games does NOT imply
permission to relicense them MIT or omit accompanying GPL source/credits.

## External game status

The Legend of Edgar: GPL C/SDL2 game. The existing import workflow can
preserve original gameplay source files and apply a narrow SDL software
renderer fallback. Still needs actual 3DS SDL portlibs, SDL_mixer,
SDL_image, font data, correct resource paths, input adaptations and
native gameplay validation. It is NOT currently claimed as a 3DS game.

L'Abbaye des Morts: a separate existing GPLv3 native 3DS port is used as
an external integration sample, with original code/assets and a narrow
audio API compatibility fix. Its upstream code is legally separate from
PocketPort's MIT-licensed core. If the pin and dependencies are accessible
on GitHub Actions, the workflow imports, builds, verifies and bundles
the actual original game. This demonstrates real SOURCE_ADAPTED and
CROSS_COMPILED statuses when confirmed by artifact hashes. It does
NOT prove a brand-new standalone port authored by PocketPort nor
EMULATOR_BOOTED or PLAYABLE statuses.

## Gameplay regression acceptance

For an imported game, verify from the **same build**: real title screen,
new game, movement, enemy or object interaction, objective progression,
real level transition, pause/resume, audio concurrency, save/exit/load when
supported by original, shutdown and no leaked resources. Repeatedly
transition levels while measuring runtime memory grants. A compiler
exit code and deterministic host fixture are insufficient for gameplay
or frame-rate claims. Azahar screenshot and physical-console test evidence
are separate.
