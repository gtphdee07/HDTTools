"""Free checks that the Python vision client and the Worker cannot quietly drift apart (#143).

Both Claude vision External tests read test-vectors/vision_external_cases.json and the golden
values in ExampleDocs/golden_fields.json; both sides send the tool in
test-vectors/vision_tool_schemas.json. The Worker runs the same checks in
workers/scan-proxy/src/visionSharedFixtures.test.ts. No Claude call is made here: the readers'
extract_via_claude is replaced to capture what each one would send."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from hdttools import scale_ticket, trailer_tag, truck_tag

pytestmark = [pytest.mark.core, pytest.mark.minor]

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import vision_cases  # noqa: E402

READERS = {
    "truck_tag": (truck_tag, truck_tag.extract_truck_tag_fields),
    "trailer_tag": (trailer_tag, trailer_tag.extract_trailer_tag_fields),
    "scale_ticket": (scale_ticket, scale_ticket.extract_scale_ticket_fields),
}
TOOL_SCHEMAS = json.loads((ROOT / "test-vectors" / "vision_tool_schemas.json").read_text(encoding="utf-8"))
GOLDEN = json.loads((ROOT / "ExampleDocs" / "golden_fields.json").read_text(encoding="utf-8"))["photos"]


def _external_test_module():
    spec = importlib.util.spec_from_file_location(
        "claude_vision_external_under_check", ROOT / "tests" / "test_claude_vision_external.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --- the shared cases ---------------------------------------------------------------------------


def test_every_shared_case_points_at_an_image_that_exists():
    cases = vision_cases.load_cases()
    assert cases
    missing = [c.image for c in cases if not c.image_path.is_file()]
    assert missing == []


def test_every_shared_case_points_at_a_golden_entry_for_the_same_doc_type():
    for case in vision_cases.load_cases():  # raises KeyError, naming it, when the entry is missing
        assert case.fields, f"{case.golden} has no fields"
        assert GOLDEN[case.golden]["doc_type"] == case.doc_type


def test_a_case_naming_a_golden_entry_that_does_not_exist_fails_to_load(tmp_path, monkeypatch):
    cases_file = tmp_path / "cases.json"
    cases_file.write_text(
        json.dumps({"cases": [{"doc_type": "truck_tag", "image": "AddieTag.jpg", "golden": "NoSuchPhoto.jpg"}]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(vision_cases, "CASES_FILE", cases_file)
    with pytest.raises(KeyError, match="NoSuchPhoto.jpg"):
        vision_cases.load_cases()


def test_the_shared_cases_cover_every_doc_type_exactly_once():
    doc_types = [c.doc_type for c in vision_cases.load_cases()]
    assert sorted(doc_types) == sorted(READERS)


def test_the_external_test_runs_exactly_the_shared_cases():
    external = _external_test_module()
    assert external.CASES == vision_cases.load_cases()
    parametrized = [
        mark
        for mark in external.test_claude_vision_extraction_matches_the_shared_golden_values.pytestmark
        if mark.name == "parametrize"
    ]
    assert len(parametrized) == 1
    assert parametrized[0].args[1] is external.CASES


def test_the_external_test_keeps_no_image_list_or_expected_values_of_its_own():
    source = (ROOT / "tests" / "test_claude_vision_external.py").read_text(encoding="utf-8")
    assert "import pass_pool" not in source and "resolve_pass_pool_image" not in source  # no random pick
    assert 'get("known_ocr_limitations"' not in source  # the tolerance rule lives in vision_cases
    assert source.count(".jpg") == 1  # the one probe image of the free bad-key case, not a case list


# --- the comparison rule ------------------------------------------------------------------------

CASE = vision_cases.VisionCase(
    doc_type="truck_tag",
    image="x.jpg",
    golden="x.jpg",
    fields={"a": 1.0, "b": "x", "c": 5.0},
    known_ocr_limitations={"c": "reads 50"},
)


def test_a_value_that_differs_from_the_golden_value_is_a_mismatch():
    assert vision_cases.new_mismatches(CASE, {"a": 1.0, "b": "y", "c": 5.0}) == {"b": ("y", "x")}


def test_a_field_missing_from_the_answer_is_a_mismatch():
    assert vision_cases.new_mismatches(CASE, {"b": "x", "c": 5.0}) == {"a": (None, 1.0)}


def test_only_a_field_named_in_known_ocr_limitations_is_tolerated():
    assert vision_cases.new_mismatches(CASE, {"a": 1.0, "b": "x", "c": 50.0}) == {}
    assert vision_cases.new_mismatches(CASE, {"a": 1.0, "b": "x"}) == {}


# --- the tool each reader sends -----------------------------------------------------------------


def _sent_tool(module, extract, monkeypatch):
    sent = {}

    def fake(**kwargs):
        sent.update(kwargs)
        return {"front_tire": {}, "rear_tire": {}, "tire": {}}

    monkeypatch.setattr(module, "extract_via_claude", fake)
    monkeypatch.setattr(module, "TireSpec", lambda **kwargs: kwargs, raising=False)
    extract(b"image", "image/jpeg")
    return sent


def test_every_doc_type_has_a_shared_tool_entry():
    assert sorted(TOOL_SCHEMAS["doc_types"]) == sorted(READERS)


@pytest.mark.parametrize("doc_type", sorted(READERS))
def test_a_reader_sends_the_tool_name_property_names_and_required_names_the_worker_sends(doc_type, monkeypatch):
    module, extract = READERS[doc_type]
    shared = TOOL_SCHEMAS["doc_types"][doc_type]

    sent = _sent_tool(module, extract, monkeypatch)
    schema = sent["schema"]

    assert sent["tool_name"] == shared["tool_name"]
    assert list(schema["properties"]) == shared["properties"]
    assert sorted(schema["required"]) == sorted(shared["required"])

    nested = [name for name, prop in schema["properties"].items() if prop.get("type") == "object"]
    assert nested == shared["nested"]
    for name in shared["nested"]:
        tire = schema["properties"][name]
        assert list(tire["properties"]) == TOOL_SCHEMAS["tire"]["properties"]
        assert sorted(tire["required"]) == sorted(TOOL_SCHEMAS["tire"]["required"])
