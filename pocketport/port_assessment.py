"""Evidence-based source compatibility and controller coverage assessment."""
from __future__ import annotations
import json
from pathlib import Path
from .source_audit import inspect_source_project
from .source_port import inspect_source

CLASSES = {
 "graphics":("new-adapter","Implement or verify a Citro3D/Citro2D backend"),
 "audio":("new-adapter","Adapt sound and music to a native verified DSP backend"),
 "input":("existing-adapter","Map original actions to normalized controls with Old 3DS fallback"),
 "filesystem":("game-specific","Adapt save paths and RomFS/SD resource locations"),
 "threading":("requires-investigation","Audit thread scheduling and memory semantics"),
 "platform":("new-adapter","Isolate platform-specific headers and system APIs"),
 "portability":("requires-investigation","Review alignment, ISA and pointer-width assumptions"),
}
ACTIONS={"move","look","jump","attack","interact","pause","inventory","map",
         "save","load","confirm","back","crouch","sprint","use","reload","dialogue","menu"}
COMMON={"a","b","x","y","start","select","l","r","dpad_up","dpad_down",
        "dpad_left","dpad_right","circle_up","circle_down","circle_left","circle_right"}
NEW={"zl","zr","cstick_up","cstick_down","cstick_left","cstick_right"}

class AssessmentError(ValueError):
    pass

def control_coverage(info: dict, target: str) -> dict:
    if (not isinstance(info,dict) or set(info)!={"schema_version","required","bindings"}
        or type(info["schema_version"]) is not int or info["schema_version"]!=1):
        raise AssessmentError("Expected controls schema v1 with required and bindings")
    required=info["required"]; bindings=info["bindings"]
    if (not isinstance(required,list) or not 1<=len(required)<=32 or
        not all(isinstance(x,str) and x in ACTIONS for x in required) or
        len(set(required))!=len(required) or not isinstance(bindings,dict) or
        len(bindings)>32 or not set(bindings).issubset(ACTIONS)):
        raise AssessmentError("Invalid required actions or action map")
    missing=[]; inaccessible=[]; touch_only=[]
    for action in required:
        options=bindings.get(action,[])
        if (not isinstance(options,list) or len(options)>4 or
            any(not isinstance(b,str) or b not in COMMON|NEW|{"touch"} for b in options)):
            raise AssessmentError("Unsupported binding for "+action)
        physical=[b for b in options if b in COMMON]
        if not options or (action in ("pause","confirm","back") and not physical):
            missing.append(action)
        if target=="old3ds" and not physical and any(b in NEW for b in options):
            inaccessible.append(action)
        if "touch" in options and not physical:
            touch_only.append(action)
    return {"schema_version":1,"target":target,"status":"complete" if not(missing or inaccessible or touch_only) else "incomplete",
            "required_actions":required,"missing":missing,"new3ds_only_on_old":inaccessible,
            "touch_only":touch_only,
            "note":"Static mapping coverage; real gameplay context and menu reachability untested"}

def load_controls(path: Path) -> dict:
    path=Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size>16000:
        raise AssessmentError("Missing, symlinked or oversized controls JSON")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError,json.JSONDecodeError) as exc:
        raise AssessmentError("Invalid controls JSON") from exc

def assess_project(root: Path, target: str="new3ds", controls: dict|None=None) -> dict:
    if target not in ("old3ds","new3ds"):
        raise AssessmentError("Unsupported target")
    source=inspect_source(root)
    audit=inspect_source_project(Path(root),target=target)
    issues=[]
    for f in audit["findings"]:
        classification,action=CLASSES.get(f["subsystem"],("requires-investigation","Review source and build dependencies"))
        issues.append({"path":f["path"],"line":f["line"],"symbol":f["symbol"],
                       "subsystem":f["subsystem"],"classification":classification,
                       "evidence":f["evidence"],"action":action,
                       "verification":"Host comparison, actual devkitARM build, emulator/hardware behavior"})
    controls_result=(control_coverage(controls,target) if controls is not None else
                     {"status":"unknown","note":"No independently verified required-action list was supplied"})
    return {"schema_version":1,"target":target,"source_root":source["source_root"],
            "languages":source["languages"],"build_systems":source["build_systems"],
            "entrypoint_candidates":source["entrypoint_candidates"],
            "file_count":source["files"]["file_count"],
            "license_evidence":source["license"],"audited_api_count":len(issues),
            "issues":issues,"findings_truncated":audit["findings_truncated"],
            "controller_coverage":controls_result,
            "available_components":["portable UI C state machine","native Citro2D dual-screen adapter",
                                    "isolated source port copier","bounded asset optimization"],
            "engineering_tasks":[{"file":x["path"],"symbol":x["symbol"],
                                  "change":x["action"],"classification":x["classification"]}
                                 for x in issues if x["classification"]!="requires-investigation"],
            "verification":{"source_inspected":True,"source_adapted":False,"native_build":False,
                            "gameplay":False,"emulator":False},
            "next":["Review license and exact source revision","Import with pocketport port",
                    "Review patch, source game logic and unresolved system APIs",
                    "Cross-compile using trusted native build route",
                    "Test title, controls, objectives, level progression and saves"]}
