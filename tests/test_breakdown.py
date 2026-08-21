"""Tests for compute_breakdown's axle-count and tongue-weight handling.

axle_count falls back to a 2-axle assumption when omitted. standalone_weight_lb
falls back to estimating total trailer weight as trailer_axle_lb /
(1 - pin_weight_pct) when omitted (a real scale reading exists), or off the
trailer's rated GVWR when no scale reading exists at all - rather than
using the axle reading unadjusted (that assumed 0% tongue weight, which
understates the real total). These tests cover all three paths plus the
exact-figure behavior when each field is provided, per NEXT_STEPS.md.

Also covers the "insufficient data" tone/verdict tiers added alongside
the web/Streamlit skip-image feature: a blank rig no longer silently
reports "Safe to Tow".
"""

from hdttools.api.breakdown import compute_breakdown, verdict_for

_TRUCK = {"gvwr_lb": 14000, "front_gawr_lb": 6000, "rear_gawr_lb": 9500}
_TRAILER = {"gvwr_lb": 12500, "gawr_per_axle_lb": 6000}
_SCALE = {
    "steer_axle_lb": 5620,
    "drive_axle_lb": 9040,
    "trailer_axle_lb": 11380,
    "gross_weight_lb": 26040,
}


def _item(items: list[dict], label: str) -> dict:
    return next(i for i in items if i["label"] == label)


def test_trailer_axle_limit_defaults_to_2_axles_when_omitted():
    items = compute_breakdown(_TRUCK, _TRAILER, _SCALE)
    axle_item = _item(items, "Trailer Axle(s)")
    assert axle_item["limitLabel"] == "12,000 lb"
    assert axle_item["note"] == "Assumes a 2-axle trailer at the tag's per-axle rating."


def test_trailer_axle_limit_uses_custom_axle_count():
    trailer = {**_TRAILER, "axle_count": 3}
    items = compute_breakdown(_TRUCK, trailer, _SCALE)
    axle_item = _item(items, "Trailer Axle(s)")
    assert axle_item["limitLabel"] == "18,000 lb"
    assert axle_item["note"] == "Trailer axle rating: 3 axle(s) at the tag's per-axle rating."


def test_trailer_total_estimates_from_axle_reading_when_standalone_weight_omitted():
    # trailer_axle_lb (11,380) is assumed to be 80% of actual trailer
    # weight when no stand-alone weight was given -> 11,380 / 0.8 = 14,225
    items = compute_breakdown(_TRUCK, _TRAILER, _SCALE)
    total_item = _item(items, "Trailer Total (GVWR)")
    assert total_item["actualLabel"] == "14,225 lb"
    assert total_item["note"] == (
        "Estimated total weight — assumes the axle reading is 80% of "
        "actual trailer weight; enter your truck's stand-alone weight "
        "for an exact figure."
    )


def test_trailer_total_includes_estimated_tongue_weight_when_provided():
    # steer + drive (hitched) = 14,660; stand-alone = 13,000 -> tongue weight 1,660
    truck = {**_TRUCK, "standalone_weight_lb": 13000}
    items = compute_breakdown(truck, _TRAILER, _SCALE)
    total_item = _item(items, "Trailer Total (GVWR)")
    assert total_item["actualLabel"] == "13,040 lb"
    assert "1,660 lb tongue weight" in total_item["note"]


def test_tongue_weight_clamps_at_zero_when_standalone_exceeds_hitched_total():
    # steer + drive (hitched) = 14,660; stand-alone = 20,000 -> negative estimate clamped to 0
    truck = {**_TRUCK, "standalone_weight_lb": 20000}
    items = compute_breakdown(truck, _TRAILER, _SCALE)
    total_item = _item(items, "Trailer Total (GVWR)")
    assert total_item["actualLabel"] == "11,380 lb"
    assert "0 lb tongue weight" in total_item["note"]


def test_custom_pin_weight_pct_changes_the_trailer_axle_reading_estimate():
    # 11,380 / (1 - 0.15) = 13,388
    items = compute_breakdown(_TRUCK, _TRAILER, _SCALE, pin_weight_pct=0.15)
    total_item = _item(items, "Trailer Total (GVWR)")
    assert total_item["actualLabel"] == "13,388 lb"
    assert "85% of actual trailer weight" in total_item["note"]


