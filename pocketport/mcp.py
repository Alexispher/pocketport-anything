"""Read-only PocketPort stdio MCP server with workspace-confined file tools."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from .aaa import compatibility, detect_engine, inspect_executable, research_game
from .nup import inspect_nup
from .screens import load_profile, assess_profile
from .source_port import inspect_source

TOOLS = {
    "detect_engine": {"path": {"type": "string"}},
    "inspect_executable": {"path": {"type": "string"}},
    "inspect_nup": {"path": {"type": "string"}},
    "compatibility": {"path": {"type": "string"}},
    "research": {"game": {"type": "string"}},
    "display_assessment": {"path": {"type": "string"}},
    "inspect_source": {"path": {"type": "string"}},
}

def safe_path(workspace: Path, supplied: str) -> Path:
    root = Path(workspace).resolve(strict=True)
    if not root.is_dir() or not supplied:
        raise ValueError("Authorized workspace and path required")
    candidate = root / supplied
    relative = candidate.absolute().relative_to(root)
    cursor = root
    for name in relative.parts:
        if name in (".", ".."):
            raise ValueError("Parent traversal forbidden")
        cursor = cursor / name
        if cursor.is_symlink():
            raise ValueError("Symbolic links forbidden")
    result = candidate.resolve(strict=True)
    if result != root and root not in result.parents:
        raise ValueError("Path leaves authorized workspace")
    return result

def handle(message: dict, workspace: Path) -> dict | None:
    if "id" not in message:
        return None
    mid = message["id"]
    try:
        method = message.get("method")
        if method == "initialize":
            return {"jsonrpc": "2.0", "id": mid, "result": {
                "protocolVersion": "2025-06-18", "capabilities": {"tools": {}},
                "serverInfo": {"name": "pocketport-readonly", "version": "0.3.2"}}}
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": mid, "result": {"tools": [
                {"name": name, "description": "Read-only, unverified game triage",
                 "inputSchema": {"type": "object", "properties": props,
                                 "required": list(props), "additionalProperties": False}}
                for name, props in TOOLS.items()]}}
        if method != "tools/call":
            raise ValueError("Unknown MCP method")
        params = message.get("params") or {}
        name = params.get("name")
        args = params.get("arguments") or {}
        if name not in TOOLS or not isinstance(args, dict):
            raise ValueError("Unknown tool or invalid arguments")
        if set(args) != set(TOOLS[name]):
            raise ValueError("Expected exactly the declared input parameters")
        if name == "research":
            data = research_game(args["game"])
        elif name == "display_assessment":
            data = assess_profile(load_profile(safe_path(workspace, args["path"])))
        elif name == "inspect_source":
            data = inspect_source(safe_path(workspace, args["path"]))
        else:
            path = safe_path(workspace, args["path"])
            data = {"detect_engine": detect_engine,
                    "inspect_executable": inspect_executable,
                    "inspect_nup": inspect_nup,
                    "compatibility": compatibility}[name](path)
        return {"jsonrpc": "2.0", "id": mid, "result": {
            "content": [{"type": "text", "text": json.dumps(data, sort_keys=True)}],
            "isError": False}}
    except (OSError, KeyError, TypeError, ValueError) as exc:
        return {"jsonrpc": "2.0", "id": mid, "result": {
            "content": [{"type": "text", "text": str(exc)}],
            "isError": True}}

def main() -> None:
    p = argparse.ArgumentParser(description="Read-only PocketPort stdio MCP")
    p.add_argument("--workspace", required=True, type=Path)
    args = p.parse_args()
    root = args.workspace.resolve(strict=True)
    if not root.is_dir():
        p.error("Workspace must be a directory")
    for line in sys.stdin:
        try:
            message = json.loads(line)
            reply = handle(message, root)
        except (TypeError, ValueError) as exc:
            reply = {"jsonrpc": "2.0", "id": None, "error": {
                "code": -32700, "message": str(exc)}}
        if reply is not None:
            print(json.dumps(reply, sort_keys=True), flush=True)

if __name__ == "__main__":
    main()
