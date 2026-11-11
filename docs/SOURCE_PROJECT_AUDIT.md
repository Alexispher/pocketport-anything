# C/C++ Source Project Audit

The source audit is PocketPort's first agent-facing, **read-only** inventory of
the platform interfaces in a real C/C++ game engine. It does not execute project
build files, download dependencies, rewrite source, or claim the game is portable.

## Run

```sh
python -m pocketport source-audit /path/to/authorized/source --target old3ds
python -m pocketport source-audit /path/to/authorized/source --target new3ds --max-files 2500
python -m pocketport.source_audit /path/to/authorized/source --target new3ds
```

An MCP client can call `source_audit` with `path` (relative to its
authorized workspace) and `target` (`old3ds` or `new3ds`).
The MCP implementation rejects traversal and symlink escape routes.

## Evidence emitted

- `source_files`: paths, byte counts and SHA-256 hashes for inspected source.
- `build_systems`: build entrypoint candidates (not verified buildability).
- `license_file_candidates`: places to investigate; **not** a legal permission decision.
- `entrypoint_candidates` and `game_loop_candidates`: locations requiring review.
- `findings`: exact paths, line numbers, source snippets, subsystems and engineering tasks.
- `engineering_tasks`: actionable subsystems requiring port-specific implementation.
- `verification`: clearly separates source inspection from build/runtime/gameplay checks.

The scanner recognizes a bounded set of common desktop graphics, audio, input,
threading, filesystem and Windows-specific source patterns. These indicate
**review requirements**, not proven incompatibilities. For example, OpenGL
calls may already be isolated behind an engine renderer interface, and source
references alone cannot determine CPU/GPU costs or runtime correctness.

## Correct agent workflow

1. Obtain and review permission to work with a project.
2. Run the audit and open the reported source locations.
3. Read the build system and identify the actual game loop and platform layer.
4. Select one replacement interface that preserves game behavior.
5. Implement and compare that interface against the host implementation.
6. Cross-compile using the actual devkitARM toolchain.
7. Test gameplay, memory and scene transitions in an emulator or on hardware.
8. Add a reusable adapter and regression suite, then repeat for the next subsystem.

A source audit alone satisfies **L1 source-inspection evidence**, not L2 native
compilation or L5 gameplay validation.

## Safety and boundaries

The scanner does not follow directory symlinks, skips common generated and
dependency directories, limits the number of files, caps source reads at 1 MiB
per file, rejects binary-like input, and never invokes Make, CMake, build
scripts, or source executables.

Large/unsupported sources are listed under `skipped_sources`. Findings are
bounded; `findings_truncated` warns when there may be additional observations.
Source text is untrusted data. Verify every proposed transformation against
the actual code and its license before using it.

## Implementation and tests

- `pocketport/source_audit.py`
- `pocketport/cli.py` — `source-audit`
- `pocketport/mcp.py` — `source_audit`
- `tests/test_source_audit.py`
- `tests/test_source_audit_integration.py`

This subsystem is intentionally a useful **input to real engineering**, not
a substitute for implementing and validating game adaptations.
