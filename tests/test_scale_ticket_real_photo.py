"""Runs the real OCR pipeline (real Tesseract, a real ExampleDocs/ photo)
end to end, not transcribed/mocked text. Every other OCR test in this repo
(test_*_ocr_parsing.py) exercises _parse_fields against hand-transcribed
text - real, but never proven against an actual image file. This closes
that specific gap (flagged in NEXT_STEPS.md) for the scale-ticket reader,
using ExampleDocs/CatScale-GooseOnly.jpg - a real tow-vehicle-only CAT
Scale ticket (no trailer hitched) added to support the predictive/
pre-purchase feature's standalone_weight_lb input.
"""

from pathlib import Path

from fastapi.testclient import TestClient

from hdttools.api import main
from hdttools.ocr_common import ensure_tesseract_configured, ocr_text, open_image, preprocess_image
from hdttools.scale_ticket_ocr import _parse_fields

_PHOTO = Path(__file__).resolve().parent.parent / "ExampleDocs" / "CatScale-GooseOnly.jpg"


def test_real_ocr_on_the_tow_vehicle_only_photo_extracts_the_weights_correctly():
    assert _PHOTO.is_file(), f"expected the example photo at {_PHOTO}"

    ensure_tesseract_configured()
    image = open_image(_PHOTO)
    text = ocr_text(preprocess_image(image))
    fields = _parse_fields(text)

    # These are the only fields the app's math actually reads off this
    # ticket (via the standalone-weight scan pipeline) - real Tesseract
    # output on this real photo gets every one of them right.
    assert fields["steer_axle_lb"] == 5560.0
    assert fields["drive_axle_lb"] == 4420.0
    assert fields["gross_weight_lb"] == 9980.0

    standalone_from_axles = fields["steer_axle_lb"] + fields["drive_axle_lb"]
    assert standalone_from_axles == fields["gross_weight_lb"]  # no trailer hitched, so these agree


def test_real_photo_upload_through_the_actual_api_endpoint():
    # Unlike test_api.py's client fixture (which deliberately mocks every
    # OCR/image boundary so that suite doesn't need Tesseract installed),
    # this hits the real /api/extract/scale-ticket endpoint - real
    # multipart upload, real Image.open on the raw bytes, real OCR - with
    # nothing mocked, to prove the FastAPI boundary itself works with an
    # actual file, not just a `b"fake"` placeholder.
    with TestClient(main.app) as client:
        with _PHOTO.open("rb") as f:
            response = client.post(
                "/api/extract/scale-ticket",
                files={"file": ("CatScale-GooseOnly.jpg", f, "image/jpeg")},
            )

    assert response.status_code == 200
    body = response.json()
    assert body["steer_axle_lb"] == 5560.0
    assert body["drive_axle_lb"] == 4420.0
    assert body["gross_weight_lb"] == 9980.0
