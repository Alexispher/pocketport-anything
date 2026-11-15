# Autonomous 3DS Porting Playbook

**Operating rule:** do engineering. Do not use a game's release year, engine brand, nominal PC requirements, absence of an existing port or unfamiliar file formats as a substitute for investigation. Do not promise unbounded hardware capabilities either. Replace speculation with an executable experiment and measurements.

This is a design and agent-execution protocol. Only the code already shipped in this repository is an implemented feature. The techniques below become PocketPort features **only after someone implements, tests and merges them**.

## 1. Agent autonomy and escalation

- Begin with \`git status\`, exact revision, existing tests and all active work; use an independent branch and an isolated private game workspace. Never overwrite the operator's source installation, saves or uncommitted changes.
- If the user authorized porting, run the existing read-only inspection tools immediately. Do not stop at a report when code changes are possible.
- Maintain a *live engineering ledger*: hypothesis, evidence, failing input hash, command, trace/log reference, implementation diff, observed outcome, next experiment, and status.
- Parallelize independent jobs only: file formats, renderer, control semantics, audio, streaming, test harness and game logic; specify interfaces and acceptance tests first. The coordinator merges, compiles and resolves conflicts.
- When a dependency is unavailable, determine exactly which part is required, what legal substitutes or reimplementations exist, and whether a narrow vertical slice can prove a route. Offer options with measured tradeoffs, not a blanket declaration.
- Escalate only for genuinely missing permission, user-owned game files, credentials, device access, or a choice that changes the desired product. Do not hide failures or perform unauthorized actions.
- Do not copy code from independent examples without licensing and provenance review. Prefer designing your own implementation from documented behavior and tests.

## 2. Route selection is a revisable engineering decision

| Route | Entry conditions | First real experiment | Typical next step |
| --- | --- | --- | --- |
| Native source adaptation | Source and license available | Compile one real gameplay module on ARM11 | Replace platform/video/audio/input backends |
| Platform backend rewrite | Portable gameplay core, desktop-specific APIs | Render an authentic in-game frame with native GPU | Preserve original update loop; validate semantics |
| Independent compatible runtime | Original binaries cannot execute directly; legitimate data exists | Parse one real asset, demonstrate correct native frame | Reimplement necessary game systems against tests |
| Data-driven engine adaptation | Data formats understandable, scripting/game rules separable | Convert scene + collision and replay one interaction | Build a deterministic simulation, controls, progression |
| Scoped translation | Verified ISA/ABI and reference behavior, rights permit | Translate a small function with reference oracle | Grow supported instruction/API coverage |
| Full redevelopment/demake | Original behavior cannot be reused, operator accepts reconstruction | Original-feeling encounter with new code/art | Call it a demake, never a verified original port |

Do **not** assert that every engine has an open-source equivalent or that a retail game's entire code can be recovered. A route can fail in specific form and still yield a reusable subsystem. If direct porting fails, test a converter/runtime route. If that fails, identify the next smallest measurable research question.

## 3. First 90 minutes of engineering (sequence, not a completion estimate)

1. Identify target game, edition, architecture, file signatures, verified inputs and asset/source rights. Compute SHA-256, record build IDs and language/region.
2. Inspect current PocketPort branch and exact CLI flags; run \`python -m pocketport doctor\`, \`inspect-source\`, \`source-audit\`, \`port-assess\`. For binary assets use bounded inspect/format-specific readers and reject unsupported data honestly.
3. Compile and run the **smallest genuine native** 3DS baseline, not a fake binary. Keep log, ELF/3DSX hash, dependencies and toolchain version.
4. Choose one representative original game scene that exercises geometry, textures, input, state and collision. State concrete pass/fail conditions and reference evidence.
5. Make a reversible adapter or PC converter for that case, with tests for malformed data, indices, bounds, endian and version.
6. Render/step it on the target. Record real runtime output and actual failure conditions.
7. Instrument CPU frame phases and memory; run \`profile-frames\` on the resulting CSV. Tune one bottleneck at a time.
8. Add the next mechanic (interaction, enemy, transition, save) and keep earlier functionality working.
9. Update the ledger and regression suite. Repeat until the original game's meaningful progression works.

"90 minutes" here is just a prioritization label for the first iteration; no agent should claim to finish the stages in that duration.

## 4. Divide the system across PC and 3DS

### Host converter (write portable, testable code)

A PC can spend minutes processing resources that the handheld should load in milliseconds:

- Read the **user's local authorized installation**, not assets embedded in public Git. Validate archive magic, revision, integer ranges, recursion, decompressed sizes and path safety.
- Normalize world data into separate terrain, collision, entity, portal, map, audio, UI, animations and text streams.
- Precompute and serialize visibility from spatial cells, floor/height bands, portals and opaque occluders. Never occlude transparent or alpha-tested geometry as if solid. Retain a conservative near-radius fallback to avoid invisible objects.
- Generate coarse distant height fields and color atlases; permit far terrain to display before near detailed terrain arrives, **but hold collision-dependent gameplay** until the corresponding near collision is ready.
- Deduplicate identical textures/models across levels using stable content hashes. Pack global reusable assets separately from per-map instance/placement data.
- Generate several texture/mesh quality tiers (atlas, quantization, format, mip/LOD, triangle budgets), but preserve collision and player silhouette intentionally.
- Prepare animation metadata, skeleton compatibility, audio stream chunks, localizations and script/data tables with explicit version IDs.
- Emit indexed binary packs with magic, schema version, byte order, sizes, offsets, checksums, input provenance and compatible build IDs. Test out-of-bounds offsets, corrupted archives, mixed pack versions and partial writes. Large packages must respect filesystem size limits.
- Write a converter test for each format using synthetic data before importing actual retail files. Never ship the retail files with these tests.

### Console native runtime

- Use libctru with Citro3D/Citro2D or a verified target-specific renderer; PICA200 is not desktop OpenGL/Vulkan/DirectX.
- Separate persistent world state, render state, asset registry, streaming queues and temporary frame allocations.
- Preallocate/bound memory by **runtime-discovered available grant**. Monitor linear heap, conventional heap and VRAM independently. A device's physical RAM is not a process heap budget.
- Stream visible cells with prioritized queues: collision and player-adjacent geometry first, nearby interactive entities second, distant decorative resources last. Prefetch directionally, and apply backpressure before memory exhaustion.
- Use explicit resource state \`UNLOADED -> QUEUED -> LOADING -> READY -> EVICT_PENDING\`; prevent rendering freed data or mixing map generations during fast travel/death/reload.
- Keep SD/card I/O and expensive decompression out of the render-critical path where possible. GPU uploads and Citro3D resource ownership must be serialized correctly. Thread availability, service access and scheduling are model/configuration-specific.
- Support graceful visual fallback when distant resources are missing; never allow the character to fall through missing collision or skip mandatory scripted triggers.
- Make shutdown and partial initialization recoverable; release audio, GPU and SD resources without stale pointers.

## 5. The world, not merely a scene

A game is more than polygons. Implement and test these as independent but integrated services:

**Simulation:** fixed or bounded timestep, deterministic action input, physics/collision, NPC state, combat and damage, item interactions, camera collision, terrain height, water volumes where needed.

**Progression:** title -> new game -> objectives -> map transition -> checkpoint -> death/restart -> inventory -> ending; save/load must restore the exact gameplay state, not only coordinates.

**Scripts:** event triggers, dialog, quest flags, timing, local variables, object activation, cinematics, transition callbacks and fault reporting. Unsupported scripts must be visible in logs; silence is a regression.

**Network, only if the game requires it:** keep protocol version, authoritative game state, timestamps, movement reconciliation, reconnect and disconnect paths. Stress-test with a controlled local/test server. Do not bypass anti-cheat, account security or server access controls.

**Assets and authenticity:** if game data is proprietary, keep a private converter and distribute only code for which you have permission. Document whether the output is an original port, compatible reimplementation, or demake.

## 6. Visual strategy for each frame

Prioritize **actual player-visible information** over indiscriminate global reduction:

1. Frustum and distance culling; spatial bins for terrain and entity bounds.
2. Conservative portal/room visibility and optionally offline PVS for dense/static scenes. Validate that doors, moved objects and vertical multi-level spaces do not invalidate static visibility.
3. Multiple mesh LODs and coarse distant world proxies. Use hysteresis to stop constant switching/pop-in.
4. Texture residency by scene and camera; deduplicate atlases, batch compatible materials and minimize upload churn.
5. Baked lightmaps/vertex colors or inexpensive approximations for effects incompatible with the GPU.
6. Use both screens purposefully; main simulation on top, contextual controls, map, inventory and debug display below.
7. Profile the actual bottleneck (CPU prepare, render submission, GPU wait, streaming, decompression, texture upload, network or audio). Do not spend days optimizing GPU triangles when SD stalls dominate.

Optional 800x240 wide/stereo mode is an **experiment**, not a default feature promise. Re-run the full profile for each mode.

## 7. Controls as a state machine

For every gameplay/menu/cinematic/network context maintain an authoritative required-action list. Use \`control-coverage\` on a validated JSON inventory, then verify context transitions at runtime.

- Normalize buttons, touch, Circle Pad, C-Stick and optional ZL/ZR to actions, not hardwired scenes.
- Use modifier layers / sets for numerous abilities, with visual feedback so players know which action each button invokes.
- On Old 3DS, provide a design that uses common buttons and Circle Pad; use D-pad in a context-dependent camera/action mode if needed, with deterministic tap-versus-hold and no ghost inputs on resume.
- Never rely solely on touch for pause/back/confirm or other essential actions; every required menu must be navigable physically.
- Save the user's remapping and active input scheme. Test reconnect, pause, inventory, map, cutscene, game-over and load.
- Test hold/release repeat, stale events after pause, analog deadzones, action conflict and rapid modifier changes.

## 8. Debugging ladder: never stop at an error message

For each reproducible failure:

1. Save exact failing log, stage, hash and one minimal testcase.
2. Classify architecture, toolchain, compiler, linker, binary layout, assets, graphics, input, streaming, collision, audio, game state, network or memory.
3. Trace the **real** responsible function; don't silence errors with unused stubs, generic success returns or replaced game logic.
4. Reproduce behavior with a host reference or controlled synthetic fixture when actual game data cannot be committed.
5. Make the smallest causal change; compile on the **actual ARM11 toolchain**.
6. Run the same scenario again in emulator and real hardware as available; measure memory and frame cost.
7. Add a regression, update ledger, keep the next blocker queued.

If an entire engine does not compile, compile a real gameplay subsystem and identify its dependencies. If a material cannot be rendered, replace the backend while preserving scene/collision and visible meaning. If memory is exhausted, measure actual lifetime and residency before redesigning. An unknown is a research item with an owner, not an impossibility verdict.

## 9. Delivery and scientific integrity

Each attempt delivers a code diff and a short machine-readable/Markdown report with:

- exact game/version/source provenance; asset rights; input hashes;
- branch/commit, compile commands/toolchain, output SHA-256, target Old/New;
- meaningful tested scenarios (not merely boot);
- frame-time **distribution** and worst spikes by phase, RAM/linear/VRAM minima and memory errors;
- tests run, failing/untested systems and regressions;
- next executable experiment and what would falsify its hypothesis.

\`docs/FIELD_TEST_PROTOCOL.md\` defines a minimal manifest and the \`field-audit\` command to validate evidence bookkeeping without pretending to observe the console itself.

**Success criteria:** another developer, starting from authorized inputs and a clean checkout, can reproduce the build, install it, play an authentic interaction, progress through a game milestone and inspect evidence of the same build. Expand until the full original gameplay loop is demonstrated.
