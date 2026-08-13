"""Tests for compute_breakdown's axle-count and tongue-weight handling.

Both fields are optional and fall back to the original (pre-fix)
behavior when omitted — these tests cover that fallback plus the new
behavior when each field is provided, per the approved plan in
NEXT_STEPS.md.
"""

from hdttools.api.breakdown import compute_breakdown

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


def test_trailer_total_excludes_tongue_weight_when_standalone_weight_omitted():
    items = compute_breakdown(_TRUCK, _TRAILER, _SCALE)
    total_item = _item(items, "Trailer Total (GVWR)")
    assert total_item["actualLabel"] == "11,380 lb"
    assert total_item["note"] == "Excludes tongue weight carried by the truck — not on either tag."


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
