"""Runs compute_breakdown/verdict_for against the shared golden vectors in
test-vectors/breakdown_cases.json - the same cases the Kotlin port
(android/.../domain/BreakdownGoldenVectorTest.kt) checks itself against.
The fixture is the source of truth (ADR-0007), so every case here runs for real and must
pass. A case whose "requires" names a capability this runner doesn't know fails
loudly rather than being skipped - all three runners (this one, Kotlin, TypeScript)
share that rule, so a new capability can never be silently ignored.

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

pytestmark = [pytest.mark.core]

_VECTORS_PATH = Path(__file__).resolve().parent.parent / "test-vectors" / "breakdown_cases.json"
_CASES = json.loads(_VECTORS_PATH.read_text(encoding="utf-8"))["cases"]

# Python is the reference implementation, so it supports every capability the
# fixture has today. A case needing anything else must fail until it is added here.
_SUPPORTED_CAPABILITIES = {
    "insufficient_tone",
    "gvwr_fallback_trailer_estimate",
    "adjustable_pin_weight_pct",
    "predictive_truck_estimate",
}


def _unsupported(case: dict) -> set[str]:
    return set(case["requires"]) - _SUPPORTED_CAPABILITIES


def _parse_lb(label: str) -> int:
    # "8,500 lb" -> 8500. Python's items only expose pre-formatted display
    # strings, never raw numbers - this recovers the number for comparison
    # against the golden vectors' actual_lb/limit_lb, without re-deriving
    # the formatting itself (that's what test_breakdown.py's own string
    # assertions already cover).
    match = re.match(r"([\d,]+) lb", label)
    assert match, f"unexpected label format: {label!r}"
    return int(match.group(1).replace(",", ""))


# Rows Android words differently on purpose (see Breakdown.kt); only these may carry "note_android".
_ANDROID_NOTE_ROWS = {"Tow Vehicle Total (GVWR)", "Combined Rig Weight"}


@pytest.mark.parametrize("case", _CASES, ids=[c["name"] for c in _CASES])
def test_golden_vector(case: dict):
    _check_case(case)


def _check_case(case: dict):
    unknown = _unsupported(case)
    assert not unknown, f"{case['name']}: unknown capability {sorted(unknown)} - add it to the runner or fix the fixture"

    items = compute_breakdown(case["truck"], case["trailer"], case["scale"], case["pin_weight_pct"])
    verdict = verdict_for(items)

    assert verdict["status"] == case["expected"]["verdict_status"]
    assert verdict["headline"] == case["expected"]["headline"], f"{case['name']}: headline"
    assert verdict["subline"] == case["expected"]["subline"], f"{case['name']}: subline"

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
        assert actual_item["badgeLabel"] == expected_item["badge"], f"{case['name']}/{label}: badge"
        assert actual_item["note"] == expected_item["note"], f"{case['name']}/{label}: note"


def test_every_breakdown_row_has_an_over_limit_case():
    over_limit_rows = {
        item["label"]
        for case in _CASES
        for item in case["expected"]["items"]
        if item["tone"] == "warning"
    }
    all_rows = {item["label"] for item in compute_breakdown({}, {}, {}, 0.20)}
    assert all_rows - over_limit_rows == set()


def test_unknown_capability_fails_instead_of_skipping():
    assert _unsupported({"requires": ["no_such_capability"]}) == {"no_such_capability"}
    assert _unsupported({"requires": ["insufficient_tone"]}) == set()


def test_a_fixture_case_with_an_unknown_capability_fails_the_run():
    bad_case = {**_CASES[0], "requires": ["no_such_capability"]}
    with pytest.raises(AssertionError, match="unknown capability"):
        _check_case(bad_case)


def test_note_android_only_appears_on_the_rows_android_words_differently():
    stray = {
        f"{case['name']}/{item['label']}"
        for case in _CASES
        for item in case["expected"]["items"]
        if "note_android" in item and item["label"] not in _ANDROID_NOTE_ROWS
    }
    assert stray == set()
