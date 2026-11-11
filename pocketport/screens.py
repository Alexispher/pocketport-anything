"""Versioned Nintendo 3DS screen/input profile and evidence-gated assessment.

Configuration is declarative; it never proves a game or platform feature runs.
"""
from __future__ import annotations

import json
from pathlib import Path

TOP = (400, 240)
BOTTOM = (320, 240)
_ALLOWED_KEYS = {"dpad_left", "dpad_right", "circle_left", "circle_right",
                 "a", "b", "x", "y", "l", "r", "start", "select",
                 "dpad_up", "dpad_down"}
_PAGES = {"hud", "map", "inventory", "pause", "help"}
_ALLOWED = {
    "schema_version", "target", "source", "displays", "touch", "controls",
    "pages", "graphics", "resources", "unsupported"
}
_REQUIRED = _ALLOWED - {"unsupported"}


class ScreenProfileError(ValueError):
    pass


def _exact(obj: object, allowed: set[str], required: set[str], label: str) -> dict:
    if not isinstance(obj, dict):
        raise ScreenProfileError(f"{label} must be an object")
    extra = set(obj) - allowed
    missing = required - set(obj)
    if extra or missing:
        raise ScreenProfileError(
            f"{label} has unknown fields {sorted(extra)} or missing fields {sorted(missing)}")
    return obj


def _positive_int(value: object, name: str, max_value: int) -> int:
    if type(value) is not int or not 0 < value <= max_value:
        raise ScreenProfileError(f"{name} must be integer in 1..{max_value}")
    return value


def validate_profile(data: object) -> dict:
    p = _exact(data, _ALLOWED, _REQUIRED, "screen profile")
    if type(p["schema_version"]) is not int or p["schema_version"] != 1:
        raise ScreenProfileError("Unsupported screen profile schema_version; expected 1")
    if p["target"] not in ("old3ds", "new3ds"):
        raise ScreenProfileError("target must be old3ds or new3ds")
    source = _exact(p["source"], {"viewports", "verified", "touch_required"},
                    {"viewports", "verified", "touch_required"}, "source")
    _positive_int(source["viewports"], "source.viewports", 4)
    if type(source["verified"]) is not bool or type(source["touch_required"]) is not bool:
        raise ScreenProfileError("source.verified and touch_required must be booleans")
    displays = _exact(p["displays"], {"top", "bottom"}, {"top", "bottom"}, "displays")
    if displays["top"] not in ("gameplay", "menu", "cutscene"):
        raise ScreenProfileError("top display has invalid role")
    if displays["bottom"] not in ("hud", "map", "inventory", "help", "disabled"):
        raise ScreenProfileError("bottom display has invalid role")
    touch = _exact(p["touch"], {"mode", "physical_fallback"},
                   {"mode", "physical_fallback"}, "touch")
    if touch["mode"] not in ("disabled", "optional", "required"):
        raise ScreenProfileError("touch.mode must be disabled, optional or required")
    if type(touch["physical_fallback"]) is not bool or not touch["physical_fallback"]:
        raise ScreenProfileError("A documented physical control fallback is mandatory")
    if source["touch_required"] and touch["mode"] == "disabled":
        raise ScreenProfileError("Original game needs touch; disabled touch requires explicit redesign")
    controls = _exact(p["controls"], {"bindings"}, {"bindings"}, "controls")
    bindings = controls["bindings"]
    if not isinstance(bindings, dict) or not bindings:
        raise ScreenProfileError("controls.bindings must not be empty")
    if len(bindings) > 32:
        raise ScreenProfileError("Too many control bindings")
    for name, buttons in bindings.items():
        if not isinstance(name, str) or not 1 <= len(name) <= 32:
            raise ScreenProfileError("Control action name length invalid")
        if not isinstance(buttons, list) or not 1 <= len(buttons) <= 3:
            raise ScreenProfileError("Each binding must list 1..3 physical buttons")
        if any(b not in _ALLOWED_KEYS for b in buttons) or len(set(buttons)) != len(buttons):
            raise ScreenProfileError(f"Unsupported or repeated physical button in {name}")
    if "pause" not in bindings or "back" not in bindings:
        raise ScreenProfileError("pause and back require physical button bindings")
    pages = p["pages"]
    if not isinstance(pages, list) or len(pages) > 5 or len(pages) < 3:
        raise ScreenProfileError("pages must be an explicit array of 3..5 entries")
    if any(page not in _PAGES for page in pages) or len(set(pages)) != len(pages):
        raise ScreenProfileError("Unknown or repeated UI page")
    if not {"hud", "pause", "help"}.issubset(set(pages)):
        raise ScreenProfileError("hud/pause/help pages are mandatory")
    if displays["bottom"] in ("map", "inventory") and displays["bottom"] not in pages:
        raise ScreenProfileError("Bottom role must be included in enabled pages")
    graphics = _exact(p["graphics"], {"mode", "stereo_requested"},
                      {"mode", "stereo_requested"}, "graphics")
    if graphics["mode"] not in ("2d", "3d", "mixed") or type(graphics["stereo_requested"]) is not bool:
        raise ScreenProfileError("Unsupported graphics mode or stereo flag")
    resources = _exact(p["resources"], {"application_ram_budget_bytes", "source"},
                       {"application_ram_budget_bytes", "source"}, "resources")
    budget = resources["application_ram_budget_bytes"]
    if budget is not None:
        _positive_int(budget, "application_ram_budget_bytes", 256 * 1024 * 1024)
        if resources["source"] != "measured":
            raise ScreenProfileError("Application RAM budget needs measured evidence")
    elif resources["source"] != "unknown":
        raise ScreenProfileError("Unknown application RAM must have source='unknown'")
    unsupported = p.get("unsupported", [])
    if (not isinstance(unsupported, list) or len(unsupported) > 48
            or any(not isinstance(s, str) or not 1 <= len(s) <= 120 for s in unsupported)):
        raise ScreenProfileError("unsupported must be an array of bounded strings")
    return p


