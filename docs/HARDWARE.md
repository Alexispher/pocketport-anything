# Nintendo 3DS platform constraints and design budgets

**Platform source of truth:** [3dbrew Hardware](https://3dbrew.org/wiki/Hardware), [Memory layout](https://www.3dbrew.org/wiki/Memory_layout), [NCCH extended header](https://www.3dbrew.org/wiki/NCCH/Extended_Header), [PICA GPU pitfalls](https://www.3dbrew.org/wiki/GPU/Pitfalls), [GPU instructions](https://3dbrew.org/wiki/Shader_Instruction_Set). Community-derived documentation is not guaranteed to cover every firmware or loader configuration; validate the active environment.

| Resource | Old 3DS/2DS | New 3DS/New 2DS | Important restriction |
| --- | --- | --- | --- |
| CPU | Dual-core ARM11 MPCore at ~268 MHz | Quad-core ARM11 MPCore, ~268 or ~804 MHz modes | CPU core and clock access are restricted by OS/permissions; not all cores are free for the game |
| Physical FCRAM | 128 MiB | 256 MiB | NOT equal to application heap |
| Typical application mode | 64 MiB default | 124 MiB standard New mode | Other mode grants include 80/96 MiB Old and 178 MiB New; loader/exheader specific |
| VRAM | 6 MiB | 6 MiB | Textures, render targets and GPU surfaces compete for limited space |
| GPU | DMP PICA200, ~268 MHz | PICA200, same class | No arbitrary modern fragment shader programs/OpenGL desktop renderer |
| Top display | 400x240 per eye; 800x240 physical in stereo | Same | Stereoscopy multiplies presentation/rendering work |
| Bottom display | 320x240 resistive touchscreen | Same | A separately designed UI is strongly recommended |

## CPU, binary compatibility and scheduling

ARM11 is 32-bit ARMv6K-class hardware. ARM64 instructions, Switch 2 binaries, Windows x86-64 executables and N64 MIPS code are not directly executable by changing filename extensions. Modern runtime calls, symbol resolution, endianness, ABI, relocated code, exceptions, memory mappings, graphics and middleware must be replaced with real implementations. New-model clock and L2 modes depend on the process configuration; test rather than guessing throughput. A portable C core is the primary reusable target; use an ISA translator only for verified, supportable subsets.

## PICA200 and graphics

The GPU has programmable vertex processing and fixed/specialized geometry/fragment capabilities. Use [citro3d](https://github.com/devkitPro/citro3d) for 3D and [citro2d](https://github.com/devkitPro/citro2d) for 2D. [tex3ds](https://github.com/devkitPro/tex3ds) handles actual supported texture encoding, atlas, mipmap generation and format options. Core citro3d texture helpers accept specific dimensions (typically power-of-two between 8 and 1024) and formats including RGBA8, RGB565, RGBA4, ETC1/ETC1A4, etc.; a generic PNG cannot be assumed to be a GPU-ready binary texture. Check tex3ds command-line help for current flags before automating. Support supported PICA200 materials, baked lighting, vertex color and static shadows; unsupported post-processing and PC shaders need redesign, not an automatic rename.

Draw-call overhead, state changes, CPU geometry conversion, texture uploads, vertex transforms, stereo double rendering and alpha overdraw are often material bottlenecks. Profile on-device. Recommended first optimizations are fewer state changes, atlas coalescing, simpler geometry, streamed resources, fixed timestep, camera/visibility culling, LOD, and preprocessed GPU formats. Avoid assigning a universal frame-rate target without measurements.

## Runtime and memory

Real applications must derive available heap from actual grants and observe linear memory usage. Split pools for streaming, transient frames, persistent geometry and textures; avoid allocating memory equal to physical FCRAM. `runtime/core/pp_runtime.c` implements portable *accounting only*; it does not query the OS or manage actual GPU memory. Limit assets to provable budgets. `pocketport optimize` reports encoded/unencoded state separately.

## Storage, audio, input

libctru exposes RomFS and SD services, HID, DSP audio (`ndsp`) and lifecycle APIs. Pack read-only assets with the 3DSX RomFS build flags; user saves require a dedicated app-specific directory, checksums, backups and safe write/rename semantics. The original native template only **reads** a RomFS text file (no save writes). Touch, Circle Pad, face buttons and D-pad are available; New-specific C-Stick/ZL/ZR require compatibility fallbacks. Audio streaming must use supported buffers/format conversions and should be measured for underruns. There is **no** complete PocketPort audio subsystem yet.

## Packaging / running

Use devkitPro `devkitARM`, `libctru`, `citro3d`, `citro2d`, `tex3ds`, `3dsxtool` and appropriate rules for `.3dsx`. `.cia`/title packaging is a separate optional, highly configuration-dependent route and is not implemented by the demo. The existence of Luma3DS, Azahar or GodMode9 does not prove any game works; hardware and emulator validation remain required.

Sources: [3dbrew Hardware](https://3dbrew.org/wiki/Hardware), [3dbrew Memory](https://www.3dbrew.org/wiki/Memory_layout), [devkitPro examples](https://github.com/devkitPro/3ds-examples), [3DS NDSP sample](https://github.com/devkitPro/3ds-examples/blob/master/audio/streaming/source/main.c), [citro3d texture implementation](https://github.com/devkitPro/citro3d/blob/master/source/texture.c).
