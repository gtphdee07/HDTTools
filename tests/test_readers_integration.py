"""Application-level tests: each read_* function wired end-to-end with
every I/O boundary (file picker, vision extraction, review form, database
save) mocked, so we're testing orchestration and control flow only."""

from hdttools import file_picker, review_form, scale_ticket, scale_ticket_ocr, trailer_tag, truck_tag

_SCALE_FIELDS = {
    "ticket_number": "123",
    "weigh_number": None,
    "date": "7-12-26",
    "time": "10:10",
    "scale_number": "3274",
    "location_name": None,
    "location_address": None,
    "city": None,
    "state": "CO",
    "steer_axle_lb": 5640.0,
    "drive_axle_lb": 9080.0,
    "trailer_axle_lb": 19680.0,
    "gross_weight_lb": 34400.0,
    "company": "Wandering Trails",
    "commodity": "RV",
    "tractor_number": "GOOSE",
    "trailer_number": "ADDIE",
}

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
    "front_tire": {
        "tire": "225/70R19.5", "rim": "19.5x6.0RW",
        "cold_pressure_kpa": 620.0, "cold_pressure_psi": 90.0, "dual": False,
    },
    "rear_tire": {
        "tire": "225/70R19.5", "rim": "19.5x6.0RW",
        "cold_pressure_kpa": 550.0, "cold_pressure_psi": 80.0, "dual": True,
    },
}

_TRAILER_FIELDS = {
    "manufacturer": "Brinkley RV",
    "date": "12/2025",
    "vin": "7T0FG4836TG003166",
    "vehicle_type": "Trailer",
    "gvwr_kg": 10659.0,
    "gvwr_lb": 23500.0,
    "gawr_per_axle_kg": 3629.0,
    "gawr_per_axle_lb": 8000.0,
    "uvw_kg": 9323.0,
    "uvw_lb": 20554.0,
    "tire": {
        "tire": "ST215/75R17.5", "rim": "17.5x6.75",
        "cold_pressure_kpa": 221.0, "cold_pressure_psi": 125.0, "dual": False,
    },
}


def test_read_scale_ticket_saves_reviewed_record(tmp_path, monkeypatch):
    image_path = tmp_path / "ticket.jpg"
    image_path.write_bytes(b"fake")

    monkeypatch.setattr(scale_ticket, "select_image_file", lambda title: image_path)
    monkeypatch.setattr(scale_ticket, "extract_via_claude", lambda **kwargs: dict(_SCALE_FIELDS))
    monkeypatch.setattr(scale_ticket, "review_and_edit", lambda record: record)

    saved = []
    monkeypatch.setattr(scale_ticket, "save_scale_ticket", lambda record: saved.append(record) or 1)

    result = scale_ticket.read_scale_ticket()

    assert result is not None
    assert result.ticket_number == "123"
    assert result.source_image == str(image_path)
    assert saved == [result]


def test_read_scale_ticket_returns_none_when_user_cancels(tmp_path, monkeypatch):
    image_path = tmp_path / "ticket.jpg"
    image_path.write_bytes(b"fake")

    monkeypatch.setattr(scale_ticket, "select_image_file", lambda title: image_path)
    monkeypatch.setattr(scale_ticket, "extract_via_claude", lambda **kwargs: dict(_SCALE_FIELDS))
    monkeypatch.setattr(scale_ticket, "review_and_edit", lambda record: None)

    saved = []
    monkeypatch.setattr(scale_ticket, "save_scale_ticket", lambda record: saved.append(record))

    result = scale_ticket.read_scale_ticket()

    assert result is None
    assert saved == []


def test_read_scale_ticket_ocr_saves_reviewed_record(tmp_path, monkeypatch):
    image_path = tmp_path / "ticket.jpg"
    image_path.write_bytes(b"fake")

    monkeypatch.setattr(scale_ticket_ocr, "_ensure_tesseract_configured", lambda: None)
    monkeypatch.setattr(file_picker, "select_image_file", lambda title: image_path)
    monkeypatch.setattr(scale_ticket_ocr, "_preprocess", lambda path: object())
    monkeypatch.setattr(scale_ticket_ocr, "_ocr_text", lambda image: "STEER AXLE 100 LB")
    monkeypatch.setattr(review_form, "review_and_edit", lambda record: record)

    saved = []
    monkeypatch.setattr(
        scale_ticket_ocr, "save_scale_ticket", lambda record: saved.append(record) or 1
    )

    result = scale_ticket_ocr.read_scale_ticket()

    assert result is not None
    assert result.steer_axle_lb == 100.0
    assert saved == [result]


def test_read_truck_tag_prompts_for_name_and_saves(tmp_path, monkeypatch):
    image_path = tmp_path / "truck.jpg"
    image_path.write_bytes(b"fake")

    monkeypatch.setattr(truck_tag, "select_image_file", lambda title: image_path)
    monkeypatch.setattr(truck_tag, "prompt_vehicle_name", lambda: "Goose")
    monkeypatch.setattr(truck_tag, "extract_via_claude", lambda **kwargs: dict(_TRUCK_FIELDS))
    monkeypatch.setattr(truck_tag, "review_and_edit", lambda record: record)

    saved = []
    monkeypatch.setattr(truck_tag, "save_truck_tag", lambda record: saved.append(record) or 1)

    result = truck_tag.read_truck_tag()

    assert result is not None
    assert result.vehicle_name == "Goose"
    assert result.front_tire.tire == "225/70R19.5"
    assert result.rear_tire.dual is True
    assert saved == [result]


def test_read_truck_tag_returns_none_when_user_cancels(tmp_path, monkeypatch):
    image_path = tmp_path / "truck.jpg"
    image_path.write_bytes(b"fake")

    monkeypatch.setattr(truck_tag, "select_image_file", lambda title: image_path)
    monkeypatch.setattr(truck_tag, "prompt_vehicle_name", lambda: "Goose")
    monkeypatch.setattr(truck_tag, "extract_via_claude", lambda **kwargs: dict(_TRUCK_FIELDS))
    monkeypatch.setattr(truck_tag, "review_and_edit", lambda record: None)

    saved = []
    monkeypatch.setattr(truck_tag, "save_truck_tag", lambda record: saved.append(record))

    result = truck_tag.read_truck_tag()

    assert result is None
    assert saved == []


def test_read_trailer_tag_prompts_for_name_and_saves(tmp_path, monkeypatch):
    image_path = tmp_path / "trailer.jpg"
    image_path.write_bytes(b"fake")

    monkeypatch.setattr(trailer_tag, "select_image_file", lambda title: image_path)
    monkeypatch.setattr(trailer_tag, "prompt_vehicle_name", lambda: "Addie")
    monkeypatch.setattr(trailer_tag, "extract_via_claude", lambda **kwargs: dict(_TRAILER_FIELDS))
    monkeypatch.setattr(trailer_tag, "review_and_edit", lambda record: record)

    saved = []
    monkeypatch.setattr(trailer_tag, "save_trailer_tag", lambda record: saved.append(record) or 1)

    result = trailer_tag.read_trailer_tag()

    assert result is not None
    assert result.vehicle_name == "Addie"
    assert result.tire.tire == "ST215/75R17.5"
    assert saved == [result]
