# Graphics compatibility matrix

| Feature | Nintendo 3DS implementation candidate | Framework implementation now | Verification |
| --- | --- | --- | --- |
| 2D filled rectangles | citro2d / PICA200 | Native and source-port demos | Source written; 3DS toolchain needed for build |
| 2D assets | citro2d sprite atlas/t3x | Only PNG preparation + optional tex3ds output | Pillow host tests; tex3ds not tested in this environment |
| Texture dimensions | citro3d supported power-of-two constraints | Sized and padded to 8-1024 with UV fraction | Host tests |
| 3D mesh draw | citro3d vertex buffers, PICA200 | Not implemented | None |
| GLSL/Vulkan/DirectX shaders | Manual replacements / PICA200 vertex programs and fixed-function approximations | Not implemented | None |
| Skeletal animation | CPU or optimized offline matrix/skinning, budgeted | Not implemented | None |
| Dynamic lighting | Hardware-supported features and baked approximations | Not implemented | None |
| High-quality shadows | Baked textures, blob shadows, selective geometry | Not implemented | None |
| Stereo parallax | Separate per-eye render targets | Not implemented | None |
| Material transparency | Citro3d blending/state management | citro2d renderer uses RGBA solid shapes | Source written; no 3DS test |

Use [citro3d](https://github.com/devkitPro/citro3d), [citro2d](https://github.com/devkitPro/citro2d) and [3dbrew PICA200 reference](https://www.3dbrew.org/wiki/GPU/Pitfalls) as authoritative implementation research. Unsupported visual effects should be approximated with explicit design review, not silently deleted. A screenshot from a host renderer is never evidence of 3DS rendering.
