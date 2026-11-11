#!/usr/bin/env python3
"""Embed a compiled shader into C without external bin2s or xxd dependencies."""
import pathlib
import sys
if len(sys.argv) != 3:
    raise SystemExit("usage: embed_shbin.py INPUT.shbin OUTPUT.c")
data = pathlib.Path(sys.argv[1]).read_bytes()
if not data:
    raise SystemExit("empty compiled shader")
body = ",".join(str(n) for n in data)
pathlib.Path(sys.argv[2]).write_text(
    "#include <stdint.h>\n"
    "const uint32_t pp_vshader_size = " + str(len(data)) + "u;\n"
    "const unsigned char pp_vshader[] __attribute__((aligned(4))) = {" + body + "};\n",
    encoding="utf-8")
