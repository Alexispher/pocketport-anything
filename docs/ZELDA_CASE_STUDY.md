# Case study: Ocarina of Time aesthetics on Nintendo 3DS

**Question:** Can the modern visual direction of the new 2026 Nintendo Switch 2 Ocarina of Time be adapted to Nintendo 3DS?

## Confirmed sources

- [Official 3DS Ocarina of Time 3D](https://www.nintendo.com/en-gb/Games/Nintendo-3DS-games/The-Legend-of-Zelda-Ocarina-of-Time-3D-275007.html) is a native 3DS release with a 3DS-specific engine/control/rendering stack.
- [Nintendo Switch 2 Ocarina of Time](https://www.nintendo.com/us/store/products/the-legend-of-zelda-ocarina-of-time-switch-2/) is a distinct officially published game released **November 5, 2026**, with rebuilt graphics. Its 24.9-GB listing is not a directly useful memory footprint for 3DS and its executable is not ARM11-compatible.
- [zeldaret/oot3d](https://github.com/zeldaret/oot3d) is a **work-in-progress** decompilation, currently scoped to a USA build and not a complete self-contained 3DS ROM rebuild; see its README. Its licensed/source completeness is to be assessed function by function.
- [oot3d-texkit](https://github.com/folxxsreal/oot3d-texkit) is an **alpha** tool for reinjecting emulator-style OoT3D texture mods into actual game assets for LayeredFS/Luma3DS deployment. It requires the user's own RomFS, Windows and .NET 10 per its README; it is specific to OoT3D, not a universal converter.
- [HarbourMasters Shipwright / Ship of Harkinian](https://github.com/harbourmasters/shipwright) is a source port based on the N64 project with a separate game-data preparation flow, not a Switch 2 port or bundled ROM.
- [999sian/soh-3ds](https://github.com/999sian/soh-3ds) is an active *experimental* 3DS SoH implementation with a PICA200 renderer and native controls. Its own documentation distinguishes New-model primary target, Old-model experiments, tested Azahar paths and incomplete hardware validation. Those upstream claims were **not reproduced by this repository**.

## Recommended implementation decision

**Primary path:** route A, adapt **Ocarina of Time 3D** through authorized modding. It already runs on the target console, which avoids recreating the complete engine. Create a user-local RomFS snapshot and hashes, map model/texture archive bindings, begin with a narrow independently licensed texture/lighting update, run texture kit dry-runs and output a **LayeredFS-only patch**. Compare original/modified areas in emulator/hardware and profile memory. Never ship the base game or its files.

**Alternate:** route B/D, collaborate with experimental `soh-3ds` if open-source engine extensibility and N64-based assets are the goal, subject to its provenance, licenses, runtime constraints and user-supplied supported original game archive.

**Avoid:** treating the 2026 Switch 2 `.nup`, executable, engine or game data as if native 3DS resources. Source ISA, syscall model, PICA200 shading and accessible RAM constraints make this unrealistic without substantial reconstruction. A convincing "modern look" instead uses hand-crafted lower-poly silhouettes, proportionally detailed faces, styled normal/vertex lighting, aggressive UV and texture optimization, baked lighting and targeted effect substitutions.

## What can change through assets vs code?

| Goal | Primarily assets | Engine/runtime changes |
| --- | --- | --- |
| Improved color grading and character texture art | New appropriate-sized textures/palettes | Only if effect depends on unsupported shader pipeline |
| Cleaner UI symbols and screens | UI resources and atlas edits | New touch logic or layout behavior |
| Low-poly model silhouettes/LOD | Reauthored compatible meshes if original format is verified | Model loader or skeleton changes may be required |
| New lighting/shadow style | Baked lightmaps, vertex colors and static shadow textures | Real-time global illumination / cascaded shadow mapping impossible by asset swap alone |
| Voice acting and orchestral audio | Reencoded authorized audio files | Audio playback/streaming/cutscene synchronization and memory budget adjustments |
| Modern free camera and redesigned controls | None | New code/control and collision behavior |
| High-density geometry/postprocess | Cannot just re-encode into small textures | Requires major renderer redesign and perf compromises |

## First research experiment (not yet executed)

1. Confirm legally owned OoT3D build ID and region, back up files, hash local RomFS.
2. Run `oot3d-texkit` index and texture export over an authorized copy in a separate workspace.
3. Make a single original 128x128 replacement texture, reinject to a copy, inspect diff and test LayeredFS in Azahar.
4. Test on physical 3DS, measure visual regressions, performance and memory; only then widen scope.

No Nintendo data, ROM, key or derivative texture from the commercial game ships in PocketPort. `pocketport optimize` cannot parse OoT3D `.cmb`/`.zar` and **must not** be advertised as a replacement for `oot3d-texkit`.

## Lichii NUP format inspection (read-only, host-side)

Lichii is a GPL-3.0-or-later Switch-family emulator and **not** a 3DS runtime. Primary reference files:

- https://github.com/zortos293/Lichii/blob/main/src/core/loader/nup.cpp
- https://github.com/zortos293/Lichii/blob/main/src/core/file_sys/nup_container.h
- https://github.com/zortos293/Lichii/blob/main/src/core/file_sys/nup_container.cpp
- https://github.com/zortos293/Lichii/blob/main/src/core/file_sys/nup_writer.h

The NUP v1 archive stores a 128-byte superblock, an authenticated TOC,
package/directory/file tables and raw or zstd-compressed extents. It is an
**emulator-specific archive** and must not be assumed an official Nintendo
Switch 2 package format. `pocketport inspect-nup path/to/authorized.nup`
reads only fixed header/index records and SHA-256-verifies the TOC. It never
loads program binaries, extracts assets, or decrypts data; it cannot confirm
that a title is genuinely Zelda or that its executable can run on a 3DS.

The observed Windows Lichii build-150 title sequence is user-reported evidence
of emulator execution, not independent proof of gameplay compatibility or a
portable source build. The preferred practical route remains lawful asset and
modification research on Ocarina of Time 3D or examination of the experimental
Ship of Harkinian 3DS port. NUP host-side metadata identification can help
classify an authorized local sample but is not a conversion step.

Implementation provenance: NUP offsets and structural constraints were
independently described in Python from the public format documentation. No
Lichii C++ source or proprietary data was copied into PocketPort's MIT code.
