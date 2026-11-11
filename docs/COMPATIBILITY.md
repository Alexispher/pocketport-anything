# Supported input and operation boundary (v0.2)

| Operation | Supports | Unsupported / not inferred |
| --- | --- | --- |
| Inventory | Files in explicit local directory, read-only SHA-256 and magic sniffing | Decryption, unpacking, commercial asset formats, executable emulation |
| Route planner | Verified evidence booleans, target Old/New 3DS | Automatic repository/game identification, fake license checks |
| Translator | PocketPort IR v1 uint32 add/sub/mul/const/ret => C99 and host verification | ARM64/MIPS/x86 lifting, indirect jumps, ABI, pointers, file/syscalls, full LLVM IR |
| Portable C runtime | Budget accounting, deterministic input map, safe relative resource paths | GPU allocation/VRAM, NDSP backend, save journal system |
| Gameplay example | Original Star Catcher host logic, reproducible scoring | Commercial game support, original copyrighted game assets |
| Native application source | libctru/citro2d rendering/input, RomFS read, cleanup | Verified `.3dsx` until toolchain run; hardware evidence |
| Asset optimizer | Pillow-supported bitmap formats + optional tex3ds `.t3x` | Proprietary texture/mesh containers, Blender/glTF formats, audio conversion |
| Host build | GCC/Clang executable of game core | 3DS platform launch, 3DS frame rate |
| 3DS build | devkitARM Makefile and real invocation if installed | Fallback compiler pretending to produce `.3dsx` |
| Emulator/hardware | Instructions and evidence levels | Automated emulator/hardware harness (not present) |

Source research should consult [3DS examples](https://github.com/devkitPro/3ds-examples), [N64Recomp](https://github.com/N64Recomp/N64Recomp), and [REA](https://github.com/morluto/rea). This table is intended to shrink when verifiable new runtime code is implemented, not to be bypassed with a README claim.


## Current-screen capability addendum

**Implemented source:** portable C menu/touch state machine, top/bottom
native Citro2D framebuffer ownership, original Star Catcher top gameplay
with bottom graphical HUD/MAP/BAG/HELP/PAUSE, generated JSON v1 display
profile and Python/MCP assessment. See docs/DUAL_SCREEN.md.

**Host tested:** finite control and touch hitbox behavior, pause/resume
transitions, profile validation, fallback constraints and original
gameplay regression. **Native build:** requires a verified CI .3dsx
for the exact head commit. **Not verified here:** actual two-screen
Azahar pixels, touch navigation or physical-device performance.

**Still unsupported:** arbitrary ARM64-to-ARM11 recompilation, stereo
rendering in this UI example, arbitrary game engine UI adaptation,
New 3DS exclusive control requirements, full commercial Skyrim gameplay
and automatic input rebinding from every profile JSON field.

The older v0.2 table above remains historical; newer native code exists.
