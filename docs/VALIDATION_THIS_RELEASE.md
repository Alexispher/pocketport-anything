# Release v0.2 — observed validation ledger

**Observed in the implementation environment on November 11, 2026:** Python 3.13.5, Pillow 12.3.0, GCC through `/usr/bin/cc`, Linux host; Nintendo 3DS toolchain (`arm-none-eabi-gcc`, `3dsxtool`, `picasso`, `tex3ds`) unavailable. `python -m pocketport doctor` independently confirmed this in the same session.

| Check | Actually executed result |
| --- | --- |
| Python import/syntax | `python -m compileall -q pocketport`: passed |
| Unit/integration suite | `python -m unittest discover -s tests -v`: **24 passed** |
| Scoped PocketPort IR -> C | Host compilation passed and 4 reference vectors matched (including overflow) |
| Original Star Catcher host build | GCC `-std=c99 -Wall -Wextra -Werror` passed, real executable generated |
| Star Catcher gameplay regression | Four deterministic scenarios passed, including score increase on catching star |
| Portable runtime | Compiled and executed native C test of memory budgets, input mapping, path validation and scoring |
| Original assets | Two images processed successfully with Pillow; intermediate PNGs, not `.t3x` |
| Integrated demo | `python -m pocketport demo --out ...` completed inventory → plan → translation → assets → GCC build → gameplay regression → report |
| Hardware `tex3ds` output | **Not executed; `tex3ds` unavailable** |
| devkitARM native 3DS build | **Not executed; required toolchain unavailable** |
| Azahar emulator launch | **Not executed** |
| Physical Old/New 3DS hardware | **Not executed** |
| Full commercial game port | **Not attempted or claimed** |

The host executable checksum is available in the generated `build-host/build-evidence.json`, and the generated unified demo report records commands, intermediate output and evidence hashes. Local ephemeral logs and binaries are omitted from the public source ZIP. Cross-compilation and emulator/hardware validation must be run before any console-ready release claim. Actual 3DS evidence level is L0 for this original game: identified, not compiled for 3DS.
