"""Runs compute_breakdown/verdict_for against the shared golden vectors in
test-vectors/breakdown_cases.json - the same cases the Kotlin port
(android/.../domain/BreakdownGoldenVectorTest.kt) checks itself against.
Python is the source of truth, so every case here runs for real and must
pass; Kotlin's own runner skips whatever capabilities its current port
doesn't have yet (see the JSON file's _readme and each case's "requires").

This does not replace tests/test_breakdown.py - that file's hand-written,
one-scenario-per-test style stays the readable primary regression suite.
This file exists specifically to keep Python and Kotlin from silently
drifting apart, per TESTING.md's cross-platform section.
"""

import json
import re
from pathlib import Path

import pytest

from hdttools.api.breakdown import compute_breakdown, verdict_for

_VECTORS_PATH = Path(__file__).resolve().parent.parent / "test-vectors" / "breakdown_cases.json"
_CASES = json.loads(_VECTORS_PATH.read_text(encoding="utf-8"))["cases"]


def _parse_lb(label: str) -> int:
    # "8,500 lb" -> 8500. Python's items only expose pre-formatted display
    # strings, never raw numbers - this recovers the number for comparison
    # against the golden vectors' actual_lb/limit_lb, without re-deriving
    # the formatting itself (that's what test_breakdown.py's own string
    # assertions already cover).
    match = re.match(r"([\d,]+) lb", label)
    assert match, f"unexpected label format: {label!r}"
    return int(match.group(1).replace(",", ""))


@pytest.mark.parametrize("case", _CASES, ids=[c["name"] for c in _CASES])
def test_golden_vector(case: dict):
    items = compute_breakdown(case["truck"], case["trailer"], case["scale"], case["pin_weight_pct"])
    verdict = verdict_for(items)

    assert verdict["status"] == case["expected"]["verdict_status"]

    by_label = {item["label"]: item for item in items}
    for expected_item in case["expected"]["items"]:
        label = expected_item["label"]
        assert label in by_label, f"{case['name']}: missing row {label!r}"
        actual_item = by_label[label]
        assert actual_item["tone"] == expected_item["tone"], f"{case['name']}/{label}: tone"
        assert _parse_lb(actual_item["actualLabel"]) == expected_item["actual_lb"], (
            f"{case['name']}/{label}: actual_lb"
        )
        assert _parse_lb(actual_item["limitLabel"]) == expected_item["limit_lb"], (
            f"{case['name']}/{label}: limit_lb"
        )
        assert actual_item["pct"] == expected_item["pct"], f"{case['name']}/{label}: pct"
        assert actual_item["estimated"] == expected_item["estimated"], f"{case['name']}/{label}: estimated"