def test_trailer_total_estimates_from_gvwr_when_no_scale_reading_at_all():
    # No scale ticket at all (the pre-purchase/predictive case) - nothing
    # to divide, so fall back to the trailer's rated GVWR instead of the
    # axle-reading estimate.
    items = compute_breakdown(_TRUCK, _TRAILER, {})
    total_item = _item(items, "Trailer Total (GVWR)")
    assert total_item["actualLabel"] == "12,500 lb"
    assert "no scale reading yet" in total_item["note"]


def test_blank_rig_reports_not_enough_information_not_a_false_pass():
    items = compute_breakdown({}, {}, {})
    assert all(item["tone"] == "insufficient" for item in items)
    verdict = verdict_for(items)
    assert verdict["status"] == "insufficient"
    assert verdict["headline"] == "Not Enough Information"


def test_partial_rig_mixes_real_and_insufficient_rows():
    # Truck tag + scale ticket entered (truck GVWR raised so the combined
    # total genuinely passes - a real failure would otherwise correctly
    # win over "partial", see the next test down), trailer tag skipped:
    # rows that only need truck+scale data still compute for real; every
    # row that needs trailer-tag data is flagged insufficient instead of
    # a false pass.
    truck = {**_TRUCK, "gvwr_lb": 16000}
    items = compute_breakdown(truck, {}, _SCALE)
    assert _item(items, "Front Axle (Steer)")["tone"] == "success"
    assert _item(items, "Tow Vehicle Total (GVWR)")["tone"] == "success"
    assert _item(items, "Trailer Axle(s)")["tone"] == "insufficient"  # no trailer GAWR
    assert _item(items, "Trailer Total (GVWR)")["tone"] == "insufficient"  # no trailer GVWR
    assert _item(items, "Combined Rig Weight")["tone"] == "insufficient"  # no trailer GVWR
    verdict = verdict_for(items)
    assert verdict["status"] == "partial"
    assert verdict["headline"] == "Partially Checked"


def test_all_missing_scale_data_is_partial_not_insufficient_when_tags_exist():
    # Truck + trailer tags both entered, but no scale ticket at all: 5 of
    # 6 rows have no real "actual" reading and are insufficient, but
    # "Trailer Total (GVWR)" can still trivially self-compare against the
    # trailer's own rated GVWR in the no-scale-data estimate branch - so
    # this is "partial," not "insufficient" (verified behavior, not just
    # assumed - the trailer's GVWR fallback always produces a comparable
    # number once a trailer tag exists, even with zero scale data).
    items = compute_breakdown(_TRUCK, _TRAILER, {})
    assert _item(items, "Trailer Total (GVWR)")["tone"] == "success"
    assert _item(items, "Front Axle (Steer)")["tone"] == "insufficient"
    verdict = verdict_for(items)
    assert verdict["status"] == "partial"


def test_a_real_failure_always_wins_over_insufficient_rows():
    # Truck massively over its GVWR, trailer/scale both blank - a real
    # failure must never be hidden behind other rows being insufficient.
    truck = {"gvwr_lb": 1000, "front_gawr_lb": 500, "rear_gawr_lb": 500}
    scale = {"steer_axle_lb": 5620, "drive_axle_lb": 9040}
    items = compute_breakdown(truck, {}, scale)
    verdict = verdict_for(items)
    assert verdict["status"] == "fail"
    assert verdict["headline"] == "Not Safe to Tow"


def test_truck_total_estimates_from_standalone_weight_when_no_hitched_reading():
    # Pure pre-purchase case: a tow-vehicle-alone reading exists, but no
    # hitched combined scale reading (no rig to hitch yet). Previously
    # "Tow Vehicle Total (GVWR)" stayed "Not enough info" forever here -
    # this is the fix that actually answers "can I tow this" pre-purchase.
    # No scale data at all -> trailer total falls to the GVWR-fallback
    # estimate (12,500) -> tongue weight estimate = 12,500 * 0.20 = 2,500.
    truck = {**_TRUCK, "standalone_weight_lb": 6000}
    items = compute_breakdown(truck, _TRAILER, {})
    truck_item = _item(items, "Tow Vehicle Total (GVWR)")
    assert truck_item["tone"] == "success"
    assert truck_item["actualLabel"] == "8,500 lb"
    assert truck_item["badgeLabel"] == "5,500 lb to spare"
    assert truck_item["estimated"] is True
    assert "2,500 lb tongue weight" in truck_item["note"]
    assert "20% of the trailer's estimated total" in truck_item["note"]


