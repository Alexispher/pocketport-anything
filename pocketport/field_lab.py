"""Read-only field lab for per-frame telemetry and same-build evidence bookkeeping.

This module does not execute the game, observe an emulator, verify a human's
gameplay claim, or compile a binary. It validates data and artifact integrity.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from pathlib import Path
from statistics import mean

MAX_CSV_BYTES = 4 * 1024 * 1024
MAX_MANIFEST_BYTES = 64 * 1024
MAX_FRAMES = 50000
MAX_SCENARIOS = 128
MAX_ARTIFACT_BYTES = 128 * 1024 * 1024
TARGETS = frozenset(("old3ds", "new3ds"))
ENVIRONMENTS = frozenset(("host", "emulator", "hardware"))
RESULTS = frozenset(("pass", "fail", "untested"))
NUMERIC = (
    "frame_ms", "cpu_ms", "gpu_ms", "stream_ms", "draw_calls",
    "heap_free_kb", "linear_free_kb", "vram_free_kb",
)
MIN_MEMORY = ("heap_free_kb", "linear_free_kb", "vram_free_kb")
CORE_SCENARIOS = (
    "boot", "movement", "interaction", "transition", "pause-resume",
    "audio", "save-load", "shutdown",
)
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
ID_RE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")


class FieldLabError(ValueError):
    """Input rejected before any command execution (none is performed)."""


def _regular_file(path: Path, limit: int) -> Path:
    p = Path(path)
    if p.is_symlink() or not p.is_file():
        raise FieldLabError("File missing, not regular, or symlinked: " + str(p))
    size = p.stat().st_size
    if size > limit:
        raise FieldLabError("Input file exceeds size bound: " + str(p))
    return p


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return round(ordered[max(0, math.ceil(len(ordered) * fraction) - 1)], 3)


def _stats(values: list[float], budget: float) -> dict:
    return {
        "frames": len(values),
        "p50_ms": _percentile(values, 0.50),
        "p95_ms": _percentile(values, 0.95),
        "p99_ms": _percentile(values, 0.99),
        "mean_ms": round(mean(values), 3),
        "worst_ms": round(max(values), 3),
        "over_frame_budget": sum(v > budget for v in values),
        "stalls_over_50ms": sum(v > 50 for v in values),
    }


def analyze_frames(path: Path, target_fps: int = 30) -> dict:
    """Compute sampled frame-time distributions; do not invent missing metrics."""
    if type(target_fps) is not int or target_fps not in (30, 60):
        raise FieldLabError("target_fps must be exactly 30 or 60")
    p = _regular_file(Path(path), MAX_CSV_BYTES)
    samples: list[dict] = []
    try:
        with p.open("r", encoding="utf-8-sig", newline="") as f:
            rows = csv.DictReader(f)
            if not rows.fieldnames or "frame_ms" not in rows.fieldnames:
                raise FieldLabError("CSV must contain frame_ms header")
            if len(rows.fieldnames) > 64 or len(set(rows.fieldnames)) != len(rows.fieldnames):
                raise FieldLabError("CSV columns are duplicated or excessive")
            for index, row in enumerate(rows, 1):
                if index > MAX_FRAMES:
                    raise FieldLabError("Frame CSV exceeds row bound")
                if None in row:
                    raise FieldLabError("CSV row has more cells than its header")
                parsed: dict = {}
                for column in NUMERIC:
                    raw = row.get(column)
                    if raw is None or raw == "":
                        if column == "frame_ms":
                            raise FieldLabError("Missing frame_ms on row " + str(index))
                        continue
                    try:
                        value = float(raw)
                    except (ValueError, TypeError) as exc:
                        raise FieldLabError("Invalid " + column + " on row " + str(index)) from exc
                    if not math.isfinite(value) or not 0 <= value <= 120000:
                        raise FieldLabError("Nonfinite/out-of-range " + column + " on row " + str(index))
                    parsed[column] = value
                phase = row.get("phase") or "unspecified"
                if len(phase) > 64 or not phase.isprintable():
                    raise FieldLabError("Invalid phase label on row " + str(index))
                parsed["phase"] = phase
                samples.append(parsed)
    except UnicodeError as exc:
        raise FieldLabError("CSV is not UTF-8") from exc
    if not samples:
        raise FieldLabError("Frame CSV contains no samples")
    budget = 1000.0 / target_fps
    phases: dict[str, list[float]] = {}
    memory: dict[str, float] = {}
    metrics: dict[str, list[float]] = {}
    for sample in samples:
        phases.setdefault(sample["phase"], []).append(sample["frame_ms"])
        for key in MIN_MEMORY:
            if key in sample:
                memory[key] = min(memory.get(key, sample[key]), sample[key])
        for key in ("cpu_ms", "gpu_ms", "stream_ms", "draw_calls"):
            if key in sample:
                metrics.setdefault(key, []).append(sample[key])
    return {
        "schema_version": 1,
        "status": "sampled-telemetry-analyzed",
        "target_fps": target_fps,
        "frame_budget_ms": round(budget, 3),
        "source_rows": len(samples),
        "frame_time": _stats([s["frame_ms"] for s in samples], budget),
        "phases": {k: _stats(v, budget) for k, v in sorted(phases.items())},
        "minimum_available_kb": {k: round(v, 3) for k, v in sorted(memory.items())},
        "optional_metrics": {
            k: {"samples": len(v), "mean": round(mean(v), 3), "worst": round(max(v), 3)}
            for k, v in sorted(metrics.items())
        },
        "note": "Only sampled input data. Not a live capture, hardware proof or unmeasured FPS claim.",
    }


def _no_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for k, v in pairs:
        if k in result:
            raise FieldLabError("Duplicate JSON key: " + k)
        result[k] = v
    return result


def _relative_file(root: Path, relative: str, limit: int | None = None) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise FieldLabError("Expected a nonempty POSIX relative file path")
    raw = Path(relative)
    if raw.is_absolute() or any(part in ("..", ".") for part in relative.split("/")):
        raise FieldLabError("Unsafe path: " + relative)
    canonical_root = root.resolve()
    resolved = (canonical_root / raw).resolve()
    if not resolved.is_relative_to(canonical_root):
        raise FieldLabError("Path escapes the evidence folder")
    cursor = canonical_root
    for part in raw.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise FieldLabError("Symlinked evidence path is not accepted")
    if limit is not None:
        _regular_file(resolved, limit)
    elif not resolved.is_file():
        raise FieldLabError("Evidence file not found: " + relative)
    return resolved


def _hash_file(p: Path) -> str:
    hasher = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def audit_field_manifest(path: Path) -> dict:
    """Verify 3DSX header/hash and structured same-build evidence references.

    Even a valid manifest only establishes artifact/file integrity and what
    the operator *reports*; it cannot independently verify rendered gameplay.
    """
    p = _regular_file(Path(path), MAX_MANIFEST_BYTES)
    try:
        data = json.loads(p.read_text(encoding="utf-8"),
                          object_pairs_hook=_no_duplicate_json_keys)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise FieldLabError("Malformed UTF-8 field manifest JSON") from exc
    if not isinstance(data, dict) or type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        raise FieldLabError("Expected schema_version 1 manifest object")
    if not isinstance(data.get("target"), str) or data["target"] not in TARGETS:
        raise FieldLabError("target must be old3ds or new3ds")
    base = p.parent
    artifact = data.get("artifact")
    issues: list[str] = []
    artifact_ok = False
    actual_sha = None
    if artifact is None:
        issues.append("No native artifact supplied; source-only evidence")
    elif not isinstance(artifact, dict) or set(artifact) != {"path", "sha256"}:
        raise FieldLabError("artifact requires only path and sha256")
    else:
        expected = artifact["sha256"]
        if not isinstance(expected, str) or not SHA256_RE.fullmatch(expected):
            raise FieldLabError("artifact.sha256 must be 64 hex characters")
        if not isinstance(artifact["path"], str) or not artifact["path"].endswith(".3dsx"):
            raise FieldLabError("artifact.path must name a .3dsx file")
        binary = _relative_file(base, artifact["path"], MAX_ARTIFACT_BYTES)
        with binary.open("rb") as f:
            header = f.read(4)
        actual_sha = _hash_file(binary)
        artifact_ok = header == b"3DSX" and actual_sha == expected.lower()
        if header != b"3DSX":
            issues.append("Artifact is not a 3DSX header")
        if actual_sha != expected.lower():
            issues.append("Artifact SHA-256 does not match manifest")

    scenarios = data.get("scenarios", [])
    if not isinstance(scenarios, list) or len(scenarios) > MAX_SCENARIOS:
        raise FieldLabError("scenarios must be a bounded list")
    ids: set[str] = set()
    summaries: list[dict] = []
    for index, item in enumerate(scenarios):
        if not isinstance(item, dict) or not {"id", "result", "environment"}.issubset(item):
            raise FieldLabError("Each scenario needs id/result/environment")
        sid = item["id"]
        if not isinstance(sid, str) or not ID_RE.fullmatch(sid) or sid in ids:
            raise FieldLabError("Invalid or duplicate scenario id")
        ids.add(sid)
        result = item["result"]
        env = item["environment"]
        if (not isinstance(result, str) or result not in RESULTS or
                not isinstance(env, str) or env not in ENVIRONMENTS):
            raise FieldLabError("Unknown scenario result/environment")
        evidence_file = item.get("evidence")
        evidence_available = False
        if evidence_file is not None:
            _relative_file(base, evidence_file)
            evidence_available = True
        recorded_sha = item.get("artifact_sha256")
        if recorded_sha is not None and (
            not isinstance(recorded_sha, str) or not SHA256_RE.fullmatch(recorded_sha)
        ):
            raise FieldLabError("Invalid scenario artifact_sha256")
        same_build = (artifact_ok and isinstance(recorded_sha, str)
                      and recorded_sha.lower() == actual_sha)
        if result == "pass" and not same_build:
            issues.append(sid + ": pass claim does not match verified build")
        if result == "pass" and not evidence_available:
            issues.append(sid + ": pass claim has no evidence file")
        if env in ("emulator", "hardware") and result == "pass" and not evidence_available:
            issues.append(sid + ": missing external observation")
        summaries.append({
            "id": sid, "environment": env, "reported_result": result,
            "same_build_hash": same_build, "evidence_file_present": evidence_available,
            "observation_independently_verified": False,
        })
    completed = {
        s["id"] for s in summaries if s["reported_result"] == "pass"
        and s["same_build_hash"] and s["evidence_file_present"]
    }
    missing = [scenario for scenario in CORE_SCENARIOS if scenario not in completed]
    return {
        "schema_version": 1, "target": data["target"],
        "status": ("evidence-recorded-needs-human-review" if artifact_ok and not issues
                   else "incomplete-or-inconsistent"),
        "artifact_header_and_sha256_verified": artifact_ok,
        "actual_artifact_sha256": actual_sha,
        "recorded_scenarios": summaries,
        "core_scenarios_not_evidenced": missing,
        "issues": issues,
        "playable_verified": False,
        "note": "Header and hashes authenticate bytes only. Observations require independent emulator/hardware gameplay review.",
    }
