"""Web-app persistence: saved rig profiles and completed checks.

Separate from `hdttools.database`'s CLI-facing raw extraction tables —
uploaded photos aren't kept for the web app (processed in memory and
discarded), and there's no `vehicle_name` to invent for one, so a check's
truck/trailer/scale values are stored as a snapshot rather than routed
through the CLI's per-document tables. Shares the same SQLite file
(`DEFAULT_DB_PATH`).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..database import DEFAULT_DB_PATH

_SEED_RIG = {
    "truck_name": "Big Blue (Ford F-350)",
    "trailer_name": "The Nest (Grand Design 2930RL)",
}


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path = DEFAULT_DB_PATH) -> None:
    """Create the rigs/checks tables if missing, and seed one placeholder
    rig on first run so the wizard has something to select."""
    conn = _connect(db_path)
    try:
        with conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS rigs ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "truck_name TEXT NOT NULL, trailer_name TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS checks ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "rig_id INTEGER NOT NULL, truck_name TEXT NOT NULL, "
                "trailer_name TEXT NOT NULL, date TEXT NOT NULL, "
                "verdict TEXT NOT NULL, breakdown_json TEXT NOT NULL)"
            )
            count = conn.execute("SELECT COUNT(*) AS n FROM rigs").fetchone()["n"]
            if count == 0:
                conn.execute(
                    "INSERT INTO rigs (truck_name, trailer_name) VALUES (?, ?)",
                    (_SEED_RIG["truck_name"], _SEED_RIG["trailer_name"]),
                )
    finally:
        conn.close()


def list_rigs(db_path: Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    conn = _connect(db_path)
    try:
        rows = conn.execute("SELECT id, truck_name, trailer_name FROM rigs ORDER BY id").fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_rig(rig_id: int, db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any] | None:
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT id, truck_name, trailer_name FROM rigs WHERE id = ?", (rig_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_checks(db_path: Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT id, rig_id, truck_name, trailer_name, date, verdict, breakdown_json "
            "FROM checks ORDER BY id DESC"
        ).fetchall()
        results = []
        for row in rows:
            record = dict(row)
            record["breakdown"] = json.loads(record.pop("breakdown_json"))
            results.append(record)
        return results
    finally:
        conn.close()


def save_check(
    rig_id: int,
    truck_name: str,
    trailer_name: str,
    verdict: str,
    breakdown: list[dict[str, Any]],
    db_path: Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    date = datetime.now(timezone.utc).strftime("%b %d, %Y")
    conn = _connect(db_path)
    try:
        with conn:
            cursor = conn.execute(
                "INSERT INTO checks (rig_id, truck_name, trailer_name, date, verdict, breakdown_json) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (rig_id, truck_name, trailer_name, date, verdict, json.dumps(breakdown)),
            )
        return {
            "id": cursor.lastrowid,
            "rig_id": rig_id,
            "truck_name": truck_name,
            "trailer_name": trailer_name,
            "date": date,
            "verdict": verdict,
            "breakdown": breakdown,
        }
    finally:
        conn.close()
