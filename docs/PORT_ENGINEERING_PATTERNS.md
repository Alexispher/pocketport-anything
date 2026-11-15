# Portable implementation patterns for ambitious game adaptations

This is a set of **engineering patterns to implement and validate**, not a claim that PocketPort ships all of them. Create your own code and fixtures; the examples are abstract contracts, not copied vendor formats or game data.

## A. Host-produced resource packs

A lightweight native client can display worlds much larger than available RAM if the PC performs costly conversion and the console reads bounded indexed pieces.

**Offline build contract**

1. Identify source input hashes, game version, legal permission, asset dialect and coordinate system.
2. Parse bounded input and reject invalid lengths, integer overflow, index loops, bad decompression ratios and unknown type IDs.
3. Transform coordinate handedness, units, triangle winding, normals, UV orientation, animation skinning and collision independently; compare against reference screenshots and floor-height probes.
4. Split output into *global* shared resources (deduplicated textures, models, animations, fonts) and *local* packs (terrain, object placements, collision, scripts, audio triggers).
5. Build sorted indexes keyed by map/cell/resource type/stable content ID. Include a file-wide build ID plus per-chunk compression method, raw/payload sizes and checksums.
6. Output reproducible packs using canonical ordering. Require a consistency test: identical inputs plus converter revision produce identical pack hashes.
7. Verify package generation with synthetic maps and deliberately malformed source files. Keep protected assets out of commits, logs and public CI.

**Console reader contract**

- Reject incompatible version/build ID, truncated header, offset wrap, out-of-file chunk and decompression beyond declared cap.
- Read only needed indices, stage uploads, fail gracefully on corrupt decorative data; block progression if collision or scripted gameplay data is unavailable.
- A loaded asset carries its pack generation and resource type; stale loads from a previous map are discarded.
- Keep read-only assets separate from writable saves and configuration.
- Make maps replaceable without copying the entire world into RAM.

Useful pack test cases: zero-cell map, maximum legal chunk, duplicate content ID, truncated index, corrupt CRC, mixed map/pool revisions, reloading previous zone, rapid warp between two zones, low SD throughput.

## B. Render and memory frame contracts

Define phases explicitly, instrument them and keep the metrics portable:

`frame` = `input -> simulation -> visibility -> prepare -> streaming_apply -> render_submit -> gpu_wait -> audio_housekeeping`.

Log **per-frame** rows with `frame_ms,phase,cpu_ms,gpu_ms,stream_ms,heap_free_kb,linear_free_kb,vram_free_kb,draw_calls` where available. Missing fields may stay absent; never invent numbers. Timestamp and coarse map/camera location help correlate spikes. Use `python -m pocketport profile-frames frames.csv --target-fps 30` for a real captured log.

**Failure budgeting**: Measure p50, p95, p99, maximum, late-frame count, long stalls and free-memory minima. Compare a rural/empty area, dense geometry, a particle-heavy encounter, traversal, menu UI, save/load and map transition. A stable average FPS with violent loading hitches is a failed streaming test.

**Memory ownership**: Distinguish ordinary heap, GPU/linear memory and VRAM. Every resource pool needs a strict cap, owner, eviction protocol, reference count or generation token, out-of-memory behavior and shutdown path. Avoid CPU-side copies of large GPU resources when not needed. Never infer usable RAM solely from console model.

**Draw batching**: Group by pipeline/material/texture/state, not merely model identity. Atlas where appropriate; protect UV padding and transparent edges. Keep alpha overdraw measured. Compare batching changes with a visual fixture and draw-call counters.

## C. Visibility, LOD and streaming

**Conservative PVS**: Partition the level into spatial cells with vertical levels where applicable. Offline sample representative camera positions; store candidate visible surfaces, entities and room/portal groups. At runtime combine PVS with near-field fallback, frustum testing and dynamic doors/actors. If precomputed visibility is missing, render a conservative fallback rather than wrongly hiding collision-critical objects.

**Multi-resolution world**: Make a coarse far mesh/atlas cheap enough to keep available. Stream full geometry near the player. Use screen-space error or distance thresholds with hysteresis to avoid flicker. Guarantee consistent terrain seams and prevent physics from using the approximate far mesh.

**Prioritized queue**: Critical collision -> required trigger/script -> visible gameplay entity -> near textures -> distant terrain detail -> cosmetic FX. Separate prefetch and required-to-play queues. Require a loading gate while critical data is unavailable.

