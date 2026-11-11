<div align="center">

# 🎮 PocketPort Anything

### Investigate anything. Engineer the port. Prove it runs.

**An open-source, AI-assisted research and engineering framework for adapting games to Nintendo 3DS.**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Target: Nintendo 3DS](https://img.shields.io/badge/Target-Nintendo%203DS-e60012)](docs/HARDWARE.md)
[![Status: Experimental](https://img.shields.io/badge/Status-Experimental-orange)](docs/COMPATIBILITY.md)
[![GitHub Actions](https://github.com/Alexispher/pocketport-anything/actions/workflows/tests.yml/badge.svg)](https://github.com/Alexispher/pocketport-anything/actions)

**[Quick Start](#-quick-start) · [Features](#-what-works-today) · [AAA Ambitions](#-aaa-game-research-program) · [Architecture](#-architecture) · [Roadmap](#-development-roadmap) · [AI Agents](#-ai-agents-and-skills) · [Contributing](#-contributing)**

</div>

---

> [!IMPORTANT]
> **“Anything” describes the scope of investigation, not a promise of universal compatibility.** PocketPort Anything is **not** a Switch/Switch 2 emulator, a one-click commercial-game converter, or a complete ARM64/x86/MIPS-to-ARM11 recompiler. Its current working components are real but deliberately limited. This README distinguishes **implemented features**, **validated host behavior**, and **future engineering goals**.

## 🌌 The vision

**What if an AI coding agent could investigate *any* game, understand what makes it run, locate reusable implementations, plan a Nintendo 3DS adaptation, build the necessary components, and prove what actually works?**

That is the ambition behind **PocketPort Anything**.

The project is designed to grow from a reproducible porting toolkit into a research-driven, engine-aware framework. Rather than maintaining a small whitelist of compatible titles, the long-term approach is to:

1. **Identify** a game, its engine, architecture, formats, and dependencies.
2. **Research** existing source ports, decompilations, recompilers, SDKs, forks, and prior attempts.
3. **Choose** the strongest engineering route: native source port, reconstruction, asset adaptation, targeted reimplementation, or a clearly labeled alternative.
4. **Adapt** graphics, audio, input, filesystem, memory use, and executable behavior to 3DS constraints.
5. **Build** reproducibly using the real Nintendo 3DS toolchain.
6. **Validate** with unit tests, native builds, emulators, and—when available—physical hardware.
7. **Record** evidence and reusable knowledge for future games.

The focus is ambitious: **large, complex 3D games and their engines**. Small original demonstrations are used to validate the infrastructure, **not** presented as finished AAA ports.

## 📍 Project status

| Area | Current implementation | Evidence / boundary |
|---|---|---|
| Python CLI | **Implemented** | Inspection, planning, initialization, translation, asset optimization, builds, tests, reports |
| File inventory | **Implemented** | SHA-256, file signatures and read-only inventory |
| NUP v1 metadata inspection | **Implemented** | Header and authenticated index inspection; no extraction or game execution |
| PocketPort IR → C99 | **Implemented, limited** | Defined uint32 IR subset; **not** arbitrary machine code |
| IR interpreter and equivalence checks | **Implemented** | Host-side comparison against compiled generated C |
| Original C game runtime | **Implemented** | Star Catcher gameplay core and deterministic host tests |
| Native 3DS example sources | **Implemented as source** | libctru/citro2d template; build needs devkitPro |
| Asset image preparation | **Implemented** | Pillow-based resizing/padding; optional `tex3ds` integration |
| Automated host tests | **Implemented** | Python and native C regression coverage |
| Engine fingerprinting across AAA games | **Experimental** | Bounded family/header candidates; not full game verification |
| Public GitHub port candidate discovery | **Experimental** | Optional metadata-only search; no verification of builds, branches or gameplay |
| General-purpose binary lifting/recompilation | **Research goal** | Not implemented |
| Full AAA game port | **Not demonstrated** | No commercial game claimed playable |
| Physical 3DS performance validation | **Not demonstrated here** | Requires device/toolchain and repeatable measurements |

**Version note:** the supplied integrated archive is labeled **v0.3.1**, while `pyproject.toml` and some documentation still identify the package as **0.2.0**. Version metadata should be synchronized in a separate reviewed change.

> [!NOTE]
> Earlier host-side validation reported passing regression tests and a working native demonstration. These do **not** prove that any AAA game—or even the example—has been successfully launched on a physical Nintendo 3DS. See [validation records](docs/VALIDATION_THIS_RELEASE.md).

## 🚀 Quick start

### Requirements

- **Python 3.10+**
- A C compiler such as GCC or Clang for host-side native tests
- Optional: Pillow for image processing
- Optional: devkitPro/devkitARM and 3DS libraries for console builds

Clone the repository:

```bash
git clone https://github.com/Alexispher/pocketport-anything.git
cd pocketport-anything
```

Run the environment diagnostics:

```bash
python -m pocketport doctor
```

Inspect a directory **without modifying its files**:

```bash
python -m pocketport inspect examples/asset-pipeline/assets
```

Generate an evidence-gated porting plan:

```bash
python -m pocketport plan examples/asset-pipeline/assets --target new3ds
```

Run the tests:

```bash
python -m unittest discover -s tests -v
# Optional, if pytest is installed:
python -m pytest -q
```

Run the original integrated demonstration:

```bash
python -m pocketport demo --out /tmp/pocketport-unified-demo
```

> On Windows, replace `/tmp/...` with a writable directory such as `.\output\...`.

### Install the optional image dependencies

```bash
python -m pip install -r requirements-optional.txt
```

### Inspect an authorized NUP file

```bash
python -m pocketport inspect-nup "/path/to/authorized/game.nup"
```

The NUP reader is **read-only**. It inspects structural metadata and checks index integrity. It does **not** extract game data, decrypt files, identify a title with certainty, or port an executable.

## 🧰 What works today

### 1. File and game-workspace inspection

PocketPort can inventory a local directory, collect file metadata, compute hashes, and identify some file signatures. It can create isolated project workspaces and emit structured reports.

```bash
python -m pocketport hash /path/to/file
python -m pocketport inspect /path/to/directory --out inventory.json
python -m pocketport manifest /path/to/directory --out manifest.json --game "My Game" --target new3ds
python -m pocketport init ./my-game-port --game "My Game" --target new3ds
```

The `init` command creates a separate `work-private/` area for locally authorized inputs and an `output/` area for generated artifacts. **Do not commit these private files.**

### 2. Evidence-first route planning

The route planner works with **explicit evidence**, rather than inventing a porting method from a game title.

```bash
python -m pocketport plan ./my-game-port --target new3ds --evidence evidence.json
```

Its recommendations are limited by the evidence supplied. It does not currently discover or verify arbitrary source ports automatically.

Read [Porting Strategies](docs/PORTING_STRATEGIES.md), [Routes](docs/ROUTES.md), and [Compatibility](docs/COMPATIBILITY.md).

### 3. PocketPort IR translation

The project includes a **real, scoped translation pipeline**:

```text
PocketPort IR source
       ↓
IR parser
       ↓
Reference interpreter
       ↓
C99 source generator
       ↓
Host C compiler
       ↓
Behavioral equivalence tests
```

The defined IR currently supports a small set of unsigned 32-bit operations, including arithmetic, bitwise operators, shifts, constants, and return behavior as implemented by the repository.

```bash
python -m pocketport translate examples/translation-demo/score.ppir --out ./output/translated
python -m pocketport verify-ir examples/translation-demo/score.ppir
```

**This is not an ARM64, MIPS, x86, or x86-64 binary translator.** Function lifting, memory semantics, full control-flow recovery, ABI compatibility, syscalls, and graphics API replacement remain major research and implementation challenges.

See [Translation Runtime](docs/TRANSLATION_RUNTIME.md).

### 4. Original playable demonstration: Star Catcher

The repository includes an original C game demonstrating the integration of:

- Portable gameplay logic
- Generated C scoring logic
- Native host execution
- Deterministic gameplay regression tests
- 3DS frontend source and toolchain integration

```bash
python -m pocketport build examples/source-port/project.json --host
python -m pocketport test examples/source-port/project.json --host
python -m pocketport report examples/source-port/project.json --out ./output/report.json
```

After a successful host build, the example's executable is generated in its host build directory. A **PC build is not a 3DS build**.

### 5. Asset preparation and hardware-aware profiles

The image pipeline can prepare supported bitmap resources with profile-based processing and optional use of Nintendo 3DS texture tooling:

```bash
python -m pocketport optimize examples/asset-pipeline/manifest.json \
  --out ./output/assets --profile balanced
```

This is **not** a universal commercial-game asset converter. Proprietary model formats, shader translation, scene reconstruction, and engine-specific audio pipelines are not generally supported.

See [Graphics](docs/GRAPHICS.md) and [Optimization](docs/OPTIMIZATION.md).

### 6. NUP v1 structural analysis

The integrated NUP module inspects an NUP v1 archive's metadata, including its signature, header structure, package index, and SHA-256 integrity information.

**Important distinction:** the NUP format described by the Lichii project is an **emulator-specific container format**; a `.nup` extension alone does not establish that a file is an official Nintendo package or that its contents can execute on 3DS.

Reference: [Lichii](https://github.com/zortos293/Lichii) and [Zelda Case Study](docs/ZELDA_CASE_STUDY.md).

## 🕹️ Nintendo 3DS build target

PocketPort targets both **Old Nintendo 3DS** and **New Nintendo 3DS**, with platform differences treated as engineering constraints rather than interchangeable performance profiles.

The intended native stack includes:

| Component | Purpose |
|---|---|
| [devkitPro / devkitARM](https://devkitpro.org/) | ARM cross-compilation and development environment |
| [libctru](https://github.com/devkitPro/libctru) | Nintendo 3DS system services |
| [citro3d](https://github.com/devkitPro/citro3d) | 3DS graphics interface |
| [citro2d](https://github.com/devkitPro/citro2d) | Higher-level 2D graphics |
| `tex3ds` | Supported texture conversion workflows |
| [3ds-examples](https://github.com/devkitPro/3ds-examples) | Official development examples |
| [Azahar](https://github.com/azahar-emu/azahar) | Emulator testing, when available |

With the required toolchain installed:

```bash
python -m pocketport build examples/source-port/project.json --console
# or
make -C templates/3ds-homebrew
```

**No toolchain?** The build must fail clearly. PocketPort must never generate a fake `.3dsx` or mislabel a host executable as a console build.

### Why AAA ports are hard

The 3DS is a constrained handheld platform. Major obstacles include:

- Different instruction sets and operating-system APIs
- Severe memory and GPU resource limitations relative to modern consoles
- Shader and material incompatibility
- CPU-heavy simulation, physics, AI, and streaming
- Proprietary asset containers and middleware
- Large world and level data
- Save, audio, input, and threading assumptions

A successful port often requires **rewriting systems**, **reducing content complexity**, or **reconstructing a compatible engine**—not just changing a compiler target.

## 👑 AAA game research program

**Our ambition is big games.** The following are **research targets**, not currently supported games.

| Research target | Engineering focus | Current PocketPort status |
|---|---|---|
| **The Legend of Zelda: Ocarina of Time** | Native 3DS modding, source-port reuse, modernized assets, NUP research | Case study and NUP metadata tools |
| **Grand Theft Auto: San Andreas** | RenderWare, asset formats, handheld optimization | Research target |
| **The Elder Scrolls V: Skyrim** | Creation Engine, archive formats, world streaming | Research target |
| **Fallout 3 / New Vegas** | Gamebryo, engine dependencies, asset pipelines | Research target |
| **Dark Souls** | Proprietary engine analysis, rendering and memory | Research target |
| **Resident Evil 4** | Engine-specific adaptation and resource budgeting | Research target |
| **GTA V / Red Dead Redemption** | RAGE architecture, feasibility assessment | Extreme research targets |
| **Breath of the Wild / Tears of the Kingdom** | Large-scale world streaming and hardware feasibility | Extreme research targets |
| **The Witcher 3 / Cyberpunk 2077** | REDengine architecture, feasibility and alternative approaches | Extreme research targets |

A **native port**, **engine reconstruction**, **demake**, and **streaming client** are different outcomes and must never be conflated.

### Zelda: a concrete case study

The project documents several distinct routes for studying *Ocarina of Time*:

1. **Ocarina of Time 3D** — research authorized modifications to an engine already designed for 3DS.
2. **[zeldaret/oot3d](https://github.com/zeldaret/oot3d)** — study the work-in-progress 3DS decompilation.
3. **[Ship of Harkinian](https://github.com/HarbourMasters/Shipwright)** — examine source-port architecture and its asset preparation model.
4. **[soh-3ds](https://github.com/999sian/soh-3ds)** — investigate an experimental native 3DS adaptation.
5. **[oot3d-texkit](https://github.com/folxxsreal/oot3d-texkit)** — study narrowly scoped texture workflows.
6. **[Lichii](https://github.com/zortos293/Lichii)** — inspect the documented NUP format and host-side emulator architecture.

The repository's NUP analysis does **not** establish that a specific game is genuine, that a modern remake has been independently verified, or that any modern console executable is portable to ARM11.

See the full [Zelda Case Study](docs/ZELDA_CASE_STUDY.md).

## 🧠 The “Anything” philosophy

PocketPort is inspired by the **methodology** of projects such as [Co-op Anything](https://github.com/cranebeaker/coop-anything): investigate a game, identify existing work, choose a game-specific technical path, test actual behavior, and preserve discoveries for future projects.

**The distinction matters:** Co-op Anything primarily modifies games on platforms that already run them. PocketPort must additionally solve the problem of executing or reconstructing software on a fundamentally different device.

Our long-term framework should support these routes:

| Route | When it is appropriate |
|---|---|
| Native source port | Game or compatible engine source is available |
| Decompilation-based port | A verified reconstruction provides a suitable codebase |
| Static recompilation | Supported architecture and runtime can be faithfully modeled |
| Engine reimplementation | Original runtime cannot be reused, but behavior can be reconstructed |
| Asset/graphics adaptation | An existing 3DS game or engine can host authorized modified content |
| Demake | Fidelity-preserving native execution is not feasible |
| Streaming | Remote execution is chosen explicitly; **not** advertised as a native port |

No route guarantees success.

## 🏗️ Architecture

```text
                      USER / AI AGENT
                             │
                   PocketPort Python CLI
                             │
        ┌────────────────────┼─────────────────────┐
        │                    │                     │
   Inspection           Evidence-based         Workspaces
  SHA-256 / NUP            Planning          / Manifests
        │                    │                     │
        └────────────────────┼─────────────────────┘
                             │
                    Scoped Translation
                   PocketPort IR → C99
                             │
                 Original Portable C Core
                             │
        ┌────────────────────┴─────────────────────┐
        │                                          │
    Host Build                               3DS Toolchain
   GCC / Clang                           devkitARM / libctru
        │                                          │
   Host-side QA                         Console build output
        │                                          │
        └────────────────────┬─────────────────────┘
                             │
                     Evidence Reports
```

### Source tree

```text
pocketport/
├── cli.py             # Command-line entry points
├── inventory.py       # File inventory and hashing
├── nup.py             # Read-only NUP v1 metadata inspection
├── planning.py        # Evidence-based route selection
├── translation.py     # PocketPort IR and C99 generation
├── assets.py          # Image preparation
├── build.py           # Build, test, report integration
├── environment.py     # Toolchain diagnostics
└── demo.py            # Integrated original demonstration

runtime/core/          # Portable C game and runtime
templates/3ds-homebrew/# Nintendo 3DS source template
examples/              # Original reproducible examples
tests/                 # Python and native regression tests
docs/                  # Architecture, research, limits, evidence
.agents/skills/        # AI-agent guidance
.github/workflows/     # CI
```

See [Architecture](docs/ARCHITECTURE.md) and [Tooling](docs/TOOLING.md).

## 🤖 AI agents and skills

PocketPort provides repository instructions for AI coding agents:

- [`AGENTS.md`](AGENTS.md) — engineering rules and evidence requirements
- [`SKILL.md`](SKILL.md) — project-level skill guidance
- [`.agents/skills/pocketport-anything/SKILL.md`](.agents/skills/pocketport-anything/SKILL.md) — reusable skill

### Example agent prompt

```text
Read https://github.com/Alexispher/pocketport-anything
and follow AGENTS.md and .agents/skills/pocketport-anything/SKILL.md.

Investigate how [GAME] could be adapted for New Nintendo 3DS.

Start by auditing the existing code and identifying the actual game,
engine, platform, available source ports, and known limitations.

Preserve working functionality. Implement one verifiable improvement,
run tests, record evidence, and clearly separate research from
features that actually work. Never claim a native port without
a real native build and runtime validation.
```

### Future agent architecture

Planned improvements include engine detection, source-port discovery, a structured compatibility knowledge base, specialized engine adapters, tool interfaces for agents, and reproducible emulator/hardware QA.

These are **roadmap items**, not existing CLI commands.

## 🧪 Testing and evidence

PocketPort uses an **evidence-first** development philosophy.

| Evidence level | What it means |
|---|---|
| Identified | Inputs and environment have been described |
| Analyzed | Formats and dependencies have been inspected |
| Translated | A defined code subset has passed semantic tests |
| Host-built | Executable compiles and runs on a host PC |
| Console-built | Real devkitARM build produces a valid console artifact |
| Emulator-booted | Emulator successfully launches the artifact |
| Interactive | Input, graphics, and game logic operate |
| Hardware-validated | Physical 3DS execution has been observed and recorded |
| Full-game-validated | Relevant complete-game scenarios have passed |

These descriptions express a **validation ladder**, not a claim that all levels have been achieved.

Every important result should preserve:

- Exact command
- Tool and version
- Source revision
- Input hashes
- Target device or emulator
- Output artifact
- Logs
- Known failures and limitations

Run the included regression suite:

```bash
python -m unittest discover -s tests -v
```

Consult [Testing](docs/TESTING.md), [Validation](docs/VALIDATION.md), and [Validation This Release](docs/VALIDATION_THIS_RELEASE.md).

## 🗺️ Development roadmap

### Phase 1 — Solid engineering foundation

- [x] Python CLI and project workspace
- [x] Read-only file inventory and hashes
- [x] Evidence-based planning
- [x] Scoped PocketPort IR → C99
- [x] Original C gameplay demonstration
- [x] Host regression tests
- [x] 3DS template and source frontend
- [x] Image preparation pipeline
- [x] Read-only NUP v1 metadata reader

### Phase 2 — Engine-aware investigation

- [ ] Evidence-based detection of common AAA engines
- [ ] Executable architecture and dependency inspection
- [ ] Automatic search for source ports and decompilation projects
- [ ] Structured compatibility knowledge base
- [ ] Engine-family research adapters
- [ ] Machine-readable feasibility reports

### Phase 3 — Real porting infrastructure

- [ ] Extended IR and control-flow semantics
- [ ] Tested architecture-specific translation subsets
- [ ] Graphics and material compatibility adapters
- [ ] Audio, input, filesystem, and save adapters
- [ ] Asset streaming and memory budgets
- [ ] Reusable build profiles for Old/New 3DS

### Phase 4 — AAA-focused validation

- [ ] Reproducible end-to-end build of a substantial existing 3D codebase
- [ ] Emulator startup and graphics validation
- [ ] Physical 3DS performance measurements
- [ ] Verified Zelda adaptation experiment
- [ ] Verified RenderWare/GTA investigation workflow
- [ ] Public compatibility reports with reproducible evidence

**The roadmap prioritizes difficult games, but does not imply that every game can run on 3DS hardware.**

## 📚 Research and references

### Nintendo 3DS development

- [devkitPro](https://devkitpro.org/)
- [libctru](https://github.com/devkitPro/libctru)
- [citro3d](https://github.com/devkitPro/citro3d)
- [citro2d](https://github.com/devkitPro/citro2d)
- [3ds-examples](https://github.com/devkitPro/3ds-examples)
- [Azahar emulator](https://github.com/azahar-emu/azahar)

### Porting, recompilation and reverse engineering

- [Co-op Anything](https://github.com/cranebeaker/coop-anything)
- [N64Recomp](https://github.com/N64Recomp/N64Recomp)
- [REA — Reverse Engineer Anything](https://github.com/morluto/rea)
- [Ship of Harkinian](https://github.com/HarbourMasters/Shipwright)
- [zeldaret/oot3d](https://github.com/zeldaret/oot3d)
- [soh-3ds](https://github.com/999sian/soh-3ds)
- [Lichii](https://github.com/zortos293/Lichii)

Links are **research references**, not statements that these projects are dependencies, endorsed integrations, or license-compatible code sources.

### Internal documentation

| Document | Topic |
|---|---|
| [Architecture](docs/ARCHITECTURE.md) | System organization |
| [Compatibility](docs/COMPATIBILITY.md) | Supported and unsupported features |
| [Hardware](docs/HARDWARE.md) | 3DS constraints |
| [Graphics](docs/GRAPHICS.md) | Rendering considerations |
| [Optimization](docs/OPTIMIZATION.md) | Asset and performance approaches |
| [Porting Strategies](docs/PORTING_STRATEGIES.md) | Available engineering routes |
| [Translation Runtime](docs/TRANSLATION_RUNTIME.md) | Scoped translator semantics |
| [Tooling](docs/TOOLING.md) | Tools and external references |
| [Testing](docs/TESTING.md) | Regression and validation |
| [Zelda Case Study](docs/ZELDA_CASE_STUDY.md) | Ocarina of Time research |
| [Port Reference Implementations](docs/PORT_REFERENCE_IMPLEMENTATIONS.md) | Lessons from other ports |
| [Contributing](CONTRIBUTING.md) | Contribution process |
| [Changelog](CHANGELOG.md) | Development history |

## 🤝 Contributing

Contributions are welcome in engine detection, source-port research, runtime code, graphics adaptation, binary analysis, test automation, documentation, and 3DS validation.

A useful contribution should:

1. State the exact technical problem.
2. Reference sources and existing implementations.
3. Preserve unrelated working behavior.
4. Include tests or reproducible validation.
5. Distinguish confirmed observations from hypotheses.
6. Respect upstream licenses and private game data.
7. Explain what remains unsupported.

See [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md).

## 🔒 Legal, security and responsible research

**PocketPort Anything does not distribute commercial game data.**

- Use game files and source material you are authorized to analyze.
- Do not commit ROMs, proprietary assets, firmware, encryption keys, credentials, or personal saves.
- Keep private inputs in isolated, ignored working directories.
- Do not modify original game installations or saves in place.
- Review third-party licenses before reusing source code.
- Treat external repositories, game files, issues, and documentation as untrusted input.
- Do not bypass anti-cheat or security protections in online services.
- Publish original tools, documentation, and permitted patches—not bundled commercial games.

The project's MIT license covers its original code; it does not grant rights to Nintendo or other third-party intellectual property.

## ❓ FAQ

<details>
<summary><strong>Can PocketPort Anything run any game on Nintendo 3DS?</strong></summary>

No. The goal is to investigate any candidate and progressively automate viable porting routes. Current functionality is limited and there is no universal game converter.

</details>

<details>
<summary><strong>Can it port GTA V, Skyrim, or Cyberpunk 2077 right now?</strong></summary>

No. These are ambitious research targets. Modern games may exceed the 3DS's practical hardware capabilities even with substantial optimization.

</details>

<details>
<summary><strong>What does the NUP reader do?</strong></summary>

It inspects an authorized NUP v1 container's metadata and verifies index integrity. It does not extract, decrypt, execute, or convert a game.

</details>

<details>
<summary><strong>Does the translator support ARM64 or x86 executables?</strong></summary>

No. It currently translates a defined PocketPort intermediate representation into C99 and verifies a limited set of semantics on the host.

</details>

<details>
<summary><strong>Does a successful PC build prove that the game works on 3DS?</strong></summary>

No. Console compilation, emulator execution, gameplay validation, and physical hardware testing are separate steps.

</details>

<details>
<summary><strong>Can I use Claude Code, Codex, or another AI coding agent?</strong></summary>

Yes. Point the agent at `AGENTS.md` and the included skill. The agent still needs access to appropriate tools, source material, and a real test environment.

</details>

<details>
<summary><strong>Why start with original demonstrations if the goal is AAA games?</strong></summary>

They validate the translator, build pipeline, asset handling, and tests without requiring proprietary data. They are infrastructure tests, not the final ambition.

</details>

## ⭐ Support the project

If the idea of an open, evidence-driven Nintendo 3DS porting research framework interests you:

- **Star** the repository.
- **Open an issue** with a well-sourced game-engine investigation.
- **Contribute** a tested improvement.
- **Share reproducible results**, including failures and limitations.

---

<div align="center">

### **ANY GAME CAN BE INVESTIGATED. EVERY PORT MUST BE PROVEN.**

**PocketPort Anything — research boldly, build carefully, validate everything.**

[Repository](https://github.com/Alexispher/pocketport-anything) · [Issues](https://github.com/Alexispher/pocketport-anything/issues) · [License](LICENSE)

</div>


## 🔬 AAA investigation — implementation update

The existing runtime, NUP parser and PPIR translator are preserved. The new
read-only `detect-engine` command reports bounded engine-family clues (Unity,
Unreal, Bethesda, RenderWare, RAGE, REDengine, id Tech); `inspect-executable`
reports ELF/PE machine architecture from headers without executing binaries.
`research "GTA SA"` consults a small offline AAA investigation catalogue, while
`discover-ports "Skyrim" --live` optionally searches public GitHub repository
metadata. These are **unverified candidates**, not working commercial ports.
`compatibility /isolated/game --target new3ds` tracks unknown memory grants
separately from on-disk bytes. A restricted, read-only stdio MCP integration
is available via `python -m pocketport.mcp --workspace /isolated/game`.
Read [AAA investigation](docs/AAA_INVESTIGATION.md) for commands, source links
and exact support boundaries. No arbitrary ARM64 or 3DS AAA game conversion is
claimed. The project is still unvalidated on Azahar and physical 3DS hardware.


## Skyrim 2011 native-runtime proof-of-concept

The experimental `pocketport.skyrim` package implements a read-only BSA 104
index/member decoder, TES5 plugin STAT/CELL/REFR scanner, DXT1 DDS to RGB565
**intermediate** conversion and PPSC v1 static placement scene serialization.
A portable C loader validates these packages. The new Citro3D frontend (source
only until cross-built) draws reference **markers**, not Skyrim's actual NIF
geometry, lighting, or gameplay. No original assets are in git.

For commands and exact boundaries, see [Skyrim Native Initiative](docs/SKYRIM_NATIVE.md).
