"""SQLite persistence for reviewed extraction records."""

from __future__ import annotations

import dataclasses
import sqlite3
from pathlib import Path
from typing import Any

from .models import ScaleTicketData, TrailerTagData, TruckTagData

DEFAULT_DB_PATH = Path("hdttools.db")

_SCALE_TICKET_COLUMNS = [
    "source_image", "ticket_number", "weigh_number", "date", "time",
    "scale_number", "location_name", "location_address", "city", "state",
    "steer_axle_lb", "drive_axle_lb", "trailer_axle_lb", "gross_weight_lb",
    "company", "commodity", "tractor_number", "trailer_number",
]

_TRUCK_TAG_COLUMNS = [
    "vehicle_name", "source_image", "manufacturer", "date", "vin",
    "vehicle_type", "gvwr_kg", "gvwr_lb", "front_gawr_kg", "front_gawr_lb",
    "rear_gawr_kg", "rear_gawr_lb", "standalone_weight_lb",
    "front_tire_tire", "front_tire_rim", "front_tire_cold_pressure_kpa",
    "front_tire_cold_pressure_psi", "front_tire_dual",
    "rear_tire_tire", "rear_tire_rim", "rear_tire_cold_pressure_kpa",
    "rear_tire_cold_pressure_psi", "rear_tire_dual",
]

_TRAILER_TAG_COLUMNS = [
    "vehicle_name", "source_image", "manufacturer", "date", "vin",
    "vehicle_type", "gvwr_kg", "gvwr_lb", "gawr_per_axle_kg",
    "gawr_per_axle_lb", "uvw_kg", "uvw_lb", "axle_count",
    "tire_tire", "tire_rim", "tire_cold_pressure_kpa",
    "tire_cold_pressure_psi", "tire_dual",
]


def _flatten(obj: Any) -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for f in dataclasses.fields(obj):
        value = getattr(obj, f.name)
        if dataclasses.is_dataclass(value):
            for sub_key, sub_value in _flatten(value).items():
                flat[f"{f.name}_{sub_key}"] = sub_value
        else:
            flat[f.name] = value
    return flat


def _save(table: str, columns: list[str], record: Any, db_path: Path) -> int:
    values = _flatten(record)
    col_sql = ", ".join(f'"{c}"' for c in columns)
    placeholders = ", ".join("?" for _ in columns)

    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.execute(
                f'CREATE TABLE IF NOT EXISTS "{table}" '
                f'(id INTEGER PRIMARY KEY AUTOINCREMENT, {col_sql}, '
                f'saved_at TEXT DEFAULT CURRENT_TIMESTAMP)'
            )
            cursor = conn.execute(
                f'INSERT INTO "{table}" ({col_sql}) VALUES ({placeholders})',
                [values.get(c) for c in columns],
            )
        return cursor.lastrowid
    finally:
        conn.close()


def save_scale_ticket(record: ScaleTicketData, db_path: Path = DEFAULT_DB_PATH) -> int:
    """Save a reviewed scale ticket record and return its new row id."""
    return _save("scale_tickets", _SCALE_TICKET_COLUMNS, record, db_path)


def save_truck_tag(record: TruckTagData, db_path: Path = DEFAULT_DB_PATH) -> int:
    """Save a reviewed truck tag record and return its new row id."""
    return _save("truck_tags", _TRUCK_TAG_COLUMNS, record, db_path)


def save_trailer_tag(record: TrailerTagData, db_path: Path = DEFAULT_DB_PATH) -> int:
    """Save a reviewed trailer tag record and return its new row id."""
    return _save("trailer_tags", _TRAILER_TAG_COLUMNS, record, db_path)
