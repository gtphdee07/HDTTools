"""Real Tesseract OCR against every real ExampleDocs/ photo listed in
golden_fields.json's "photos" section, proving each doc-type parser
extracts the real, physically-verified ground truth from the actual
image - not transcribed/mocked text like the *_ocr_parsing.py suites
exercise, and not just one hand-picked case like
test_scale_ticket_real_photo.py's original scale-ticket test.

Parametrized per field (not per photo): adding a new brand/format later
needs only a new "photos" entry (plus the photo file itself) in
golden_fields.json - no new test code. A field listed under a photo's
"known_ocr_limitations" gets xfail(strict=True) with the recorded real
reason instead of either asserting a value real OCR doesn't actually
produce or silently skipping the check - if it ever starts passing for
real, the strict xfail turns into a hard failure demanding the
limitation note be removed, not a silent pass. See golden_fields.json's
own "_readme" and NEXT_STEPS.md/ARCHIVE_WEB_STREAMLIT.md item #6.
"""

import json
from functools import lru_cache
from pathlib import Path

import pytest

from hdttools.ocr_common import ensure_tesseract_configured, ocr_text, open_image, preprocess_image
from hdttools.scale_ticket_ocr import _parse_fields as _parse_scale_ticket
from hdttools.trailer_tag_ocr import _parse_fields as _parse_trailer_tag
from hdttools.truck_tag_ocr import _parse_fields as _parse_truck_tag

_EXAMPLE_DOCS = Path(__file__).resolve().parent.parent / "ExampleDocs"
_GOLDEN = json.loads((_EXAMPLE_DOCS / "golden_fields.json").read_text(encoding="utf-8"))

_PARSERS = {
    "truck_tag": _parse_truck_tag,
    "trailer_tag": _parse_trailer_tag,
    "scale_ticket": _parse_scale_ticket,
}


def _field_cases():
    cases = []
    for filename, photo in _GOLDEN["photos"].items():
        limitations = photo.get("known_ocr_limitations", {})
        for field_name, expected in photo["fields"].items():
            case_id = f"{filename}-{field_name}"
            if field_name in limitations:
                cases.append(
                    pytest.param(
                        filename,
                        photo["doc_type"],
                        field_name,
                        expected,
                        marks=pytest.mark.xfail(reason=limitations[field_name], strict=True),
                        id=case_id,
                    )
                )
            else:
                cases.append(pytest.param(filename, photo["doc_type"], field_name, expected, id=case_id))
    return cases


@lru_cache(maxsize=None)
def _real_ocr_fields(filename: str, doc_type: str) -> dict:
    # Cached so every field of the same photo (several parametrized cases
    # each) doesn't re-run real Tesseract OCR on the same image - the OCR
    # pass itself is the slow, shared part; only the parsed-field lookup
    # differs per case.
    photo_path = _EXAMPLE_DOCS / filename
    assert photo_path.is_file(), f"expected the example photo at {photo_path}"

    ensure_tesseract_configured()
    image = open_image(photo_path)
    text = ocr_text(preprocess_image(image))
    return _PARSERS[doc_type](text)


@pytest.mark.parametrize("filename,doc_type,field_name,expected", _field_cases())
def test_real_ocr_matches_golden_ground_truth(filename, doc_type, field_name, expected):
    fields = _real_ocr_fields(filename, doc_type)
    assert fields.get(field_name) == expected
