"""Bounded structured diagnostics for actual native compiler and linker output.

No build command is run by this module. A log may contain arbitrary strings,
so normalize only observed lines and never pretend a proposed fix was applied.
"""
from __future__ import annotations
import re
from pathlib import Path

MAX_SIZE=2*1024*1024
MAX_FINDINGS=60
RULES=(
    ("missing-header","compile",re.compile(r"(?:fatal error:|error:).*(?:No such file or directory|file not found)",re.I),
     "Locate the include and install/provide the real matching dependency; validate with the same toolchain"),
    ("undefined-symbol","link",re.compile(r"(?:undefined reference to|undefined symbol:)",re.I),
     "Locate actual symbol definition or port the implementation; never link an empty dummy"),
    ("incompatible-architecture","toolchain",re.compile(r"(?:unrecognized command.line option|selected processor does not support|architecture of input file is incompatible|file in wrong format)",re.I),
     "Inspect target ISA, ABI flags and object architecture; rebuild correct ARM11 objects"),
    ("shader-failure","graphics",re.compile(r"(?:picasso:.*error|shader.*(?:syntax error|compile error)|vshader.*error)",re.I),
     "Inspect PICA200 shader source/uniform registers and rerun real Picasso compiler"),
    ("missing-asset","assets",re.compile(r"(?:no rule to make target.*(?:romfs|data|asset)|cannot open.*(?:romfs|data)|missing asset)",re.I),
     "Verify asset path, source rights and RomFS packaging, then test runtime loading"),
    ("memory-exhaustion","memory",re.compile(r"(?:out of memory|cannot allocate memory|std::bad_alloc|allocation failed)",re.I),
     "Measure active process grants/linear+VRAM pools and bound resources, then retest"),
    ("missing-library","link",re.compile(r"(?:cannot find -l|library not found for -l|No such file or directory.*\.a)",re.I),
     "Install compatible devkitPro portlibs or adapt library dependency; test actual linkage"),
    ("make-failure","build",re.compile(r"(?:make: \*\*\*|error: command failed)",re.I),
     "Review preceding compiler errors and failing target; preserve raw build log"),
)
def diagnose(log: str) -> dict:
    if not isinstance(log,str):
        raise ValueError("Build log must be text")
    if len(log.encode("utf-8",errors="replace"))>MAX_SIZE:
        raise ValueError("Build log exceeds 2 MiB bound")
    findings=[]
    for number,line in enumerate(log.splitlines(),1):
        if not line.strip():
            continue
        for rule,area,pattern,action in RULES:
            if pattern.search(line):
                findings.append({
                    "line":number,"kind":rule,"subsystem":area,
                    "evidence":line.strip()[:350],"next_action":action,
                    "correction_verified":False,
                    "verification":"Re-run the authentic build and the relevant runtime regression"})
                break
        if len(findings)>=MAX_FINDINGS:
            break
    return {
        "schema_version":1,"status":"diagnosed" if findings else "no-matching-patterns",
        "findings":findings,"findings_truncated":len(findings)>=MAX_FINDINGS,
        "observed_problem_count":len(findings),
        "note":"Heuristic log classification only. No source was changed or target run verified",
    }

def diagnose_file(path: Path) -> dict:
    path=Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size>MAX_SIZE:
        raise ValueError("Log missing, symlinked or larger than 2 MiB")
    return diagnose(path.read_text(encoding="utf-8",errors="replace"))
