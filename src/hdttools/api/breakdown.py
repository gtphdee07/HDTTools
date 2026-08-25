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
    # `1 - pin_weight_pct` is a divisor below (axle-reading-estimate branch) -
    # exactly 1.0 crashed with ZeroDivisionError. Real bug found 2026-08-24
    # via the combinatorial sweep; reaches here unvalidated from a real
    # caller too (POST /api/breakdown's BreakdownRequest.pin_weight_pct has
    # no Pydantic range constraint). Deliberately narrow: only the exact
    # zero-divisor case is guarded - a value *above* 1.0 (e.g. a caller
    # sending "15" meaning 15% instead of the fraction 0.15) is left alone
    # on purpose, since it already fails loud with an obviously-wrong
    # negative result instead of crashing or silently looking plausible -
    # see test_breakdown_endpoint_pin_weight_pct_is_a_fraction_not_the_ui_percentage.
    if pin_weight_pct == 1.0:
        pin_weight_pct = 0.99

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

    standalone_raw = truck.get("standalone_weight_lb")
    standalone_weight = _lb(standalone_raw)
    have_hitched = steer_raw is not None and drive_raw is not None
    # Truthy, not just non-None: a truck can't really weigh 0 lb, so an
    # explicit 0 here means "not entered," the same as it being absent -
    # matching axle_count's existing truthy check just below, and the
    # Kotlin port's own documented truthiness-parity decision. Regression
    # found 2026-08-21 while porting this fix to Kotlin - a plain
    # `is not None` check (introduced earlier this session alongside the
    # have_hitched/have_standalone decoupling) let standalone_weight_lb: 0
    # through as "real data," producing a nonsensical tongue-weight result.
    have_standalone = bool(standalone_raw)

    # Trailer total: which branch fires depends only on what's known about
    # the TRAILER side of the tongue-weight math (a real hitched reading
    # plus a real stand-alone reading gives an exact figure; otherwise fall
    # back to an axle-reading estimate or, with no scale data at all, a
    # GVWR-rated estimate) - deliberately independent of whether the truck
    # side ends up using an estimate too (see truck_total_actual below).
    trailer_total_estimated = False
    if have_hitched and have_standalone:
        tongue_weight = max(0.0, (steer + drive) - standalone_weight)
        trailer_total_actual = trailer_axle + tongue_weight
        trailer_total_note = (
            f"Includes an estimated {round(tongue_weight):,.0f} lb tongue weight "
            "(steer + drive minus your truck's stand-alone weight)."
        )
    elif trailer_axle_raw is not None:
        trailer_total_actual = trailer_axle / (1 - pin_weight_pct)
        trailer_total_note = (
            "Estimated total weight — assumes the axle reading is "
            f"{1 - pin_weight_pct:.0%} of actual trailer weight; "
            "enter your truck's stand-alone weight for an exact figure."
        )
        trailer_total_estimated = True
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
        trailer_total_estimated = True

    # Truck total: a real hitched reading always wins (today's original
    # behavior). Without one, but with a real tow-vehicle-alone reading,
    # estimate the missing tongue weight off the trailer total above -
    # this is what actually answers the pre-purchase "can I tow this"
    # question, which previously stayed "Not enough info" forever since
    # only a hitched reading was ever recognized here.
    truck_total_estimated = False
    if have_hitched:
        truck_total_actual: float | None = steer + drive
        truck_total_note = "Steer + drive axle readings vs. your truck tag's GVWR."
    elif have_standalone:
        truck_tongue_weight_estimate = trailer_total_actual * pin_weight_pct
        truck_total_actual = standalone_weight + truck_tongue_weight_estimate
        truck_total_note = (
            "Estimated total weight — includes an estimated "
            f"{round(truck_tongue_weight_estimate):,.0f} lb tongue weight "
            f"({pin_weight_pct:.0%} of the trailer's estimated total); enter a "
            "real hitched scale reading for an exact figure."
        )
        truck_total_estimated = True
    else:
        truck_total_actual = None
        truck_total_note = "Steer + drive axle readings vs. your truck tag's GVWR."

    # Each row's own "do we actually have enough data to check this"
    # flag - checked from the specific source fields it depends on, not
    # inferred from whether actual/limit happen to be 0 (a real 0 lb
    # reading and a never-entered field are otherwise indistinguishable).
    # A rated limit of exactly 0 means "not entered," not "really rated for
    # zero" - no real vehicle has a 0 lb GAWR/GVWR - matching the same
    # truthy-not-just-non-None reasoning already used for
    # standalone_weight_lb/axle_count above. Real bug found 2026-08-24 via
    # the combinatorial sweep: an `is None`-only check let an explicit 0
    # rated limit through as "sufficient data," which then divided by that
    # same 0 computing `pct` below, crashing with ZeroDivisionError instead
    # of reporting "Not enough info."
    raw_items = [
        (
            "Front Axle (Steer)",
            steer,
            _lb(front_gawr_raw),
            None,
            steer_raw is None or not front_gawr_raw,
            False,
        ),
        (
            "Rear Axle (Drive)",
            drive,
            _lb(rear_gawr_raw),
            None,
            drive_raw is None or not rear_gawr_raw,
            False,
        ),
        (
            "Tow Vehicle Total (GVWR)",
            truck_total_actual if truck_total_actual is not None else 0.0,
            truck_gvwr,
            truck_total_note,
            truck_total_actual is None or not truck_gvwr_raw,
            truck_total_estimated,
        ),
        (
            "Trailer Axle(s)",
            trailer_axle,
            gawr_per_axle * axle_count,
            trailer_axle_note,
            trailer_axle_raw is None or not gawr_per_axle_raw,
            False,
        ),
        (
            "Trailer Total (GVWR)",
            trailer_total_actual,
            trailer_gvwr,
            trailer_total_note,
            not trailer_gvwr_raw,
            trailer_total_estimated,
        ),
        (
            "Combined Rig Weight",
            gross,
            truck_gvwr + trailer_gvwr,
            None,
            gross_raw is None or not truck_gvwr_raw or not trailer_gvwr_raw,
            False,
        ),
    ]

    items = []
    for label, actual, limit, note, insufficient, estimated in raw_items:
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
                    "estimated": False,
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
                "estimated": estimated,
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