def test_truck_and_trailer_totals_both_estimate_when_only_a_trailer_axle_reading_exists():
    # A real trailer-axle scale reading exists (weighed the trailer alone)
    # and a real tow-vehicle-alone reading exists, but the two were never
    # weighed hitched together. Regression test for the bug this session
    # fixed: the old code gated tongue-weight math on `if standalone_weight`
    # alone, so this exact scenario silently zeroed tongue weight instead
    # of falling back to the axle-based estimate (11,380 unadjusted instead
    # of the correct 14,225 estimate).
    truck = {**_TRUCK, "standalone_weight_lb": 10000}
    scale = {"trailer_axle_lb": 11380}
    items = compute_breakdown(truck, _TRAILER, scale)

    trailer_item = _item(items, "Trailer Total (GVWR)")
    assert trailer_item["actualLabel"] == "14,225 lb"  # not 11,380 - the bug's symptom
    assert trailer_item["estimated"] is True

    truck_item = _item(items, "Tow Vehicle Total (GVWR)")
    assert truck_item["actualLabel"] == "12,845 lb"  # 10,000 + (14,225 * 0.20)
    assert truck_item["estimated"] is True


def test_tow_vehicle_total_stays_insufficient_with_neither_hitched_nor_standalone_reading():
    items = compute_breakdown(_TRUCK, _TRAILER, {})
    truck_item = _item(items, "Tow Vehicle Total (GVWR)")
    assert truck_item["tone"] == "insufficient"
    assert truck_item["estimated"] is False


def test_estimated_flag_is_false_for_a_real_hitched_reading_even_when_trailer_side_estimates():
    items = compute_breakdown(_TRUCK, _TRAILER, _SCALE)
    assert _item(items, "Tow Vehicle Total (GVWR)")["estimated"] is False
    assert _item(items, "Trailer Total (GVWR)")["estimated"] is True


def test_estimated_flag_is_always_false_on_insufficient_rows():
    # A row can internally take an "estimate" branch (e.g. Trailer Total's
    # GVWR-fallback) while still being flagged insufficient for an
    # unrelated reason (no trailer GVWR at all) - estimated must not leak
    # true in that case, since there's no real number being shown.
    items = compute_breakdown({}, {}, {})
    assert all(item["estimated"] is False for item in items)


def test_standalone_weight_of_zero_is_treated_as_not_provided():
    # A truck can't really weigh 0 lb - an explicit 0 here means "not
    # entered," the same as the field being absent entirely. Regression
    # test: have_standalone briefly became a plain `is not None` check
    # earlier this session (alongside the have_hitched/have_standalone
    # decoupling fix), which let a literal 0 through as "real data" and
    # produced a nonsensical tongue-weight estimate - caught while porting
    # this exact logic to Kotlin, where the equivalent truthiness-parity
    # test already existed and failed against it.
    truck = {**_TRUCK, "standalone_weight_lb": 0}
    items = compute_breakdown(truck, _TRAILER, _SCALE)
    total_item = _item(items, "Trailer Total (GVWR)")
    # Falls back to the axle-based estimate (11,380 / 0.8 = 14,225), not
    # the exact-tongue-weight branch (which would wrongly use the full
    # steer+drive reading as "tongue weight").
    assert total_item["actualLabel"] == "14,225 lb"


def test_verdict_status_is_never_derived_from_headline_text():
    # Regression test: main.py/streamlit_app both used to derive a
    # simplified pass/fail string via `"fail" if headline.startswith
    # ("Not") else "pass"` - "Not Enough Information" also starts with
    # "Not", which would misclassify insufficient data as a real failure.
    # verdict_for must return an explicit status instead.
    blank_verdict = verdict_for(compute_breakdown({}, {}, {}))
    assert blank_verdict["headline"].startswith("Not")
    assert blank_verdict["status"] == "insufficient"
