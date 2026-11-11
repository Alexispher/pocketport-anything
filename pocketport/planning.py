"""Evidence-gated port route planner; no unsupported automated game identification."""
from __future__ import annotations

ROUTES = (
    ("existing-3ds-version", "existing_3ds_version", "A", "Adapt an existing licensed 3DS release via authorized mods."),
    ("existing-3ds-port", "existing_3ds_port", "B", "Extend an established and license-compatible homebrew port."),
    ("source-port", "source_available", "C", "Port available, licensed source to the devkitARM runtime."),
    ("decompilation-port", "decomp_available", "D", "Use a complete-enough lawful reconstruction with verified provenance."),
    ("runtime-rehost", "runtime_available", "E", "Reuse a tested compatible engine or bytecode interpreter on the 3DS."),
    ("static-recompilation", "static_recomp_supported", "E", "Use a verified supported ISA/ABI binary translator plus runtime."),
    ("engine-reimplementation", "engine_reimplementation_feasible", "F", "Reimplement needed behavior using verified reference tests."),
    ("demake", "demake_feasible", "G", "Preserve key gameplay and presentation in a smaller original implementation."),
)


def choose(evidence: dict, target: str) -> dict:
    if target not in ("old3ds", "new3ds"):
        raise ValueError("Target must be old3ds or new3ds")
    if evidence.get("license_ok") is False:
        return {"route": "blocked", "reason": "Permission/license evidence rejects the intended use", "target": target}
    if evidence.get("resources_ok") is False:
        return {"route": "feasibility", "reason": "Measured target resource budgets are insufficient", "target": target}
    for route, flag, letter, reason in ROUTES:
        # Boolean true must be independently evidenced by the operator, not inferred from file suffixes.
        if evidence.get(flag) is True:
            return {"route": route, "route_letter": letter, "target": target, "reason": reason,
                    "evidence_key": flag, "confidence": "operator-asserted; engineering verification required",
                    "next_action": "Verify provenance, build and real hardware constraints for this candidate"}
    return {"route": "feasibility", "target": target,
            "reason": "No supported route was substantiated by the supplied evidence; do not invent compatibility.",
            "next_action": "Collect game/build identity, license, dependencies, code availability, and hardware measurements"}
