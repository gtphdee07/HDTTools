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
import shutil
import sys
from pathlib import Path

import pytest

from hdttools.ocr_common import ensure_tesseract_configured, ocr_text, open_image, preprocess_image
from hdttools.scale_ticket_ocr import _parse_fields as _parse_scale_ticket
from hdttools.trailer_tag_ocr import _parse_fields as _parse_trailer_tag
from hdttools.truck_tag_ocr import _parse_fields as _parse_truck_tag

_EXAMPLE_DOCS = Path(__file__).resolve().parent.parent / "ExampleDocs"

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))  # pass_pool.py is a standalone module, like coverage_lib.py

import pass_pool  # noqa: E402
import vehicle_discovery  # noqa: E402

_PARSERS = {
    "truck_tag": _parse_truck_tag,
    "trailer_tag": _parse_trailer_tag,
}

# Reads the merged view (golden_fields.json + anything auto-discovered
# under ExampleDocs/scans/ by scripts/vehicle_discovery.py) so a
# directory-only vehicle still gets parametrized here with no test-code
# change - see that module's docstring for the drop-in-a-folder workflow.
_PASS_POOL_DOC_TYPES = pass_pool.registered_doc_types()


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


def test_a_directory_discovered_vehicle_resolves_and_extracts_for_real(tmp_path, monkeypatch):
    """Integration proof for scripts/vehicle_discovery.py's directory
    convention (item #13's diversity-growth mechanism): builds an
    isolated fake scans/ tree under tmp_path containing a real copy of
    CatScale-GooseOnly.jpg plus a vehicle.json, points
    vehicle_discovery's default scan root at it, and proves
    pass_pool.resolve_pass_pool_image can pick the discovered vehicle
    and that real Tesseract still extracts the documented fields -
    end to end, through the exact production code path, without adding
    a permanent fixture to ExampleDocs/scans/. Uses the doc_type
    "scale_ticket" (currently unregistered in either pool) specifically
    so there's exactly one candidate vehicle to resolve - no seeded RNG
    trickery needed to make the pick deterministic.
    """
    real_photo = _EXAMPLE_DOCS / "CatScale-GooseOnly.jpg"
    vehicle_dir = tmp_path / "scans" / "scale" / "test_only_scale_vehicle"
    vehicle_dir.mkdir(parents=True)
    shutil.copy(real_photo, vehicle_dir / "ticket.jpg")
    (vehicle_dir / "vehicle.json").write_text(
        json.dumps(
            {
                "pool": "pass",
                "fields": {
                    "location_name": "LOVES COUNTRY STORES I 25 EXIT 49 WALSENBURG CO",
                    "scale_number": "3274",
                    "steer_axle_lb": 5560.0,
                    "drive_axle_lb": 4420.0,
                    "trailer_axle_lb": 0.0,
                    "gross_weight_lb": 9980.0,
                },
                "known_ocr_limitations": {
                    "location_name": "Same real limitation documented for this photo in golden_fields.json's 'photos' section."
                },
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(vehicle_discovery, "_DEFAULT_SCANS_ROOT", tmp_path / "scans")

    filename, photo = pass_pool.resolve_pass_pool_image("scale_ticket", rng=random.Random())
    assert filename == "scans/scale/test_only_scale_vehicle/ticket.jpg"

    # Discovered image paths come back relative to the scan root's
    # *parent* (tmp_path here, since we patched the default scans root
    # to tmp_path/"scans") - not _EXAMPLE_DOCS, which this isolated test
    # deliberately never touches.
    ensure_tesseract_configured()
    image = open_image(tmp_path / filename)
    text = ocr_text(preprocess_image(image))
    extracted = _parse_scale_ticket(text)

    known_limitations = set(photo.get("known_ocr_limitations", {}))
    mismatched = {field for field, expected in photo["fields"].items() if extracted.get(field) != expected}
    assert mismatched == known_limitations, (
        f"directory-discovered vehicle: real extraction mismatch {sorted(mismatched)} "
        f"didn't match documented known_ocr_limitations {sorted(known_limitations)}"
    )
