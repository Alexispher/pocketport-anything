"""Bounded optional public GitHub repository metadata search (read-only)."""
from __future__ import annotations
import json
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.github.com/search/repositories"

def search_repositories(game: str, *, limit: int = 5, timeout: float = 8.0) -> dict:
    """Search hits are candidate source repositories, NOT playable 3DS ports."""
    game = " ".join(game.split())
    if not game or len(game) > 160 or any(ord(c) < 32 for c in game):
        raise ValueError("Expected a nonblank title under 160 characters")
    if not 1 <= limit <= 10:
        raise ValueError("Limit must be 1..10")
    if not 0 < timeout <= 30:
        raise ValueError("Timeout must be within 0..30 seconds")
    query = urllib.parse.urlencode({"q": f"{game} Nintendo 3DS port", "per_page": limit})
    request = urllib.request.Request(f"{API}?{query}", headers={
        "Accept": "application/vnd.github+json", "User-Agent": "PocketPortAnything/0.3"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.load(response)
    except (OSError, urllib.error.URLError, ValueError) as exc:
        return {"game": game, "status": "search-unavailable",
                "candidates": [], "error": str(exc)}
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        return {"game": game, "status": "invalid-response", "candidates": []}
    candidates = []
    for item in data["items"][:limit]:
        if not isinstance(item, dict):
            continue
        url = item.get("html_url", "")
        if not isinstance(url, str) or not url.startswith("https://github.com/"):
            continue
        license_data = item.get("license") or {}
        candidates.append({"repository": item.get("full_name", ""), "url": url,
                           "description": item.get("description") or "",
                           "archived": bool(item.get("archived")),
                           "license": (license_data.get("spdx_id", "unknown")
                                       if isinstance(license_data, dict) else "unknown"),
                           "status": "search-hit only; not buildable or gameplay-validated"})
    return {"game": game, "status": "search-completed", "candidates": candidates,
            "scope": "Public metadata; inspect branches, source, licenses and testing separately."}
