# PocketPort IR translation/recompilation proof

This demonstration uses original source-level PocketPort IR v1, **not** decoded ARM64/MIPS/x86 instructions. Its parser validates SSA-like registers, `uint32` modulo arithmetic, and defined `const`, `add`, `sub`, `mul`, `ret` instructions. The C generator emits standard portable C99, and `verify-ir` compiles it with host GCC/Clang and compares actual output from the executable shared library with the Python interpreter on fixed vectors including overflow.

The same generated `score.c` is linked into the real game core at `../source-port/`, which can be built for the host or cross-compiled with a fully configured devkitARM toolchain. No generic binary lifting is claimed.

```bash
python -m pocketport translate examples/translation-demo/score.ppir --out examples/source-port/generated
python -m pocketport verify-ir examples/translation-demo/score.ppir
```
