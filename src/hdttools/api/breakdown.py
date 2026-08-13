"""Axle-by-axle safety comparison: front axle, rear axle, tow vehicle
total, trailer axle(s), trailer total, combined rig weight.

Python port of `web/src/calc.ts`'s `breakdown()`/`verdictFor()` — this is
now the single source of truth (the frontend no longer computes this
itself), so keep the two in sync if a client-side copy is ever needed
again.
"""

from __future__ import annotations

from typing import Any


def _lb(value: Any) -> float:
    return float(value) if value is not None else 0.0


def compute_breakdown(truck: dict, trailer: dict, scale: dict) -> list[dict]:
    steer = _lb(scale.get("steer_axle_lb"))
    drive = _lb(scale.get("drive_axle_lb"))
    trailer_axle = _lb(scale.get("trailer_axle_lb"))
    gross = _lb(scale.get("gross_weight_lb"))
    truck_gvwr = _lb(truck.get("gvwr_lb"))
    trailer_gvwr = _lb(trailer.get("gvwr_lb"))
    gawr_per_axle = _lb(trailer.get("gawr_per_axle_lb"))

    raw_items = [
        ("Front Axle (Steer)", steer, _lb(truck.get("front_gawr_lb")), None),
        ("Rear Axle (Drive)", drive, _lb(truck.get("rear_gawr_lb")), None),
        (
            "Tow Vehicle Total (GVWR)",
            steer + drive,
            truck_gvwr,
            "Steer + drive axle readings vs. your truck tag's GVWR.",
        ),
        (
            "Trailer Axle(s)",
            trailer_axle,
            gawr_per_axle * 2,
            "Assumes a 2-axle trailer at the tag's per-axle rating.",
        ),
        (
            "Trailer Total (GVWR)",
            trailer_axle,
            trailer_gvwr,
            "Excludes tongue weight carried by the truck — not on either tag.",
        ),
        ("Combined Rig Weight", gross, truck_gvwr + trailer_gvwr, None),
    ]

    items = []
    for label, actual, limit, note in raw_items:
        passed = actual <= limit
        margin = round(limit - actual)
        pct = min(100, round((actual / limit) * 100)) if limit > 0 else 0
        items.append(
            {
                "label": label,
                "tone": "success" if passed else "warning",
                "badgeLabel": f"{margin:,.0f} lb to spare" if passed else f"{abs(margin):,.0f} lb over",
                "pct": pct,
                "barColor": "var(--state-success)" if passed else "var(--state-danger)",
                "actualLabel": f"{round(actual):,.0f} lb",
                "limitLabel": f"{round(limit):,.0f} lb",
                "note": note,
            }
        )
    return items


def verdict_for(items: list[dict]) -> dict:
    any_fail = any(item["tone"] == "warning" for item in items)
    if any_fail:
        return {
            "headline": "Not Safe to Tow",
            "subline": "One or more axles are over their rated limit — see the breakdown below.",
            "bandBg": "var(--state-danger)",
            "icon": "alert-triangle",
        }
    return {
        "headline": "Safe to Tow",
        "subline": "Every axle checks out under its rated limit.",
        "bandBg": "var(--state-success)",
        "icon": "check-circle-2",
    }
