"""The fail-pool regression test (item #13,
FUTURE_CONSTRAINED_RANDOM_OCR_TESTING.md): resolves a random
known-illegible real photo per doc_type via scripts/fail_pool.py, runs
it through the real Tesseract pipeline, and proves two things:

1. The real extraction still produces the documented `None` failure
   signature (an OCR-level check) - a real regression here means
   Tesseract, ocr_common.py, or a *_ocr.py parser started behaving
   differently against a photo already known to defeat it.
2. That signature still funnels into the app's real "Not Enough
   Information" degradation path via compute_breakdown/verdict_for (an
   app-level check) - a real regression here means the app started
   silently accepting garbled OCR output as real data instead of
   degrading gracefully. Generalizes
   tests/test_breakdown.py::test_blank_rig_reports_not_enough_information_not_a_false_pass
   (a hand-written `{}`) to a real photo's real garbled OCR output.

Unlike tests/test_pass_pool_regression.py, this pool is self-contained
in golden_fields.json's "fail_pool" section rather than referencing
"photos" - these photos were deliberately never added to "photos" (see
ARCHIVE_WEB_STREAMLIT.md's item #11 "document, don't build" finding),
and the golden truth here *is* the failure signature itself, not a
value that would otherwise be duplicated.
"""

import json
import random
import sys
from pathlib import Path

import pytest

from hdttools.api.breakdown import compute_breakdown, verdict_for
from hdttools.ocr_common import ensure_tesseract_configured, ocr_text, open_image, preprocess_image
from hdttools.truck_tag_ocr import _parse_fields as _parse_truck_tag

_EXAMPLE_DOCS = Path(__file__).resolve().parent.parent / "ExampleDocs"
_GOLDEN = json.loads((_EXAMPLE_DOCS / "golden_fields.json").read_text(encoding="utf-8"))

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))  # fail_pool.py is a standalone module, like pass_pool.py

import fail_pool  # noqa: E402

_PARSERS = {
    "truck_tag": _parse_truck_tag,
}

_FAIL_POOL_DOC_TYPES = [dt for dt in _GOLDEN.get("fail_pool", {}) if dt != "_readme"]


@pytest.mark.parametrize("doc_type", _FAIL_POOL_DOC_TYPES)
def test_fail_pool_random_pick_still_produces_documented_none_signature(doc_type):
    filename, entry = fail_pool.resolve_fail_pool_image(doc_type, rng=random.Random())

    ensure_tesseract_configured()
    image = open_image(_EXAMPLE_DOCS / filename)
    text = ocr_text(preprocess_image(image))
    extracted = _PARSERS[doc_type](text)

    for field in entry["expected_none_fields"]:
        assert extracted.get(field) is None, (
            f"{filename} ({doc_type}): field {field!r} used to reliably come back None "
            f"under real Tesseract but now returns {extracted.get(field)!r} - either a "
            "real extraction-API improvement (update golden_fields.json/promote this "
            "photo to the pass-pool) or a real regression, not a silent drift."
        )


def test_fail_pool_random_pick_reaches_not_enough_information_not_a_false_pass():
    filename, entry = fail_pool.resolve_fail_pool_image("truck_tag", rng=random.Random())

    ensure_tesseract_configured()
    image = open_image(_EXAMPLE_DOCS / filename)
    text = ocr_text(preprocess_image(image))
    extracted = _parse_truck_tag(text)

    items = compute_breakdown(extracted, {}, {})
    assert all(item["tone"] == "insufficient" for item in items), (
        f"{filename}: real garbled OCR output produced a non-insufficient breakdown row - "
        "the app is no longer degrading gracefully on a known-illegible real photo."
    )
    verdict = verdict_for(items)
    assert verdict["status"] == "insufficient"
    assert verdict["headline"] == "Not Enough Information"
