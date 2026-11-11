# AAA Game Investigation — Implemented Scope

PocketPort includes bounded, **read-only engine-family detection** and ELF/PE
executable-header inspection. These identify candidate technology and
architecture; they do not port a commercial game, unpack encryption, or run a
foreign executable.

## Usage

```bash
python -m pocketport detect-engine /authorized/isolated-game-copy
python -m pocketport inspect-executable /authorized/isolated-game-copy/main.elf
python -m pocketport research "GTA SA"
python -m pocketport discover-ports "Skyrim"
python -m pocketport discover-ports "GTA San Andreas" --live --limit 5
python -m pocketport compatibility /authorized/isolated-game-copy --target new3ds
python -m pocketport.mcp --workspace /authorized/isolated-game-copy
```

The detector recognizes corroborating Unity Mono/IL2CPP files, UE3 package
magic, UE4/5 container pairing, Bethesda BSA+TES4 combinations, RenderWare
TXD+IMG, RAGE RPF, REDengine CR2W, and id Tech 3 IBSP+PK3.
Multiple matching families remain ambiguous. A filename alone does not
establish identity. The executable inspector parses only bounded ELF and
PE headers; it does not recover imported APIs or implement an ISA backend.

The local research catalogue `knowledge/aaa_targets.json` contains
AAA *investigation cases* and candidate routes, not working 3DS ports.
Unknown titles are reported as unknown. Optional live GitHub discovery
searches only public repository metadata. Its matches are unverified
leads: check forks, commits, release builds, licensing, test logs and
source code before drawing conclusions.

The stdio MCP server exposes exactly five read-only tools and limits
all file paths to an explicitly authorized workspace. No arbitrary
command execution, write operations, or software installation is exposed.
GitHub/network search is a separate opt-in CLI function.

## Prior 3DS engineering evidence

- [Super Mario 64 3DS](https://github.com/sm64-port/sm64_3ds):
  source/decompilation with a dedicated 3DS graphics/backend pipeline.
- [ctrQuake](https://github.com/masterfeizz/ctrQuake):
  source-based Quake port, with platform-specific controls/data.
- [DevilutionX](https://github.com/diasurgical/devilutionX):
  engine reconstruction with 3DS platform adaptation.
- [Ship of Harkinian 3DS](https://github.com/999sian/soh-3ds):
  experimental PICA200 backend, not modern Switch 2 NUP execution.
- [Co-op Anything](https://github.com/cranebeaker/coop-anything):
  triage-first architecture, versioned evidence and bounded-agent QA.
- [Lichii](https://github.com/zortos293/Lichii):
  GPL-3.0-or-later emulator and NUP metadata reference only; GPL code
  is not copied into this MIT repository.

## AAA case study boundaries

**Modern Zelda NUP:** the existing NUP reader authenticates the package
index, not game provenance, member integrity, or ARM11 compatibility.
The existing 3DS OoT release and experimental SoH 3DS port are different
engine lines, not ports of that newer executable.

**GTA San Andreas:** a matched TXD/IMG format is not a source engine.
A GTA III reconstruction must not be described as San Andreas support.

**Skyrim and Fallout New Vegas:** matched Bethesda archives can guide
format investigation. OpenMW targets Morrowind, not Skyrim or Fallout.

**GTA V, Cyberpunk, Breath of the Wild and Tears of the Kingdom:**
native execution is unverified; study constrained reconstruction/demake
routes, not a fictitious automatic machine-code converter.

## Evidence gates

Store game build ID, original hashes, matching header clues, named
source/project commits, license and process memory measurements.
Host tests are not cross-compilation. Emulator boot is not hardware
gameplay or a full-game validation.
