# Field Lab — native evidence and measured frame-time protocol

The Field Lab utilities are **read-only**. They do not run games, collect video, compile code, or certify gameplay. They analyze data captured elsewhere and check that each reported test references the exact same native artifact.

## Capture real performance

Instrument the 3DS runtime to write per-frame CSV. For example, use this header:

    frame_ms,phase,cpu_ms,gpu_ms,stream_ms,draw_calls,heap_free_kb,linear_free_kb,vram_free_kb

The only required column is frame_ms (milliseconds, finite and nonnegative). Optional values must be genuinely measured; omit any unavailable column. Phase can be world, loading, encounter, menu, streaming, cutscene, or another short label. The runtime should additionally log timestamp, camera/map position, available process memory grant, allocation failures, GPU queue waits, visible-but-not-resident resources, dropped texture uploads and SD latencies.

Analyze an actual run:

    python -m pocketport profile-frames /path/to/frames.csv --target-fps 30
    python -m pocketport profile-frames /path/to/frames.csv --target-fps 60

The tool returns p50/p95/p99/mean/worst frame times, frames exceeding the budget, stalls beyond 50 ms, per-phase distributions, observed minimum heap/linear/VRAM availability, and optional CPU/GPU/stream and draw-call statistics. A target frame rate is an experiment objective, not a claim that the device attains it.

The current implementation accepts UTF-8 CSV up to 4 MiB and at most 50,000 rows. It refuses NaN, negative and infinite metrics. It does not collect this telemetry itself.

## Same-build evidence

Create a private field-manifest.json next to the .3dsx and evidence files; the following JSON uses a **placeholder** SHA-256:

    {
      "schema_version": 1,
      "target": "new3ds",
      "artifact": {
        "path": "output/game.3dsx",
        "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
      },
      "scenarios": [
        {
          "id": "boot",
          "environment": "emulator",
          "result": "pass",
          "artifact_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
          "evidence": "evidence/boot-log.txt"
        },
        {
          "id": "movement",
          "environment": "hardware",
          "result": "untested"
        }
      ]
    }

Replace both hashes with the actual file SHA-256 and point evidence to actual recordings/logs. Paths are relative to the manifest directory; they may not escape it.

    python -m pocketport field-audit /path/to/field-manifest.json

The auditor checks schema, bounded input, path safety, that the .3dsx starts with the 3DSX magic, and actual SHA-256. For every scenario reported as pass it checks that the claimed build hash matches the binary and that an evidence file exists. It reports missing milestone coverage and flags inconsistent claims.

**Important: a matching header, hash and evidence path are NOT proof of gameplay.** The auditor explicitly returns playable_verified=false and observation_independently_verified=false. Someone must inspect actual emulator or device observations. It does not understand video contents.

Suggested core milestones: boot, movement, interaction, transition, pause-resume, audio, save-load and shutdown. If the game lacks a native save feature, document the exception; never fabricate a test.

## Manual real-game validation matrix

| Stage | Action | Pass condition |
| --- | --- | --- |
| Boot | Launch native binary | Actual game starts; no synthetic success screen |
| Controls | Navigate, pause, use all key actions | Works with physical buttons on the intended console variant |
| Collision | Cross stairs, doors, slopes, floors and boundaries | No falling through missing world data |
| Interaction | Use an item or attack a real adversary | Game-state changes match reference behavior |
| Progression | Complete objective, transition, respawn | New area and gameplay state load correctly |
| Memory | Walk across many scenes; return and reload | No steady memory leak or stale GPU/stream resources |
| Audio | Combat, ambience, pause, transition | Correct audio state and resource cleanup |
| Save/load | Save, exit, restart, load | Real objectives/inventory/state restored when supported |
| Online (if relevant) | Test with authorized server | Protocol, player state and reconnection verified |
| Shutdown | Quit after stress | Resources are released safely |
| Whole game | Play from start to ending | Meaningful original gameplay verified, not merely a tech demo |

Test Old and New models separately. Screen streaming/capture can influence performance. Record capture setup, available app memory, clock settings and actual measurements. Emulators do not substitute for physical hardware observations.

## Performance regression scenarios

Profile quiet outdoor map, dense world geometry, crowded NPC zone, combat with effects, loading transition, save/restore, repeated map switches, long traversal, and low SD throughput. Track GPU stalls, memory fragmentation, allocator failures, render submission time, draw calls, texture residency and cache misses. Prefer p95/p99 and worst stall over flattering average FPS.

Compare before and after under equivalent conditions. Keep source revision, exact target build, native binary hash, source input hash, converter revision and real evidence. Record unsupported systems rather than silently dropping them.

## CI boundaries

A green host test is not a native build; a compiler success is not a boot; boot is not interaction; interaction is not original campaign completion. Queued Actions jobs are untested. A release file can exist without a working game.

Deliver source, converter, executable, installation instructions, license compliance, scenario evidence, frame telemetry, regressions and the next measurable engineering task.
