# Graphics compatibility matrix

| Feature | Nintendo 3DS implementation candidate | Framework implementation now | Verification |
| --- | --- | --- | --- |
| 2D filled rectangles | Citro2D / PICA200 | Original game top playfield + independent bottom 2D HUD | Native Star Catcher CROSS_COMPILED in GitHub Actions; no same-build visual verification |
| 2D assets | Citro2D atlas/t3x | PNG preparation and optional real tex3ds encoder; Skyrim BC1/BC3 GPU upload path | Host decoder tests; real tex3ds smoke in CI; actual texture pixels not separately verified |
| Texture dimensions | citro3d supported power-of-two constraints | Sized and padded to 8-1024 with UV fraction | Host tests |
| 3D mesh draw | Citro3D vertex buffers / PICA200 | Limited Skyrim PPMG native triangle viewer with shader and camera | Authentic devkitARM .3dsx in CI; user previously verified app boots in Azahar, not this same build visually |
| GLSL/Vulkan/DirectX shaders | Manual replacements / PICA200 vertex programs and fixed-function approximations | Not implemented | None |
| Skeletal animation | CPU or optimized offline matrix/skinning, budgeted | Not implemented | None |
| Dynamic lighting | Hardware-supported features and baked approximations | Not implemented | None |
| High-quality shadows | Baked textures, blob shadows, selective geometry | Not implemented | None |
| Stereo parallax | Separate per-eye render targets | Not implemented | None |
| Material transparency | Citro3d blending/state management | citro2d renderer uses RGBA solid shapes | Source written; no 3DS test |

Use [citro3d](https://github.com/devkitPro/citro3d), [citro2d](https://github.com/devkitPro/citro2d) and [3dbrew PICA200 reference](https://www.3dbrew.org/wiki/GPU/Pitfalls) as authoritative implementation research. Unsupported visual effects should be approximated with explicit design review, not silently deleted. A screenshot from a host renderer is never evidence of 3DS rendering.


## Current native implementation evidence update

The historical table above is a versioned baseline, not the current state.
**2D**: original Star Catcher now uses two independent Citro2D screen targets
in one C3D frame: 400x240 top gameplay and 320x240 bottom HUD/menu.
**3D**: the Skyrim experiment has a real PICA200 vertex shader, PPMG
vertex/index decoding, NIF BSTriShape subset and native triangle rendering
code; this is NOT general engine compatibility or a full Skyrim scene.
**Textures**: BC1/BC3 to tex3ds conversion and optional GPU t3x loading
are implemented for a constrained experiment; full materials/mipchains
and arbitrary modern PC graphics pipelines remain unsupported.

A successful devkitARM build establishes CROSS_COMPILED only. Verify each
screen in the same-build Azahar launch before calling actual rendering
confirmed. Source-port dual-screen Citro2D code has not been integrated
into the separate 3D viewer in this milestone.
