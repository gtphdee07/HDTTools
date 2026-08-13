"""Local JSON persistence for the Streamlit app's last-5 recent rigs.

Mirrors `web/src/recentRigs.ts`'s localStorage-backed behavior, but as a
JSON file in the user's home directory since Streamlit has no browser
storage. Won't survive a redeploy on an ephemeral host (e.g. Streamlit
Community Cloud) - that's an accepted tradeoff for local/self-hosted use,
not something this solves.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RECENT_RIGS_PATH = Path.home() / ".rigcheck" / "recent_rigs.json"
MAX_RECENT_RIGS = 5


def load_recent_rigs() -> list[dict[str, Any]]:
    try:
        raw = RECENT_RIGS_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def save_recent_rig(nickname: str, truck: dict[str, Any], trailer: dict[str, Any]) -> list[dict[str, Any]]:
    existing = [r for r in load_recent_rigs() if r.get("nickname", "").lower() != nickname.lower()]
    updated = {
        "nickname": nickname,
        "truck": truck,
        "trailer": trailer,
        "lastUsedAt": datetime.now(timezone.utc).isoformat(),
    }
    next_rigs = [updated, *existing][:MAX_RECENT_RIGS]

    RECENT_RIGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECENT_RIGS_PATH.write_text(json.dumps(next_rigs, indent=2), encoding="utf-8")
    return next_rigs
