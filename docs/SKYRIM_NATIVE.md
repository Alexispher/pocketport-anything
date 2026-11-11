# Skyrim 2011: first native data-path implementation

**Status:** HOST_TESTED for supported synthetic formats and C loader; native
devkitARM build and 3DS launch not yet verified. The target is original
Skyrim for Windows (2011), not Special/Anniversary Edition.

## Working components

- `pocketport/skyrim/bsa.py`: read-only Skyrim BSA v104 table validation,
  explicit traversal/memory limits, raw or zlib member extraction, no
  writes to the original archive.
- `pocketport/skyrim/tes5.py`: bounded TES4-style plugin container
  parsing, GRUP nesting and STAT/CELL/REFR records; MODEL paths,
  base FormID, positions, rotations and scales. Unknown records are not
  interpreted, scripts are never executed.
- `pocketport/skyrim/dds.py`: real DXT1/BC1 block decompression to row-major
  RGB565 **intermediate** bytes, 512x512 maximum, no alpha support. This
  is *not* a tex3ds GPU texture or a NIF conversion.
- `pocketport/skyrim/scene.py`: resolves REFR -> STAT references and
  serializes their positions and FormIDs in a bounded PPSC v1 scene package.
- `runtime/skyrim/pp_scene.{h,c}`: native portable read-only scene loader,
  finite transform validation, allocation-free fixed-capacity 1024-entry
  memory and nearest-marker query; tested on host GCC.
- `examples/skyrim-native`: Citro3D frontend source. Loads
  `sdmc:/3ds/pocketport/skyrim/scene.ppsc` from a user-supplied converted
  asset package, initializes GPU, draws diagnostic **marker triangles**
  at Skyrim-derived static placements, and permits camera movement (D-pad)
  and closest-marker query (A button). Markers are not NIF mesh geometry;
  no quests, collision or game loop compatibility is implied.
- `scripts/embed_shbin.py`: builds a C array from picasso output for the
  PICA200 shader used by the native renderer.

## Commands

```bash
python -m pocketport skyrim-inspect-bsa /private/Data/Skyrim-Meshes.bsa
python -m pocketport skyrim-inspect-plugin /private/Data/Skyrim.esm
python -m pocketport skyrim-convert-scene /private/Data/Skyrim.esm --cell-id 0x00000001 --out /private/output/scene.ppsc
python -m pocketport skyrim-validate-scene /private/output/scene.ppsc
python -m pocketport skyrim-convert-dds /private/example.dds --out /private/output/texture.pptr

# Only with the official devkitPro environment:
make -C examples/skyrim-native
# Expected: examples/skyrim-native/pocketport-skyrim.3dsx
```

The particular cell FormID is only an **example**: inspect your original
Skyrim data for an actual form ID. The converter refuses to create an output
without resolved references and refuses to overwrite an existing package.

Move your private `scene.ppsc` to the SD card at
`/3ds/pocketport/skyrim/scene.ppsc`. Never publish or commit converted
Skyrim data. A launch in Azahar/3DS has **not** yet been observed.

## Technical limitations and known work

- TES5 parsing is partial. Large record traversal, string handling, FormID
  load-order remapping, compressed records and unfamiliar GRUP semantics need
  testing against real user-owned Skyrim.esm.
- NIF geometry/animation/material loading: **not implemented**.
- PICA200 GPU texture tiling and upload of decoded DDS: **not implemented**.
- World chunks, occlusion, physics, Havok, Papyrus, AI, doors, quests,
  audio, saves, interaction with true game records: **not implemented**.
- Renderer and gameplay framerate, RAM availability on real New 3DS:
  **not measured**. The C scene loader uses at most 1024 references;
  source uses at most 128 static-placement triangles per frame.
- Native 3DS build requires devkitARM, libctru, Citro3D, picasso,
  3dsxtool and Python 3. No fake `.3dsx` is generated.

## Reference implementations and licensing

- MW3DS, https://github.com/3ds-conspiracy/mw3ds — Morrowind game-data
  conversion, PICA200 native engine, independent Old/New 3DS profiles.
  **GPL-3.0**; architectural research only, no code copied.
- devkitPro 3ds-examples, especially `graphics/gpu/simple_tri`, demonstrates
  libctru/Citro3D matrix, framebuffer and picasso shader conventions.
  https://github.com/devkitPro/3ds-examples
- OpenMW, https://github.com/OpenMW/openmw, is a Morrowind engine, **not**
  a Skyrim-compatible engine.
- PocketPort BSA, TES5, DDS and PPSC components here are independent
  implementations backed by synthetic test fixtures.

## Evidence gates

Only test execution justifies HOST_TESTED. Native 3DS launch,
actual Skyrim game data loading, NIF mesh rendering and hardware
validation require separate future evidence; none is claimed here.
