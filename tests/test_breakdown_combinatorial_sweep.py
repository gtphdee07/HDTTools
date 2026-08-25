"""Structured combinatorial sweep over compute_breakdown/verdict_for's
known interesting-value space - present/absent/zero/boundary combinations
of truck, trailer, and scale data, plus axle_count/pin_weight_pct
overrides. `itertools.product` over a small, deliberately-chosen set of
representative values per dimension (not `hypothesis`-driven open-ended
fuzzing - see NEXT_STEPS.md/roadmap for why: the interesting space here is
small and already enumerable from reading the code, not continuous).

This is an invariant sweep, not a golden-vector file: it doesn't assert
exact output values (tests/test_breakdown.py and
tests/test_breakdown_golden_vectors.py already do that for specific known
cases), it asserts properties that must hold for *every* combination -
never crashes, every enum field is a real member of its enum, estimated
never leaks on an insufficient row, pct stays in range. A real bug this
sweep finds gets promoted to a named case in
test-vectors/breakdown_cases.json (cross-platform with Kotlin's
BreakdownGoldenVectorTest.kt) - this file itself stays Python-only, since
it's an internal-invariant check, not a named cross-platform contract.
"""

import itertools

import pytest

from hdttools.api.breakdown import compute_breakdown, verdict_for

_VALID_TONES = {"success", "warning", "insufficient"}
_VALID_STATUSES = {"pass", "fail", "partial", "insufficient"}

# Each dimension's values are deliberately chosen to hit a specific known
# branch/edge in breakdown.py, not just "some realistic number":
TRUCK_VARIANTS = {
    "full": {"gvwr_lb": 14000, "front_gawr_lb": 6000, "rear_gawr_lb": 9500},
    "empty": {},
    "zero_gvwr": {"gvwr_lb": 0, "front_gawr_lb": 6000, "rear_gawr_lb": 9500},
    "zero_front_gawr": {"gvwr_lb": 14000, "front_gawr_lb": 0, "rear_gawr_lb": 9500},
    "zero_rear_gawr": {"gvwr_lb": 14000, "front_gawr_lb": 6000, "rear_gawr_lb": 0},
    "with_standalone": {
        "gvwr_lb": 14000,
        "front_gawr_lb": 6000,
        "rear_gawr_lb": 9500,
        "standalone_weight_lb": 13000,
    },
    "zero_standalone": {
        "gvwr_lb": 14000,
        "front_gawr_lb": 6000,
        "rear_gawr_lb": 9500,
        "standalone_weight_lb": 0,
    },
}

TRAILER_VARIANTS = {
    "full": {"gvwr_lb": 12500, "gawr_per_axle_lb": 6000},
    "empty": {},
    "zero_gvwr": {"gvwr_lb": 0, "gawr_per_axle_lb": 6000},
    "zero_gawr_per_axle": {"gvwr_lb": 12500, "gawr_per_axle_lb": 0},
    "custom_axle_count": {"gvwr_lb": 12500, "gawr_per_axle_lb": 6000, "axle_count": 3},
    "zero_axle_count": {"gvwr_lb": 12500, "gawr_per_axle_lb": 6000, "axle_count": 0},
}

SCALE_VARIANTS = {
    # steer/drive/trailer-axle chosen to land exactly on TRUCK_VARIANTS
    # "full"'s GAWRs and TRAILER_VARIANTS "full"'s per-axle rating * 2 -
    # a real 0%-over/under boundary case (actual == limit exactly) for
    # whichever combination pairs "full" with "boundary_exact".
    "boundary_exact": {
        "steer_axle_lb": 6000,
        "drive_axle_lb": 9500,
        "trailer_axle_lb": 12000,
        "gross_weight_lb": 26500,
    },
    "empty": {},
    "axle_only_no_hitched": {"trailer_axle_lb": 11380},
}

PIN_WEIGHT_PCTS = [0.20, 0.0, 1.0]


def _cases():
    cases = []
    for (truck_name, truck), (trailer_name, trailer), (scale_name, scale), pct in itertools.product(
        TRUCK_VARIANTS.items(), TRAILER_VARIANTS.items(), SCALE_VARIANTS.items(), PIN_WEIGHT_PCTS
    ):
        case_id = f"truck={truck_name},trailer={trailer_name},scale={scale_name},pct={pct}"
        cases.append(pytest.param(truck, trailer, scale, pct, id=case_id))
    return cases


@pytest.mark.parametrize("truck,trailer,scale,pin_weight_pct", _cases())
def test_combination_never_crashes_and_stays_in_valid_ranges(truck, trailer, scale, pin_weight_pct):
    items = compute_breakdown(truck, trailer, scale, pin_weight_pct=pin_weight_pct)

    for item in items:
        assert item["tone"] in _VALID_TONES, item
        assert 0 <= item["pct"] <= 100, item
        if item["tone"] == "insufficient":
            assert item["estimated"] is False, item

    verdict = verdict_for(items)
    assert verdict["status"] in _VALID_STATUSES, verdict
