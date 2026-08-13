"""API-level tests: routing, schema validation, and orchestration, with
every OCR/image boundary mocked (same monkeypatch style as
test_readers_integration.py) so the suite doesn't need Tesseract installed
to run. Each test gets an isolated temp SQLite file via a dependency
override, so nothing touches the real dev database."""

import pytest
from fastapi.testclient import TestClient

from hdttools.api import main
from hdttools.models import TireSpec


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    main.app.dependency_overrides[main.get_db_path] = lambda: db_path
    monkeypatch.setattr(main, "ensure_tesseract_configured", lambda: None)
    monkeypatch.setattr(main, "ocr_text", lambda image: "irrelevant")
    monkeypatch.setattr(main.Image, "open", lambda data: object())
    monkeypatch.setattr(main, "preprocess_image", lambda image: image)
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.dependency_overrides.clear()


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


def test_get_rigs_returns_seeded_rig(client):
    response = client.get("/api/rigs")
    assert response.status_code == 200
    rigs = response.json()
    assert len(rigs) == 1
    assert rigs[0]["truck_name"] == "Big Blue (Ford F-350)"


def test_create_check_computes_verdict_and_persists(client):
    rig_id = client.get("/api/rigs").json()[0]["id"]

    payload = {
        "rig_id": rig_id,
        "truck": {"gvwr_lb": 14000, "front_gawr_lb": 6000, "rear_gawr_lb": 9500},
        "trailer": {"gvwr_lb": 12500, "gawr_per_axle_lb": 6000},
        "scale": {
            "steer_axle_lb": 5620,
            "drive_axle_lb": 9040,
            "trailer_axle_lb": 11380,
            "gross_weight_lb": 26040,
        },
    }
    response = client.post("/api/checks", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "fail"
    assert body["verdictInfo"]["headline"] == "Not Safe to Tow"
    assert len(body["breakdownItems"]) == 6

    history = client.get("/api/checks").json()
    assert len(history) == 1
    assert history[0]["truck_name"] == "Big Blue (Ford F-350)"
    assert history[0]["verdict"] == "fail"


def test_create_check_with_unknown_rig_returns_404(client):
    response = client.post(
        "/api/checks",
        json={"rig_id": 999, "truck": {}, "trailer": {}, "scale": {}},
    )
    assert response.status_code == 404