def load_profile(path: Path) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 16000:
        raise ScreenProfileError("Profile missing, symlinked or exceeds 16 KB")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ScreenProfileError("Invalid JSON/UTF-8 profile") from exc
    return validate_profile(raw)


def assess_profile(profile: dict, evidence: dict | None = None) -> dict:
    p = validate_profile(profile)
    e = evidence or {}
    _exact(e, {"source_verified", "native_build_verified", "emulator_tested"},
           set(), "evidence")
    if any(type(value) is not bool for value in e.values()):
        raise ScreenProfileError("Evidence flags must be booleans")
    flags = [*p["unsupported"]]
    if p["graphics"]["stereo_requested"]:
        flags.append("Native stereoscopic renderer not implemented or verified")
    if p["displays"]["top"] != "gameplay":
        flags.append("Example frontend currently renders gameplay on top only")
    if p["displays"]["bottom"] == "disabled":
        flags.append("Bottom UI disabled by profile; dual-screen demo needs it enabled")
    if p["source"]["viewports"] > 2:
        flags.append("Original multi-viewport composition needs game-specific adaptation")
    if p["resources"]["application_ram_budget_bytes"] is None:
        flags.append("Application RAM grant unknown; measure on actual target process")
    return {
        "schema_version": 1, "target": p["target"],
        "hardware": {"top_logical_pixels": list(TOP),
                     "bottom_logical_pixels": list(BOTTOM),
                     "upper_stereo_capable": True,
                     "application_ram_grant": p["resources"]["application_ram_budget_bytes"]},
        "source_requirements": {**p["source"],
                                "independently_verified": bool(e.get("source_verified", False))},
        "layout": p["displays"], "pages": p["pages"], "controls": p["controls"]["bindings"],
        "touch": p["touch"],
        "implemented": {
            "portable_ui_state_machine": True,
            "native_2d_dual_screen_backend_source": True,
            "existing_3d_viewer_preserved": True,
            "arbitrary_engine_port": False,
            "stereo_renderer": False,
        },
        "verified": {
            "native_build": bool(e.get("native_build_verified", False)),
            "emulator_visual": bool(e.get("emulator_tested", False))
        },
        "dependency_requirements": [
            "devkitARM", "libctru", "citro3d", "citro2d", "3dsxtool"],
        "asset_adaptations": [
            "top gameplay viewport 400x240", "bottom UI independently laid out for 320x240",
            "PICA200-specific texture/graphics conversion when needed"
        ],
        "missing_or_unsupported": flags,
        "build_commands": [
            "make -C examples/source-port",
            "python -m unittest discover -s tests -q",
        ],
        "checklist": [
            "Confirm game engine and source rights",
            "Map original viewports and action controls",
            "Select and validate a display profile",
            "Implement a game-specific top renderer",
            "Adapt lower HUD/actions and physical fallbacks",
            "Cross-compile a real .3dsx",
            "Boot in Azahar, check both displays and touch",
            "Measure memory and frame timings on target hardware",
        ]
    }


def make_header(profile: dict) -> str:
    p = validate_profile(profile)
    # Do not advertise unsupported stereo as working in a generated frontend.
    if p["graphics"]["stereo_requested"]:
        raise ScreenProfileError("Native stereo rendering not implemented; cannot generate stereo build")
    if p["displays"]["top"] != "gameplay":
        raise ScreenProfileError("Native Star Catcher frontend only implements top-screen gameplay")
    pages = p["pages"]
    pp_pages = [k.upper() for k in pages]
    roles = {"hud": "PP_PAGE_HUD", "map": "PP_PAGE_MAP", "inventory": "PP_PAGE_INVENTORY"}
    initial = roles.get(p["displays"]["bottom"], "PP_PAGE_HUD")
    return (
        "/* Generated from validated PocketPort screen profile v1. */\n"
        "#ifndef PP_DISPLAY_PROFILE_GENERATED_H\n"
        "#define PP_DISPLAY_PROFILE_GENERATED_H\n"
        f"#define PP_PROFILE_NEW3DS {1 if p['target'] == 'new3ds' else 0}\n"
        f"#define PP_PROFILE_TOUCH_ENABLED {1 if p['touch']['mode']!='disabled' else 0}\n"
        f"#define PP_PROFILE_INITIAL_PAGE {initial}\n"
        "#define PP_PROFILE_ENABLED_PAGES ("
        + " | ".join(f"PP_UI_ALLOW_{role}" for role in pp_pages) + ")\n"
        "#endif\n"
    )


def write_header(path: Path, profile: dict) -> dict:
    code = make_header(profile)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(code, encoding="utf-8")
    return {"output": str(target), "bytes": len(code.encode("utf-8")),
            "status": "C configuration generated, native build not implied"}


def main() -> None:
    import argparse
    a = argparse.ArgumentParser()
    a.add_argument("profile")
    a.add_argument("--header", required=True)
    args = a.parse_args()
    print(json.dumps(write_header(Path(args.header), load_profile(Path(args.profile)))))


if __name__ == "__main__":
    main()
