"""Axle-by-axle safety comparison: front axle, rear axle, tow vehicle
total, trailer axle(s), trailer total, combined rig weight.

Python port of `web/src/calc.ts`'s `breakdown()`/`verdictFor()` — this is
now the single source of truth (the frontend no longer computes this
itself), so keep the two in sync if a client-side copy is ever needed
again.
"""

from __future__ import annotations

from typing import Any

# Pin/tongue weight is commonly ~15-25% of trailer weight. Used two ways,
# both in compute_breakdown below: as a fraction of a REAL trailer-axle
# scale reading (the reading is assumed to be (1 - pin_weight_pct) of the
# trailer's actual total weight) when a scale reading exists, or as a
# fraction of the trailer's RATED GVWR when no scale reading exists at
# all - the pre-purchase/predictive case, where there's no real
# measurement yet to divide. Overridable per-request; this is just the
# default a caller gets if it doesn't say otherwise.
DEFAULT_PIN_WEIGHT_PCT = 0.20


def _lb(value: Any) -> float:
    return float(value) if value is not None else 0.0


def compute_breakdown(
    truck: dict,
    trailer: dict,
    scale: dict,
    pin_weight_pct: float = DEFAULT_PIN_WEIGHT_PCT,
) -> list[dict]:
    steer_raw = scale.get("steer_axle_lb")
    drive_raw = scale.get("drive_axle_lb")
    trailer_axle_raw = scale.get("trailer_axle_lb")
    gross_raw = scale.get("gross_weight_lb")
    truck_gvwr_raw = truck.get("gvwr_lb")
    trailer_gvwr_raw = trailer.get("gvwr_lb")
    front_gawr_raw = truck.get("front_gawr_lb")
    rear_gawr_raw = truck.get("rear_gawr_lb")
    gawr_per_axle_raw = trailer.get("gawr_per_axle_lb")

    steer = _lb(steer_raw)
    drive = _lb(drive_raw)
    trailer_axle = _lb(trailer_axle_raw)
    gross = _lb(gross_raw)
    truck_gvwr = _lb(truck_gvwr_raw)
    trailer_gvwr = _lb(trailer_gvwr_raw)
    gawr_per_axle = _lb(gawr_per_axle_raw)

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
    elif trailer_axle_raw:
        trailer_total_actual = trailer_axle / (1 - pin_weight_pct)
        trailer_total_note = (
            "Estimated total weight — assumes the axle reading is "
            f"{1 - pin_weight_pct:.0%} of actual trailer weight; "
            "enter your truck's stand-alone weight for an exact figure."
        )
    else:
        # No scale reading at all - nothing to divide, so estimate off the
        # trailer's rated GVWR instead. This is the branch that makes a
        # pre-purchase "can I tow this" check possible before a real scale
        # ticket exists.
        trailer_total_actual = trailer_gvwr
        trailer_total_note = (
            "Estimated total weight — no scale reading yet, so this assumes "
            "the trailer is loaded to its rated GVWR; weigh it for a real figure."
        )

    # Each row's own "do we actually have enough data to check this"
    # flag - checked from the specific source fields it depends on, not
    # inferred from whether actual/limit happen to be 0 (a real 0 lb
    # reading and a never-entered field are otherwise indistinguishable).
    raw_items = [
        (
            "Front Axle (Steer)",
            steer,
            _lb(front_gawr_raw),
            None,
            steer_raw is None or front_gawr_raw is None,
        ),
        (
            "Rear Axle (Drive)",
            drive,
            _lb(rear_gawr_raw),
            None,
            drive_raw is None or rear_gawr_raw is None,
        ),
        (
            "Tow Vehicle Total (GVWR)",
            steer + drive,
            truck_gvwr,
            "Steer + drive axle readings vs. your truck tag's GVWR.",
            steer_raw is None or drive_raw is None or truck_gvwr_raw is None,
        ),
        (
            "Trailer Axle(s)",
            trailer_axle,
            gawr_per_axle * axle_count,
            trailer_axle_note,
            trailer_axle_raw is None or gawr_per_axle_raw is None,
        ),
        (
            "Trailer Total (GVWR)",
            trailer_total_actual,
            trailer_gvwr,
            trailer_total_note,
            trailer_gvwr_raw is None,
        ),
        (
            "Combined Rig Weight",
            gross,
            truck_gvwr + trailer_gvwr,
            None,
            gross_raw is None or truck_gvwr_raw is None or trailer_gvwr_raw is None,
        ),
    ]

    items = []
    for label, actual, limit, note, insufficient in raw_items:
        if insufficient:
            items.append(
                {
                    "label": label,
                    "tone": "insufficient",
                    "badgeLabel": "Not enough info",
                    "pct": 0,
                    "barColor": "var(--state-info)",
                    "actualLabel": f"{round(actual):,.0f} lb",
                    "limitLabel": f"{round(limit):,.0f} lb",
                    "note": note,
                }
            )
            continue

        passed = actual <= limit
        margin = round(limit - actual)
        pct = min(100, round((actual / limit) * 100))
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
    tones = [item["tone"] for item in items]
    any_fail = "warning" in tones
    all_insufficient = all(tone == "insufficient" for tone in tones)
    any_insufficient = "insufficient" in tones

    # A real failure always wins, even if other rows are insufficient -
    # never let missing data hide a genuine over-limit reading.
    if any_fail:
        return {
            "status": "fail",
            "headline": "Not Safe to Tow",
            "subline": "One or more axles are over their rated limit — see the breakdown below.",
            "bandBg": "var(--state-danger)",
            "icon": "alert-triangle",
        }
    if all_insufficient:
        return {
            "status": "insufficient",
            "headline": "Not Enough Information",
            "subline": "Add at least a truck tag, trailer tag, or scale ticket to check anything.",
            "bandBg": "var(--state-info)",
            "icon": "help-circle",
        }
    if any_insufficient:
        return {
            "status": "partial",
            "headline": "Partially Checked",
            "subline": "Some axles couldn't be checked yet — add more data for a complete picture.",
            "bandBg": "var(--state-info)",
            "icon": "help-circle",
        }
    return {
        "status": "pass",
        "headline": "Safe to Tow",
        "subline": "Every axle checks out under its rated limit.",
        "bandBg": "var(--state-success)",
        "icon": "check-circle-2",
    }
