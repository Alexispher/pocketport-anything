# Real Nintendo 3DS porting patterns

These are implementation references, **not bundled dependencies**. Re-check each
upstream project's license before incorporating any code.

| Project | Primary source | Engineering lesson |
| --- | --- | --- |
| Super Mario 64 3DS | https://github.com/sm64-port/sm64_3ds | Decompiled portable game core, custom 3DS platform backend and user-supplied original assets |
| PrBoom 3DS | https://github.com/devinacker/prboom-3ds | Native source port with original IWAD kept separate |
| ctrQuake | https://github.com/masterfeizz/ctrQuake | Engine reuse and modest software-rendering/input adapters |
| OpenLara | https://github.com/XProger/OpenLara | Engine reimplementation with distinct platform rendering backends |
| Celeste Classic | https://github.com/lemon32767/ccleste | Platform-neutral C game logic and replaceable frontends |
| Duke Nukem 3D | https://github.com/cmdada/dn3ds | Platform-specific input, sound, compatibility and screen abstractions |
| Ship of Harkinian 3DS | https://github.com/999sian/soh-3ds | Experimental native renderer and command translation; emulator results do not prove physical console support |
| Sonic CD | https://github.com/Voxel9/Sonic-CD-11-3DS-Redux | Decompiled engine with modified audio/video pipelines |

## Porting implications

Keep a game core separate from video/input/audio/storage backends; use an
existing source port or compatible engine before attempting binary translation.
A generic software framebuffer may be the simplest working 3DS rendering route
for legacy engines. Citro2D is suitable for a 2D frontend; Citro3D/PICA200
requires a distinct 3D backend, not automatic conversion of modern shaders.

PocketPort does not include third-party source code, ROMs, graphics or keys.
Each upstream project has its own licensing and asset-ownership requirements.
