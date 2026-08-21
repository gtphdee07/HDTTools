"""API-level tests: routing, schema validation, and orchestration, with
every OCR/image boundary mocked (same monkeypatch style as
test_readers_integration.py) so the suite doesn't need Tesseract installed
to run. The API is stateless (no persistence) — each platform keeps its
own recent-rigs/history state locally, so there's nothing to isolate per
test beyond the OCR mocks."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hdttools.api import main
from hdttools.models import TireSpec

_PIN_WEIGHT_PCT_CONTRACT = json.loads(
    (Path(__file__).resolve().parent.parent / "test-vectors" / "pin_weight_pct_contract.json").read_text()
)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, "ensure_tesseract_configured", lambda: None)
    monkeypatch.setattr(main, "ocr_text", lambda image: "irrelevant")
    monkeypatch.setattr(main.Image, "open", lambda data: object())
    monkeypatch.setattr(main, "preprocess_image", lambda image: image)
    with TestClient(main.app) as test_client:
        yield test_client


_TRUCK_FIELDS = {
    "manufacturer": "Ford",
    "date": "09/24",
    "vin": "1FT8W4DM7REF01313",
    "vehicle_type": "Truck",
    "gvwr_kg": 6350.0,
    "gvwr_lb": 14000.0,
    "front_gawr_kg": 2722.0,
    "front_gawr_lb": 6000.0,
    "rear_gawr_kg": 4491.0,
    "rear_gawr_lb": 9900.0,
    "front_tire": TireSpec(tire="225/70R19.5", dual=False),
    "rear_tire": TireSpec(tire="225/70R19.5", dual=True),
}

_TRAILER_FIELDS = {
    "manufacturer": "Brinkley RV",
    "date": "12/2025",
    "vin": "7T0FG4836TG003166",
    "vehicle_type": "TRAILER",
    "gvwr_kg": 10659.0,
    "gvwr_lb": 23500.0,
    "gawr_per_axle_kg": 3629.0,
    "gawr_per_axle_lb": 8000.0,
    "uvw_kg": 9323.0,
    "uvw_lb": 20554.0,
    "tire": TireSpec(tire="ST215/75R17.5", dual=False),
}

_SCALE_FIELDS = {
    "ticket_number": "123",
    "date": "7-12-26",
    "steer_axle_lb": 5620.0,
    "drive_axle_lb": 9040.0,
    "trailer_axle_lb": 11380.0,
    "gross_weight_lb": 26040.0,
}


def test_extract_truck_tag_returns_parsed_fields(client, monkeypatch):
    monkeypatch.setattr(main.truck_tag_ocr, "_parse_fields", lambda text: dict(_TRUCK_FIELDS))

    response = client.post("/api/extract/truck-tag", files={"file": ("truck.jpg", b"fake", "image/jpeg")})

    assert response.status_code == 200
    body = response.json()
    assert body["manufacturer"] == "Ford"
    assert body["front_gawr_lb"] == 6000.0
    assert body["rear_tire"]["dual"] is True


def test_extract_trailer_tag_returns_parsed_fields(client, monkeypatch):
    monkeypatch.setattr(main.trailer_tag_ocr, "_parse_fields", lambda text: dict(_TRAILER_FIELDS))

    response = client.post("/api/extract/trailer-tag", files={"file": ("trailer.jpg", b"fake", "image/jpeg")})

    assert response.status_code == 200
    body = response.json()
    assert body["gawr_per_axle_lb"] == 8000.0
    assert body["tire"]["tire"] == "ST215/75R17.5"


def test_extract_scale_ticket_returns_parsed_fields(client, monkeypatch):
    monkeypatch.setattr(main.scale_ticket_ocr, "_parse_fields", lambda text: dict(_SCALE_FIELDS))

    response = client.post("/api/extract/scale-ticket", files={"file": ("ticket.jpg", b"fake", "image/jpeg")})

    assert response.status_code == 200
    assert response.json()["gross_weight_lb"] == 26040.0


def test_extract_rejects_non_image_upload(client):
    response = client.post(
        "/api/extract/truck-tag", files={"file": ("notes.txt", b"hello", "text/plain")}
    )
    assert response.status_code == 400


def test_breakdown_endpoint_computes_verdict():
    with TestClient(main.app) as client:
        payload = {
            "truck": {"gvwr_lb": 14000, "front_gawr_lb": 6000, "rear_gawr_lb": 9500},
            "trailer": {"gvwr_lb": 12500, "gawr_per_axle_lb": 6000},
            "scale": {
                "steer_axle_lb": 5620,
                "drive_axle_lb": 9040,
                "trailer_axle_lb": 11380,
                "gross_weight_lb": 26040,
            },
        }
        response = client.post("/api/breakdown", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "fail"
    assert body["verdictInfo"]["headline"] == "Not Safe to Tow"
    assert len(body["breakdownItems"]) == 6
    assert "date" in body


def test_breakdown_endpoint_reflects_axle_count_and_standalone_weight():
    with TestClient(main.app) as client:
        payload = {
            "truck": {
                "gvwr_lb": 14000, "front_gawr_lb": 6000, "rear_gawr_lb": 9500,
                "standalone_weight_lb": 13000,
            },
            "trailer": {"gvwr_lb": 12500, "gawr_per_axle_lb": 6000, "axle_count": 3},
            "scale": {
                "steer_axle_lb": 5620,
                "drive_axle_lb": 9040,
                "trailer_axle_lb": 11380,
                "gross_weight_lb": 26040,
            },
        }
        response = client.post("/api/breakdown", json=payload)

    assert response.status_code == 200
    items = {item["label"]: item for item in response.json()["breakdownItems"]}
    assert items["Trailer Axle(s)"]["limitLabel"] == "18,000 lb"
    assert items["Trailer Total (GVWR)"]["actualLabel"] == "13,040 lb"


def test_breakdown_endpoint_accepts_a_custom_pin_weight_pct():
    with TestClient(main.app) as client:
        payload = {
            "truck": {"gvwr_lb": 14000, "front_gawr_lb": 6000, "rear_gawr_lb": 9500},
            "trailer": {"gvwr_lb": 12500, "gawr_per_axle_lb": 6000},
            "scale": {
                "steer_axle_lb": 5620,
                "drive_axle_lb": 9040,
                "trailer_axle_lb": 11380,
                "gross_weight_lb": 26040,
            },
            "pin_weight_pct": 0.15,
        }
        response = client.post("/api/breakdown", json=payload)

    assert response.status_code == 200
    items = {item["label"]: item for item in response.json()["breakdownItems"]}
    # 11,380 / (1 - 0.15) = 13,388, not the 0.20-default 14,225.
    assert items["Trailer Total (GVWR)"]["actualLabel"] == "13,388 lb"


def test_breakdown_endpoint_reports_insufficient_status_for_a_blank_rig():
    with TestClient(main.app) as client:
        payload = {"truck": {}, "trailer": {}, "scale": {}}
        response = client.post("/api/breakdown", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "insufficient"
    assert body["verdictInfo"]["status"] == "insufficient"
    assert body["verdictInfo"]["headline"] == "Not Enough Information"
    assert all(item["tone"] == "insufficient" for item in body["breakdownItems"])


def test_breakdown_endpoint_pin_weight_pct_is_a_fraction_not_the_ui_percentage():
    # Interface-contract test, paired with web/src/api.test.ts's matching
    # case via test-vectors/pin_weight_pct_contract.json. Both Web's
    # ReviewStep slider and Android's TruckTagEntryScreen slider work in
    # whole percentage points (15-25); this endpoint's pin_weight_pct is
    # the 0.15-0.25 fraction each platform's own thin conversion layer
    # (web/src/api.ts, RigCheckViewModel) divides by 100 to produce
    # before calling here - nothing on the Python side enforces that
    # conversion happened, so this test proves both halves: the fraction
    # produces the documented math, AND sending the raw UI number
    # unconverted produces a visibly, not silently, wrong result (dividing
    # by a negative number), which is why the conversion actually matters.
    ui_percent = _PIN_WEIGHT_PCT_CONTRACT["ui_percent"]
    api_fraction = _PIN_WEIGHT_PCT_CONTRACT["api_fraction"]
    assert api_fraction == ui_percent / 100

    truck = {"gvwr_lb": 14000, "front_gawr_lb": 6000, "rear_gawr_lb": 9500}
    trailer = {"gvwr_lb": 12500, "gawr_per_axle_lb": 6000}
    scale = {
        "steer_axle_lb": 5620, "drive_axle_lb": 9040,
        "trailer_axle_lb": 11380, "gross_weight_lb": 26040,
    }

    with TestClient(main.app) as client:
        correct = client.post(
            "/api/breakdown",
            json={"truck": truck, "trailer": trailer, "scale": scale, "pin_weight_pct": api_fraction},
        )
        unconverted = client.post(
            "/api/breakdown",
            json={"truck": truck, "trailer": trailer, "scale": scale, "pin_weight_pct": ui_percent},
        )

    correct_total = next(
        i for i in correct.json()["breakdownItems"] if i["label"] == "Trailer Total (GVWR)"
    )
    unconverted_total = next(
        i for i in unconverted.json()["breakdownItems"] if i["label"] == "Trailer Total (GVWR)"
    )
    # 11,380 / (1 - 0.15) = 13,388 - matches
    # test_breakdown_endpoint_accepts_a_custom_pin_weight_pct's own math.
    assert correct_total["actualLabel"] == "13,388 lb"
    # 11,380 / (1 - 15) = 11,380 / -14 - a negative weight, not a subtly
    # off number, so the mistake this test guards against would be
    # obvious in the UI, not silently wrong.
    unconverted_value = float(unconverted_total["actualLabel"].replace(",", "").split()[0])
    assert unconverted_value < 0


def test_breakdown_endpoint_response_preserves_the_estimated_field():
    # Interface-contract test between breakdown.py (produces "estimated"
    # per item) and schemas.py's BreakdownItemOut (declares it) - nothing
    # else in this suite ever inspects this key, so a rename/drop on
    # either side would go uncaught even though every other breakdown
    # test would still pass. Real (non-mocked) compute_breakdown call -
    # it has no I/O, so the client fixture's OCR mocks aren't needed here,
    # same as the other /api/breakdown tests above.
    with TestClient(main.app) as client:
        # Truck: a real steer-axle reading (so "Front Axle (Steer)" gets a
        # real, non-estimated pass/fail) but no drive-axle reading, so
        # there's no full hitched combined reading - forces "Tow Vehicle
        # Total (GVWR)" down the stand-alone-weight estimate branch.
        # Trailer: no scale data at all - forces "Trailer Total (GVWR)"
        # down the GVWR-fallback estimate branch too.
        payload = {
            "truck": {
                "gvwr_lb": 14000, "front_gawr_lb": 6000, "rear_gawr_lb": 9500,
                "standalone_weight_lb": 6000,
            },
            "trailer": {"gvwr_lb": 12500, "gawr_per_axle_lb": 6000},
            "scale": {"steer_axle_lb": 5620},
        }
        response = client.post("/api/breakdown", json=payload)

    assert response.status_code == 200
    items = {item["label"]: item for item in response.json()["breakdownItems"]}
    assert items["Tow Vehicle Total (GVWR)"]["estimated"] is True
    assert items["Trailer Total (GVWR)"]["estimated"] is True
    # A row driven by a real reading, not an estimate, must stay False -
    # confirms the field isn't just always true/always present-but-unused.
    assert items["Front Axle (Steer)"]["tone"] == "success"
    assert items["Front Axle (Steer)"]["estimated"] is False
