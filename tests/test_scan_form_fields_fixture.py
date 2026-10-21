"""Free checks on test-vectors/scan_form_fields.json and Streamlit's review form against it (#162,
under epic #147).

The fixture lists, per doc type, the fields every surface's review form shows: `scanned` (a Scan
can fill them, so each is a property of the doc type's tool in `vision_tool_schemas.json`) and
`manual_only` (shown, never returned by a Scan), each with a `text` or `number` type. Web (#163) and
Android (#164) check their own forms against the same file. No network, no Claude call."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from streamlit_app.fields import FIELDS

pytestmark = pytest.mark.core

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = json.loads(
    (ROOT / "test-vectors" / "scan_form_fields.json").read_text(encoding="utf-8")
)
TOOL_SCHEMAS = json.loads(
    (ROOT / "test-vectors" / "vision_tool_schemas.json").read_text(encoding="utf-8")
)["doc_types"]

# Streamlit's module names to the doc types of the shared files.
DOC_TYPE_OF_MODULE = {
    "truck": "truck_tag",
    "trailer": "trailer_tag",
    "scale": "scale_ticket",
}


def _doc_types(fixture: dict) -> dict:
    return {key: value for key, value in fixture.items() if not key.startswith("_")}


def problems_in_fixture(fixture: dict, tool_schemas: dict) -> list[str]:
    """Everything wrong with `fixture` against the tool schema file, one sentence each."""
    problems: list[str] = []
    doc_types = _doc_types(fixture)
    if sorted(doc_types) != sorted(tool_schemas):
        problems.append(
            f"doc types {sorted(doc_types)} differ from the tool schema file's {sorted(tool_schemas)}"
        )
    for doc_type, entry in doc_types.items():
        properties = set(tool_schemas.get(doc_type, {}).get("properties", []))
        seen: set[str] = set()
        for group in ("scanned", "manual_only"):
            for field in entry[group]:
                name = field["name"]
                if name in seen:
                    problems.append(f"{doc_type}: {name} appears twice")
                seen.add(name)
                if field["type"] not in ("text", "number"):
                    problems.append(
                        f"{doc_type}: {name} has type {field['type']!r}, not text or number"
                    )
                if group == "scanned" and name not in properties:
                    problems.append(
                        f"{doc_type}: scanned {name} is not a tool schema property"
                    )
                if group == "manual_only" and name in properties:
                    problems.append(
                        f"{doc_type}: manual_only {name} is a tool schema property"
                    )
    return problems


def _field_pairs(entry: dict) -> set[tuple[str, str]]:
    return {
        (field["name"], field["type"])
        for group in ("scanned", "manual_only")
        for field in entry[group]
    }


def problems_in_streamlit(fixture: dict, fields: dict) -> list[str]:
    """Differences between Streamlit's `FIELDS` and the fixture, per doc type, as (name, type)."""
    problems: list[str] = []
    doc_types = _doc_types(fixture)
    for module, doc_type in DOC_TYPE_OF_MODULE.items():
        shown = {(name, kind) for name, _label, kind in fields[module]}
        expected = _field_pairs(doc_types[doc_type])
        for pair in sorted(expected - shown):
            problems.append(f"{module}: fixture has {pair}, Streamlit does not")
        for pair in sorted(shown - expected):
            problems.append(f"{module}: Streamlit has {pair}, fixture does not")
    return problems


# --- the fixture against the tool schema file -----------------------------------------------------


def test_the_fixture_agrees_with_the_tool_schema_file():
    assert problems_in_fixture(FIXTURE, TOOL_SCHEMAS) == []


def test_a_scanned_name_that_is_not_a_tool_property_is_reported():
    bad = copy.deepcopy(FIXTURE)
    bad["truck_tag"]["scanned"][0]["name"] = "manufaturer"
    assert any(
        "scanned manufaturer" in p for p in problems_in_fixture(bad, TOOL_SCHEMAS)
    )


def test_a_manual_only_name_that_is_a_tool_property_is_reported():
    bad = copy.deepcopy(FIXTURE)
    bad["truck_tag"]["manual_only"].append({"name": "vin", "type": "text"})
    assert any("manual_only vin" in p for p in problems_in_fixture(bad, TOOL_SCHEMAS))


def test_a_type_that_is_neither_text_nor_number_is_reported():
    bad = copy.deepcopy(FIXTURE)
    bad["scale_ticket"]["scanned"][1]["type"] = "integer"
    assert any("'integer'" in p for p in problems_in_fixture(bad, TOOL_SCHEMAS))


def test_a_missing_or_extra_doc_type_is_reported():
    missing = copy.deepcopy(FIXTURE)
    del missing["scale_ticket"]
    extra = copy.deepcopy(FIXTURE)
    extra["tire_tag"] = {"scanned": [], "manual_only": []}
    assert any("doc types" in p for p in problems_in_fixture(missing, TOOL_SCHEMAS))
    assert any("doc types" in p for p in problems_in_fixture(extra, TOOL_SCHEMAS))


def test_a_name_listed_twice_is_reported():
    bad = copy.deepcopy(FIXTURE)
    bad["trailer_tag"]["manual_only"].append({"name": "uvw_lb", "type": "number"})
    assert any(
        "uvw_lb appears twice" in p for p in problems_in_fixture(bad, TOOL_SCHEMAS)
    )


# --- Streamlit's form against the fixture ---------------------------------------------------------


def test_streamlit_fields_equal_the_fixture():
    assert problems_in_streamlit(FIXTURE, FIELDS) == []


def test_a_field_streamlit_lacks_is_reported():
    short = {module: list(rows) for module, rows in FIELDS.items()}
    short["truck"] = [row for row in short["truck"] if row[0] != "rear_gawr_lb"]
    assert problems_in_streamlit(FIXTURE, short) == [
        "truck: fixture has ('rear_gawr_lb', 'number'), Streamlit does not"
    ]


def test_a_field_only_streamlit_has_is_reported():
    long = {module: list(rows) for module, rows in FIELDS.items()}
    long["scale"].append(("tare_lb", "Tare (lb)", "number"))
    assert problems_in_streamlit(FIXTURE, long) == [
        "scale: Streamlit has ('tare_lb', 'number'), fixture does not"
    ]


def test_a_field_whose_type_differs_is_reported_as_a_pair_each_way():
    retyped = {module: list(rows) for module, rows in FIELDS.items()}
    retyped["trailer"] = [
        (n, label, "text" if n == "uvw_lb" else k) for n, label, k in retyped["trailer"]
    ]
    assert problems_in_streamlit(FIXTURE, retyped) == [
        "trailer: fixture has ('uvw_lb', 'number'), Streamlit does not",
        "trailer: Streamlit has ('uvw_lb', 'text'), fixture does not",
    ]