**Scene transitions**: Bump a map generation token; cancel or invalidate old asynchronous requests; preserve player/sim state, place player only after correct collision exists, rebind audio and GPU resources; test repeated transitions and death/respawn.

**Pop-in diagnostics**: Track visible instances not yet resident, first-visible-to-ready latency, dropped/evicted resources, shader upload stalls and quality tier by distance. Fix the actual resource lifecycle rather than merely increasing the view distance.

## D. Gameplay semantics and online compatibility

Retain a **reference contract** for every real mechanic: movement speed, gravity, ground collision, collision triggers, attack timing, damage rules, item use, NPC routing, quest state, death, resume, travel, scene lifecycle, and persistence. Use host reference replays or independently constructed fixtures to compare outcomes.

For server-based games:
- Separate protocol/client-state implementation from the native renderer and UI.
- Record exact supported protocol/version. Validate encoding, framing, endian, message order and reconnect in a controlled server harness.
- Preserve server-authoritative rules; test login, character creation/selection, movement, actions, interaction, disconnect/relogin and state synchronization.
- Avoid storing credentials in logs; do not expose tokens or packets containing secrets.
- Respect server rules and authentication/anti-cheat mechanisms; do not attempt to bypass or disable them. Work with authorized environments.

A client can be "online" yet fail progression, inventory, social UI, group content or reconnect. Treat these as separate tested features.

## E. UI, input and audio on two screens

- Upper: gameplay/world. Lower: inventory/map/chat/skills/debug/settings according to current context; keep physical controls available even during touch navigation.
- Implement a versioned user-remappable action map. Make button modifiers and layered hotbars explicit in the UI, with hold/tap semantics and context-dependent camera controls tested end-to-end.
- Old hardware needs mappings that do not require C-Stick/ZL/ZR. Test stale button releases after pausing or switching screens.
- Test text entry and social/chat ergonomics separately from raw protocol correctness.
- Audio: bounded mixing, streaming buffers, state transitions between music/ambience/FX, graceful underrun and proper release on scene change. Do not assume UI sounds imply a working streaming soundtrack.

## F. Failure-response decision table

| Observed failure | Mandatory first experiment | Alternate architecture |
| --- | --- | --- |
| Engine depends on desktop graphics | Trace one actual draw path and recreate a known frame natively | Replace platform renderer, retain game logic |
| Unsupported proprietary scene format | Verify headers and convert a small real scene privately | Build clean-room scene loader with explicit versioning |
| Too many assets for RAM | Capture allocations and peak residency | Offline pack conversion + streaming + pooled cache |
| GPU time too high | Profile render passes/state changes | LOD, PVS, batching, baked effects |
| CPU time too high | Profile simulation/preparation hotspots | Precompute, schedule and reduce hot-path allocations |
| Severe pop-in or texture stalls | Measure file/read/upload latencies | Directional prefetch, far proxies, resident priority |
| Incorrect collisions | Compare reference floor heights and broad/narrow phases | Independent collision data at full near precision |
| Essential control unavailable | Build action inventory and context tests | Layered physical mappings and lower-screen UI |
| Network disconnect | Reproduce against authorized server and protocol traces | Fix legal protocol/state handling; do not bypass protections |
| Game loads but cannot progress | Walk title -> objective -> level transition -> save/load | Implement missing runtime/script subsystem |
| Native linker errors | Read exact missing symbol and object ABI | Port real subsystem or remove dependency via real replacement |

## G. Agent acceptance rules

A task must identify: code path, actual source/game input fixture, expected mechanic, measurable criterion, target model, regression test, evidence type and fallback experiment.

Required states:
- `SOURCE_INSPECTED`: source and dependencies mapped.
- `SOURCE_ADAPTED`: reviewed real code diff with reference tests.
- `HOST_TESTED`: host behavior exercised.
- `CROSS_COMPILED`: actual devkitARM build output checked.
- `EMULATOR_BOOTED`: same build started in a live emulator.
- `INTERACTIVE`: authentic input changes authentic game state.
- `HARDWARE_VALIDATED`: same build tested on a physical console with measured resources.
- `FULL_GAME_VALIDATED`: comprehensive original gameplay, transitions, persistence and ending verified.

Do not infer higher states from lower ones. Preserve negative and untested evidence. The Field Lab CLI checks the integrity of claims and measurements, not a human's observation of the scene.
