# PocketPort Translation Runtime (PPTR): actual subset and extension contract

The current **PPTR v1** is a real, constrained IR-to-C translator integrated with a deterministic C runtime and interactive original game. It is **not** an ARM64 binary translator. See `pocketport/translation.py` and `tests/test_translation.py`.

## IR v1 language

```text
func score_bonus catches difficulty
add raw catches difficulty
const multiplier 3
mul result raw multiplier
ret result
end
```

- Input: plain UTF-8 PocketPort IR, original and redistributable. One function per input, 1-8 unique parameters.
- Type: `uint32_t`; constants 0 to `2^32-1`; `add`, `sub`, `mul` have unsigned modulo-2^32 semantics; SSA-like destination uniqueness.
- Output: C99 `score.h`/`score.c`, deterministic and cross-compilable; no heap, dynamic linking, exceptions or undefined signed overflow.
- Verification: Python reference interpreter compared with compiled C shared library through ctypes. Test inputs include modulo overflow.
- Integration: the generated `pp_score_bonus` is linked with `runtime/core/pp_game.c`, the host frontend and the 3DS source. A host compile plus regression demonstrates a real executable end-to-end subset, not a 3DS run.

```bash
python -m pocketport translate examples/translation-demo/score.ppir --out examples/source-port/generated
python -m pocketport verify-ir examples/translation-demo/score.ppir
python -m pocketport build examples/source-port/project.json --host
```

Invalid operands, unsupported operations, duplicate destinations and out-of-range constants produce failures. There are **no** control-flow branches, memory instructions, syscalls, dynamic symbols, pointers or floating point operations in v1.

## To add a real binary frontend

Architecture specific decoders must identify **format**, ISA revision, CPU mode, ABI, memory map, executable relocations, symbol table, linking model, endian mode, instruction semantics, indirect branches, floating-point behavior, exceptions and syscalls. Provide an oracle using original, legally tested behavior and distinguish reconstruction from interpretation. The frontend lifts only *proven* operations into an explicitly typed, reference-checked IR. A backend must maintain equivalent memory/state behavior and map OS/game APIs into actual libctru abstractions; unknown opcodes or unmapped syscalls **fail**, never no-op.

[REA](https://github.com/morluto/rea) is a possible evidence provider for supported native analysis targets; its MCP/CLI is not a Nintendo CIAs ROM parser. [N64Recomp](https://github.com/N64Recomp/N64Recomp) demonstrates a domain-specific N64 MIPS-to-C translation architecture with a required runtime; it does not provide a magic ARM64 decoder or make the PICA200 compatible with Switch graphics APIs. Read original code and project licensing before reuse.

## Runtime layers

- Host-side reference parser and interpreter: `pocketport/translation.py`.
- Generated C semantics: `examples/source-port/generated/score.c`.
- Portable game/utility code: `runtime/core/pp_game.c`, `runtime/core/pp_runtime.c`.
- Platform frontend (3DS only): `examples/source-port/source/main.c`.
- Graphics backend: direct citro2d primitives in original example, **not** a universal shader translation layer.

Any additional module must have native tests, a documented capability matrix and explicit unavailable-operation diagnostics. Do not create empty `cpu/` and `graphics/` folders and pretend those components exist.
