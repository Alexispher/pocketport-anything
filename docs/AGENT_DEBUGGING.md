# AI-agent failure triage reference

Use from root SKILL.md. For each bug record branch/commit, original inputs,
reproduction steps, minimal failing test, code fix and *actual* validation.

| Symptom | Inspect | Required evidence |
| --- | --- | --- |
| Lower screen black | GFX_BOTTOM target, frame switching, console conflict | Same-build two-screen screenshot |
| Wrong UI size | 400x240 upper vs 320x240 lower, rotated FB | Visual + bounded hitbox tests |
| Touch off target | hidTouchRead coordinates, region bounds | Edge touch and OOB tests |
| Duplicate touch action | rising edge, release and held events | Long-press/drag regression |
| Buttons unavailable | portable key map and UI priority | Physical-only menu navigation |
| Game runs during pause | PPUIResult.gameplay_allowed | Game tick freezes across frames |
| Wrong help return | PPUIState.return_page and action order | MAP->PAUSE->HELP->BACK test |
| Text beyond screen | bounded strings, font scale, glyph capacity | Screenshot and length test |
| UI corrupts 3D shader | C2D_Flush, target switching, uniform reset | Mixed rendering test, not yet done |
| Wrong depth | reverse-Z, culling, shader matrices | Near/far rendered geometry check |
| Missing mesh | NIF, PPMG sizes and indices | Validated geometry and shader screenshot |
| Broken texture | tex3ds, UV, GPU texture ownership | Actual t3x + emulator sampling |
| Frame spikes | target swaps, allocations, synchronous IO | Measured C3D CPU/GPU frame timings |
| Audio underrun | real NDSP backend buffer lifetime | Only after backend exists |
| Out of memory | actual app grant, VRAM/linear allocations | Failed-allocation/cleanup test |
| Bad save | atomicity, path and checksum | Write/reopen/corruption test |
| Unsupported format | version/magic, targeted parser | Specific failure, never guess |
| Shutdown bug | partial ownership and target deletion | Controlled init failure + run |
| Missing controls | New 3DS only buttons versus fallback | Test Old+New control paths |

The right fixes start with source and measured evidence, not unsupported
game compatibility assumptions. Do not copy game files into public repo.
