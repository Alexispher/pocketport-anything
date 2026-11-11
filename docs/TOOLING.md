# Verified external toolchain and integration points

The links below describe capabilities documented by their maintainers. PocketPort does not bundle these projects or inherit their licenses. Availability, exact CLI flags, supported OS and dependency versions should be revalidated before each upstream integration.

| Tool | Verified role | Important limits |
| --- | --- | --- |
| [devkitPro](https://devkitpro.org/) / [devkitARM](https://github.com/devkitPro) | ARM homebrew cross-compilation toolchain | Must install the actual 3DS packages; generic ARM GCC is not sufficient |
| [libctru](https://github.com/devkitPro/libctru) | User-mode 3DS hardware/services, HID, RomFS, NDSP, lifecycle | Does not magically port foreign game APIs |
| [citro3d](https://github.com/devkitPro/citro3d) | PICA200 graphics interface | Not desktop OpenGL / modern fragment shaders |
| [citro2d](https://github.com/devkitPro/citro2d) | 2D sprites, shapes, text over citro3d | Needs 3DS GPU setup; not a general Vulkan renderer |
| [tex3ds](https://github.com/devkitPro/tex3ds) | Texture encoding, mipmap options, atlases, font tools | `.t3x` output generated only by actual installed converter |
| [picasso](https://github.com/devkitPro/picasso) | PICA200 shader assembler | Hardware shader ISA, not GLSL compiler |
| [3ds-examples](https://github.com/devkitPro/3ds-examples) | Reference source and templates | Examples are learning assets, not proof any requested game ports |
| [3dslink](https://github.com/devkitPro/3dslink) | Netload homebrew on an accessible real 3DS | Requires correctly configured hardware and Homebrew Menu |
| [Azahar](https://github.com/azahar-emu/azahar) | Open-source 3DS emulator/debugging environment | Emulator success != physical hardware compatibility |
| [Luma3DS](https://github.com/LumaTeam/Luma3DS) | Homebrew custom firmware and LayeredFS patches | Requires appropriate console configuration; not a game converter |
| [GodMode9](https://github.com/d0k3/GodMode9) | On-console advanced file explorer / authorized user extraction | Do not share commercial ROMs/keys or overwrite original data |
| [REA](https://github.com/morluto/rea) | Evidence-first agent-based native analysis through MCP/CLI | Requires compatible provider; does not automatically understand CIA/NCCH containers |
| [Co-op Anything](https://github.com/cranebeaker/coop-anything) | Evidence-driven game project research, QA and agent playbooks | Workflow knowledge, not a console binary translator |
| [N64Recomp](https://github.com/N64Recomp/N64Recomp) | N64 MIPS static recompilation to C | Requires a matching runtime; not ARM64/PC/Switch cross-recompiler |
| [Blender](https://www.blender.org/) | Optional headless mesh simplification/animation baking | No Blender pipeline is implemented in PocketPort v0.2 |

## REA, compatible AI agents and MCP

Read the [REA repository](https://github.com/morluto/rea), [native analysis guide](https://rea.tools/guides/native/), [CLI docs](https://github.com/morluto/rea/blob/main/docs/cli.md), and [official get-started instructions](https://rea.tools/get-started/). Set up REA and a compatible native analysis provider **separately** according to its documentation (current native provider list includes Hopper, Ghidra, IDA, and Kuna; tool availability depends on host and target). Register its MCP server with your agent. A skill file **does not install** REA or a native provider. Example workflows:

1. Ask REA (via your installed agent MCP) to inspect the specific **supported** binary file, enumerate entrypoints/symbols/strings/call sites, and attach original function address and provider/target metadata to each assertion.
2. Use findings to implement one candidate portable C function or compatibility shim in a separate file with behavior fixtures; do **not** commit proprietary code from an unauthorized source.
3. Add tests comparing the reconstruction to the original behavior where legally possible. Record mismatches and unknown regions.
4. Pipe verified source-level or modeled operations into a new **explicitly supported** PocketPort compiler frontend. `PocketPort IR v1` can handle only its defined unsigned arithmetic language. It does not ingest REA output automatically.
5. Cross-compile with devkitARM, then test emulator and hardware separately.

No particular `rea` CLI flags are hardcoded because installed providers/REA versions can change. Use `rea --help` and the current project docs. Never imply that the MCP server has been connected or used when it was not.

## Asset converters and homebrew

`tex3ds -f rgba8 -o out.t3x image.png` is a documented direct converter usage. `pocketport optimize --encode-3ds` delegates to it and fails when absent. For models/animations use licensed specialized tools and develop an explicit verified converter. The `oot3d-texkit` alpha release is tailored to a particular existing Nintendo 3DS title, not a generic glTF-to-PICA200 system: [oot3d-texkit](https://github.com/folxxsreal/oot3d-texkit).
