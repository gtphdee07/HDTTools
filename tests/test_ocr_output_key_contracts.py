"""Interface-contract tests: does each OCR module's real `_parse_fields()`
output key set still match what its two real downstream consumers expect?

Both `_parse_fields` implementations always populate every key they know
about regardless of whether the regex actually matched anything in the
given text (an unmatched field comes back with a `None` value, the key
itself is never omitted) - so calling with an empty string is enough to
get the complete, real key set; no synthetic label text needed.

Two known gaps closed here, previously flagged in `tests/TESTING.md`'s
"Known gaps" note and the root `TESTING.md`'s cross-platform section -
the two checks below are opposite *directions* of the same underlying
risk (a real key one side has, the other side doesn't recognize), since
each consumer fails silently in a different way:

1. **schemas.py direction: every OCR key must be a declared schema
   field.** FastAPI's `/api/extract/*` endpoints use `response_model=`,
   and Pydantic's default `extra="ignore"` behavior means a
   `_parse_fields` key that isn't declared on the matching model gets
   silently dropped from the JSON response - no error, just a missing
   field in the UI. `test_api.py`'s extract tests only assert specific
   known-good fields survive, not that the *complete* key set does.
2. **`fields.py` direction: every FIELDS-declared name must be a real
   OCR key** (not the reverse - `FIELDS` deliberately shows only a
   curated subset of what OCR extracts; VIN/tire-spec/date/vehicle_type/
   the *_kg fields are real OCR output but intentionally not surfaced in
   the review form, per each OCR module's own docstring). The actual
   risk is `streamlit_app/app.py`'s `_extract_fields`, which does
   `keep = {name for name, _label, _type in FIELDS[module_key]};
   fields = {k: v for k, v in parsed.items() if k in keep}` - if
   `fields.py` ever declares a name that doesn't match a real
   `_parse_fields` key (a typo, a rename on one side only), that field
   silently never gets pre-filled from OCR, even when the OCR read it
   correctly, and nothing would show an error.

Both schemas.py and FIELDS legitimately declare a few manual-only fields
(`standalone_weight_lb`, `axle_count`) that OCR never produces at all, by
design (see `ScanFieldMapping.kt`'s Android equivalent of this same
exception) - excluded explicitly below, not just left to pass by
coincidence.
"""

from __future__ import annotations

import sys
from dataclasses import fields as dataclass_fields
from pathlib import Path

from hdttools import scale_ticket_ocr, trailer_tag_ocr, truck_tag_ocr
from hdttools.api.schemas import ScaleTicketOut, TireSpecOut, TrailerTagOut, TruckTagOut
from hdttools.models import TireSpec

# Needed to import fields.py below - app.py relies on Streamlit adding its
# own script directory to sys.path at run time, which pytest doesn't do
# for us when just importing the module directly (same as test_streamlit_app.py).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "streamlit_app"))
from fields import FIELDS  # noqa: E402

_MANUAL_ONLY_FIELDS = {
    "truck": {"standalone_weight_lb"},
    "trailer": {"axle_count"},
    "scale": set(),
}


def _schema_field_names(model_cls) -> set[str]:
    return set(model_cls.model_fields.keys())


def _streamlit_field_names(module_key: str) -> set[str]:
    return {name for name, _label, _type in FIELDS[module_key]}


def test_truck_tag_ocr_output_keys_are_all_declared_on_truck_tag_out():
    unknown = set(truck_tag_ocr._parse_fields("").keys()) - _schema_field_names(TruckTagOut)
    assert not unknown


def test_trailer_tag_ocr_output_keys_are_all_declared_on_trailer_tag_out():
    unknown = set(trailer_tag_ocr._parse_fields("").keys()) - _schema_field_names(TrailerTagOut)
    assert not unknown


def test_scale_ticket_ocr_output_keys_are_all_declared_on_scale_ticket_out():
    unknown = set(scale_ticket_ocr._parse_fields("").keys()) - _schema_field_names(ScaleTicketOut)
    assert not unknown


def test_tire_spec_dataclass_fields_match_tire_spec_out():
    # The nested model both truck_tag_ocr (front_tire/rear_tire) and
    # trailer_tag_ocr (tire) embed - checked once here rather than
    # per-parent, since it's the same TireSpec/TireSpecOut pair either way.
    dataclass_names = {f.name for f in dataclass_fields(TireSpec)}
    assert dataclass_names == _schema_field_names(TireSpecOut)


def test_every_streamlit_truck_field_name_maps_to_a_real_ocr_key():
    expected = _streamlit_field_names("truck") - _MANUAL_ONLY_FIELDS["truck"]
    missing = expected - set(truck_tag_ocr._parse_fields("").keys())
    assert not missing


def test_every_streamlit_trailer_field_name_maps_to_a_real_ocr_key():
    expected = _streamlit_field_names("trailer") - _MANUAL_ONLY_FIELDS["trailer"]
    missing = expected - set(trailer_tag_ocr._parse_fields("").keys())
    assert not missing


def test_every_streamlit_scale_field_name_maps_to_a_real_ocr_key():
    expected = _streamlit_field_names("scale") - _MANUAL_ONLY_FIELDS["scale"]
    missing = expected - set(scale_ticket_ocr._parse_fields("").keys())
    assert not missing
