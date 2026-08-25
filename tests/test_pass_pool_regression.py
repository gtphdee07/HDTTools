"""The first real pass-pool regression test (item #13,
FUTURE_CONSTRAINED_RANDOM_OCR_TESTING.md): resolves a random real photo
per doc_type via scripts/pass_pool.py, runs it through the real
Tesseract pipeline, and asserts extraction still matches the documented
golden state in ExampleDocs/golden_fields.json.

A failure here means a real regression in the extraction API itself
(Tesseract, ocr_common.py, or a *_ocr.py parser) - not an
accuracy-tuning signal, since every pool member's exact behavior
(including any known_ocr_limitations) is already known before it's
added to the pool. Unlike tests/test_real_photo_ocr_accuracy.py's
exhaustive per-photo/per-field parametrization, this test resolves its
photo *at run time* via an unseeded random.Random() - "different
answers back... versus the same ones, all the time" was the project
owner's own framing for why this needs to be random at execution time,
not a fixed enumerated case. The single invariant checked (mismatched
fields == documented known_ocr_limitations) catches drift in both
directions: a new mismatch is a real regression, and a previously
limited field suddenly matching is a real improvement worth updating
golden_fields.json for.

Parametrized over doc_type (not filename) so a new pass-pool vehicle or
doc_type needs no new test code here - only a golden_fields.json edit,
same "no new test code needed" philosophy test_real_photo_ocr_accuracy.py
already uses for its own fixtures.
"""

import json
import random
import sys
from pathlib import Path

import pytest

from hdttools.ocr_common import ensure_tesseract_configured, ocr_text, open_image, preprocess_image
from hdttools.trailer_tag_ocr import _parse_fields as _parse_trailer_tag
from hdttools.truck_tag_ocr import _parse_fields as _parse_truck_tag

_EXAMPLE_DOCS = Path(__file__).resolve().parent.parent / "ExampleDocs"
_GOLDEN = json.loads((_EXAMPLE_DOCS / "golden_fields.json").read_text(encoding="utf-8"))

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))  # pass_pool.py is a standalone module, like coverage_lib.py

import pass_pool  # noqa: E402

_PARSERS = {
    "truck_tag": _parse_truck_tag,
    "trailer_tag": _parse_trailer_tag,
}

_PASS_POOL_DOC_TYPES = [dt for dt in _GOLDEN.get("pass_pool", {}) if dt != "_readme"]


@pytest.mark.parametrize("doc_type", _PASS_POOL_DOC_TYPES)
def test_pass_pool_random_pick_extraction_matches_documented_state(doc_type):
    filename, photo = pass_pool.resolve_pass_pool_image(doc_type, rng=random.Random())

    ensure_tesseract_configured()
    image = open_image(_EXAMPLE_DOCS / filename)
    text = ocr_text(preprocess_image(image))
    extracted = _PARSERS[doc_type](text)

    known_limitations = set(photo.get("known_ocr_limitations", {}))
    mismatched = {field for field, expected in photo["fields"].items() if extracted.get(field) != expected}

    assert mismatched == known_limitations, (
        f"{filename} ({doc_type}): real extraction drifted from documented state - "
        f"now mismatched: {sorted(mismatched)}, documented known_ocr_limitations: "
        f"{sorted(known_limitations)}. A field newly present in 'now mismatched' is a "
        "real regression; a field missing from it (present in 'documented' but not "
        "'now mismatched') is a real improvement - either way, golden_fields.json's "
        "known_ocr_limitations for this photo needs updating to match reality."
    )
