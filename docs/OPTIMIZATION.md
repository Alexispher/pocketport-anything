# Measurable image optimization and unsupported asset types

The included image pipeline processes explicitly supported **PNG/JPEG/WebP/BMP** files using Pillow and optionally outputs actual `.t3x` textures through `tex3ds`. It converts to RGBA, scales down to the profile maximum, pads each side to the next power of two (minimum 8), writes intermediate PNGs and reports original/converted image dimensions, UV content bounds, file sizes and SHA-256 hashes. It never modifies the source file. Unsupported files are recorded, not discarded silently.

Profiles (`max_side` for prepared textures): `visual-quality=1024`, `balanced=512`, `performance=256`, `old-3ds=256`, `new-3ds=512`. These are conservative **texture maximum dimension policies**, not guarantees of acceptable overall frame rates or memory use. Source aspect ratio is preserved; transparent padding affects UV coordinates. No mipmap atlas, palette quantization, arbitrary mesh reimplementation or audio conversion is claimed by the built-in Python stage.

```bash
python -m pip install -r requirements-optional.txt
python -m pocketport optimize examples/asset-pipeline/manifest.json --out /tmp/pocketport-assets --profile old-3ds
# Only when tex3ds is installed:
python -m pocketport optimize examples/asset-pipeline/manifest.json --out /tmp/pocketport-textures --profile balanced --encode-3ds
```

`/tmp/pocketport-assets/asset-report.json` includes `hardware_compatible_encoded: false` for every intermediate PNG. With `--encode-3ds` and successful tex3ds execution plus nonempty output it becomes true, with the actual command and checksum. That does not validate runtime upload, GPU correctness or VRAM fit.

## Beyond the currently implemented stage

- **Mesh simplification and LOD**: investigate Blender `bpy` decimate modifiers or glTF mesh optimization libraries; preserve topology/silhouette; test bounding-box, animation and normals correctness.
- **Materials/shaders**: classify physically based terms and provide explicit PICA200 fixed-function/lightmap approximations, side-by-side visual review, draw-call profiling and UV checks.
- **Audio**: inspect sample rates/channels/loop metadata and implement actual NDSP-compatible PCM output/streaming with explicit latency regression tests; no current audio encoding backend is implemented.
- **Animation**: bake, quantize and measure error; avoid losing critical gameplay bone motion.
- **Resource packaging**: organize RomFS with manifests/hashes and lazy loading; a package listing is not proof runtime loader correctness.

The imported sample images under `examples/asset-pipeline/assets/` are original, generated for this repository, and may be redistributed under MIT. See [tex3ds docs](https://github.com/devkitPro/tex3ds).
