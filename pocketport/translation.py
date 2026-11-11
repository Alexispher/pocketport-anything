"""PocketPort IR v1 interpreter and C99 translation. Not a machine-code decompiler.

Language: `func NAME ARG ...`, `const DEST UNSIGNED`, `add|sub|mul DEST SRC SRC`,
`ret SRC`, `end`. uint32 modular arithmetic and masked 32-bit shifts. This is a *precisely scoped* IR backend.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
import tempfile
from shutil import which
import ctypes

NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
MOD = 1 << 32


class IRValidationError(ValueError):
    """An unsupported or invalid IR program must fail, never silently approximate."""


@dataclass(frozen=True)
class Instruction:
    op: str
    args: tuple[str, ...]


@dataclass(frozen=True)
class Program:
    name: str
    params: tuple[str, ...]
    body: tuple[Instruction, ...]


def _name(token: str) -> str:
    if not NAME.fullmatch(token) or len(token) > 60:
        raise IRValidationError(f"Invalid symbol: {token!r}")
    return token


def parse(source: str) -> Program:
    lines = [ln.strip().split("#", 1)[0].strip() for ln in source.splitlines()]
    lines = [ln for ln in lines if ln]
    if len(lines) < 3:
        raise IRValidationError("Expected func, instructions, ret, end")
    header, terminator = lines[0].split(), lines[-1]
    if len(header) < 3 or header[0] != "func" or terminator != "end":
        raise IRValidationError("Expected `func NAME ARG...` and final `end`")
    func = _name(header[1])
    params = tuple(_name(p) for p in header[2:])
    if len(params) > 8 or len(set(params)) != len(params):
        raise IRValidationError("Use 1-8 unique parameters")
    known = set(params)
    body = []
    for line in lines[1:-1]:
        tokens = line.split()
        op, args = tokens[0], tokens[1:]
        if op == "const":
            if len(args) != 2:
                raise IRValidationError("const requires destination and uint32 integer")
            dest = _name(args[0])
            if dest in known:
                raise IRValidationError(f"SSA variable already defined: {dest}")
            try:
                number = int(args[1], 0)
            except ValueError as exc:
                raise IRValidationError(f"Invalid constant {args[1]!r}") from exc
            if number < 0 or number >= MOD:
                raise IRValidationError("Constant must be 0 <= n < 2^32")
            args = [dest, str(number)]
            known.add(dest)
        elif op in ("add", "sub", "mul", "and", "or", "xor", "shl", "shr"):
            if len(args) != 3:
                raise IRValidationError(f"{op} needs dest and two operand registers")
            dest, a, b = map(_name, args)
            if dest in known:
                raise IRValidationError(f"SSA variable already defined: {dest}")
            if a not in known or b not in known:
                raise IRValidationError(f"Use of undefined operand in: {line}")
            known.add(dest)
        elif op == "ret":
            if len(args) != 1 or _name(args[0]) not in known:
                raise IRValidationError("ret requires a defined register")
        else:
            raise IRValidationError(f"Unsupported IR instruction: {op}")
        body.append(Instruction(op, tuple(args)))
    if sum(i.op == "ret" for i in body) != 1 or body[-1].op != "ret":
        raise IRValidationError("Exactly one final ret is required")
    return Program(func, params, tuple(body))


def execute(program: Program, *values: int) -> int:
    if len(values) != len(program.params):
        raise ValueError("Incorrect argument count")
    state = {p: v % MOD for p, v in zip(program.params, values)}
    for ins in program.body:
        if ins.op == "const":
            state[ins.args[0]] = int(ins.args[1])
        elif ins.op in ("add", "sub", "mul", "and", "or", "xor", "shl", "shr"):
            a, b = state[ins.args[1]], state[ins.args[2]]
            state[ins.args[0]] = {"add": lambda: a + b,
                                   "sub": lambda: a - b,
                                   "mul": lambda: a * b,
                                   "and": lambda: a & b,
                                   "or": lambda: a | b,
                                   "xor": lambda: a ^ b,
                                   "shl": lambda: a << (b & 31),
                                   "shr": lambda: a >> (b & 31)}[ins.op]() % MOD
        elif ins.op == "ret":
            return state[ins.args[0]]
    raise AssertionError("Parser guaranteed a return")


def emit_c(program: Program) -> tuple[str, str]:
    symbol = "pp_" + program.name
    decl = f"uint32_t {symbol}(" + ", ".join(f"uint32_t {p}" for p in program.params) + ")"
    header = ("/* Generated from PocketPort IR v1; uint32 wrap semantics. */\n"
              "#ifndef POCKETPORT_GENERATED_IR_H\n#define POCKETPORT_GENERATED_IR_H\n"
              "#include <stdint.h>\n" + decl + ";\n#endif\n")
    rows = ["/* Deterministic translator output; do not hand-edit. */", '#include "score.h"', decl + " {"]
    for ins in program.body:
        if ins.op == "const":
            rows.append(f"    uint32_t {ins.args[0]} = UINT32_C({ins.args[1]});")
        elif ins.op in ("add", "sub", "mul", "and", "or", "xor", "shl", "shr"):
            op = {"add": "+", "sub": "-", "mul": "*",
                  "and": "&", "or": "|", "xor": "^",
                  "shl": "<<", "shr": ">>"}[ins.op]
            rhs = (f"({ins.args[2]} & UINT32_C(31))" if ins.op in ("shl", "shr")
                   else ins.args[2])
            rows.append(f"    uint32_t {ins.args[0]} = {ins.args[1]} {op} {rhs};")
        else:
            rows.append(f"    return {ins.args[0]};")
    rows += ["}", ""]
    return header, "\n".join(rows)


def write_c(program: Program, destination: Path) -> tuple[Path, Path]:
    destination.mkdir(parents=True, exist_ok=True)
    h, c = emit_c(program)
    header = destination / "score.h"
    impl = destination / "score.c"
    header.write_text(h, encoding="utf-8")
    impl.write_text(c, encoding="utf-8")
    return header, impl


def verify_host(program: Program, vectors: list[tuple[int, ...]] | None = None) -> dict:
    """Compile translator output into a host shared object; compare to IR interpreter."""
    cc = which("cc") or which("gcc") or which("clang")
    if not cc:
        raise RuntimeError("No host C compiler found; cannot claim translation verified")
    if vectors is None:
        vectors = [(0,) * len(program.params), (1,) * len(program.params),
                   tuple((i + 2) * 3 for i in range(len(program.params))),
                   (0xffffffff,) * len(program.params)]
    with tempfile.TemporaryDirectory(prefix="pocketport-ir-") as tmp:
        out = Path(tmp)
        _, c = write_c(program, out)
        library = out / "test.so"
        command = [cc, "-std=c99", "-O2", "-Wall", "-Wextra", "-Werror", "-shared", "-fPIC", str(c), "-o", str(library)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
        if result.returncode:
            raise RuntimeError(f"Host translator compile failed ({result.returncode}): {result.stderr}")
        fn = getattr(ctypes.CDLL(str(library)), "pp_" + program.name)
        fn.argtypes = [ctypes.c_uint32] * len(program.params)
        fn.restype = ctypes.c_uint32
        for case in vectors:
            expected, actual = execute(program, *case), fn(*case)
            if expected != actual:
                raise AssertionError(f"Interpreter/C mismatch {case}: {expected} != {actual}")
        return {"status": "host-verified", "vectors_passed": len(vectors),
                "compiler": cc, "command": command,
                "boundary": "PocketPort IR uint32 arithmetic/bitwise/shift subset only; NOT arbitrary machine binaries or 3DS execution"}
