"""Axle-by-axle safety comparison: front axle, rear axle, tow vehicle
total, trailer axle(s), trailer total, combined rig weight.

Python port of `web/src/calc.ts`'s `breakdown()`/`verdictFor()` — this is
now the single source of truth (the frontend no longer computes this
itself), so keep the two in sync if a client-side copy is ever needed
again.
"""

from __future__ import annotations

from typing import Any

# Pin/tongue weight is commonly ~15-25% of trailer weight, so a trailer's
# axle reading alone is assumed to be ~80% of its actual total weight
# when no stand-alone truck weight was given to compute an exact figure.
DEFAULT_AXLE_TO_TOTAL_RATIO = 0.8


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

    axle_count_raw = trailer.get("axle_count")
    axle_count = int(axle_count_raw) if axle_count_raw else 2
    trailer_axle_note = (
        f"Trailer axle rating: {axle_count} axle(s) at the tag's per-axle rating."
        if axle_count_raw
        else "Assumes a 2-axle trailer at the tag's per-axle rating."
    )

    standalone_weight = truck.get("standalone_weight_lb")
    if standalone_weight:
        tongue_weight = max(0.0, (steer + drive) - _lb(standalone_weight))
        trailer_total_actual = trailer_axle + tongue_weight
        trailer_total_note = (
            f"Includes an estimated {round(tongue_weight):,.0f} lb tongue weight "
            "(steer + drive minus your truck's stand-alone weight)."
        )
    else:
        trailer_total_actual = trailer_axle / DEFAULT_AXLE_TO_TOTAL_RATIO
        trailer_total_note = (
            "Estimated total weight — assumes the axle reading is "
            f"{DEFAULT_AXLE_TO_TOTAL_RATIO:.0%} of actual trailer weight; "
            "enter your truck's stand-alone weight for an exact figure."
        )

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
            gawr_per_axle * axle_count,
            trailer_axle_note,
        ),
        (
            "Trailer Total (GVWR)",
            trailer_total_actual,
            trailer_gvwr,
            trailer_total_note,
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
