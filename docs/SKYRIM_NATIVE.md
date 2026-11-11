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


## Special Edition archive support (limited)

A BSA archive whose actual header declares version **105** is parsed with
24-byte folder descriptors and LZ4 compressed members; v104 continues to
use 16-byte folder descriptors and zlib. The file magic/version are verified
from bytes, **not** inferred from folder names. This is BSA only: Fallout 4
BA2/BTDX packages are distinct and explicitly unsupported by this reader.
The optional host converter dependency is `lz4`; compressed extraction
has a caller-supplied output budget.

Skyrim LE and SE share many TES5 plugin records, but **mesh dialects
and BS stream versions vary**. Until a corresponding NIF reader and
verified scene fixture are available, a successfully read BSA is not
evidence that an SE world renders.


## Static BSTriShape NIF geometry (new experiment)

`python -m pocketport skyrim-convert-nif /private/meshes/fixture.nif --out /private/output/mesh.ppmg`
converts one strictly bounded NIF 20.2.0.7 BSTriShape, Bethesda stream 100 or
130, to PPMG v1 vertex/index geometry (XYZ, normals, UV). The reader enforces
finite transforms, index bounds and a single shape. Skinning, compound
shapes, materials, dynamic shapes and full NIF scene graphs are **unsupported**;
unsupported formats fail closed rather than fabricate triangles.

`python -m pocketport skyrim-validate-mesh /private/output/mesh.ppmg`
checks the serialized geometry. The Citro3D viewer can load this model from
`sdmc:/3ds/pocketport/skyrim/mesh.ppmg`, decompress its index data on the
CPU into triangle vertices and draw it with a fixed shader. Models are shown
**without original Skyrim materials/textures**, and the mesh is not yet placed
at the associated TES5 REFR transform or combined with a cell scene. Camera
D-pad controls are maintained. The project does not claim playable Skyrim.

The existing PPSC static markers remain as a fallback. Real Skyrim-derived
mesh rendering is only verifiable after authorized NIF conversion and
successful hardware/emulator launch.


## Local installation pipeline — limited supported vertical slice

```bash
python -m pocketport skyrim convert --game-dir "/private/Skyrim Special Edition" \
  --cell 0x00000200 --target new3ds --output "/private/skyrim3ds"
```

The cell ID above is **synthetic fixture notation**, not an asserted valid
Skyrim production location. Find a cell FormID in your own installed master.
The command recognizes an installation by `Data/Skyrim.esm` and BSA archive
headers, rejecting mixed 104/105 archives. It reads TES5 static records,
locates a matching NIF in the user's local BSA index, validates an unskinned
single-BSTriShape model, and emits `scene.ppsc`, `mesh.ppmg`, plus a
SHA-256 metadata manifest. The output stays outside the installation and
must be empty. Do not upload or commit those game-data derivatives.

The first PPMG model is **shown at local NIF coordinates**. REF placement,
cross-cell streaming, multi-shape models, shader materials, physics,
texture upload and actual Skyrim gameplay still need engine code.


## Real GPU texture data path (optional)

`python -m pocketport skyrim-convert-texture /private/source.dds
--max-dimension 128 --out /private/output/texture.t3x` decodes
the first mip of BC1/DXT1 or BC3/DXT5 DDS, downsizes to an 8..256
power-of-two texture and invokes devkitPro's **real tex3ds encoder**.
It requires Pillow and the installed `tex3ds` executable. Unsupported
BC7, normal-map conventions, mipchain dependency and shader-specific
material bindings are explicitly not supported. Converted game data
remains private. Texture upload is compiled into the native viewer:
if `texture.t3x` is placed at `SD:/3ds/pocketport/skyrim/`,
the viewer imports it using Tex3DS and maps the NIF UVs onto
the selected triangle mesh. This is a **single selected texture** and
not automatic Skyrim material resolution. Emulator/hardware display
must still be validated.
