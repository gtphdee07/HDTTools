"""Interface-contract tests: does every name in the Streamlit form's `FIELDS`
still match a real OCR key?

Both `_parse_fields` implementations always populate every key they know
about regardless of whether the regex actually matched anything in the
given text (an unmatched field comes back with a `None` value, the key
itself is never omitted) - so calling with an empty string is enough to
get the complete, real key set; no synthetic label text needed.

**Every FIELDS-declared name must be a real OCR key** (not the reverse -
`FIELDS` deliberately shows only a curated subset of what OCR extracts;
VIN/tire-spec/date/vehicle_type/the *_kg fields are real OCR output but
intentionally not surfaced in the review form, per each OCR module's own
docstring). The actual risk is `streamlit_app/app.py`'s `_extract_fields`,
which does `keep = {name for name, _label, _type in FIELDS[module_key]};
fields = {k: v for k, v in parsed.items() if k in keep}` - if `fields.py`
ever declares a name that doesn't match a real `_parse_fields` key (a
typo, a rename on one side only), that field silently never gets
pre-filled from OCR, even when the OCR read it correctly, and nothing
would show an error.

`FIELDS` legitimately declares a few manual-only fields
(`standalone_weight_lb`, `axle_count`) that OCR never produces at all, by
design (see `ScanFieldMapping.kt`'s Android equivalent of this same
exception) - excluded explicitly below, not just left to pass by
coincidence.

(The opposite direction, every OCR key declared on the FastAPI response
models, went with the FastAPI app: it existed only because `response_model`
silently dropped undeclared keys.)
"""

from __future__ import annotations

import sys
from pathlib import Path

from hdttools import scale_ticket_ocr, trailer_tag_ocr, truck_tag_ocr

# Needed to import fields.py below - app.py relies on Streamlit adding its
# own script directory to sys.path at run time, which pytest doesn't do
# for us when just importing the module directly (same as test_streamlit_app.py).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "streamlit_app"))
from fields import FIELDS  # noqa: E402

import pytest

pytestmark = [pytest.mark.core]

_MANUAL_ONLY_FIELDS = {
    "truck": {"standalone_weight_lb"},
    "trailer": {"axle_count"},
    "scale": set(),
}


def _streamlit_field_names(module_key: str) -> set[str]:
    return {name for name, _label, _type in FIELDS[module_key]}


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
