import sqlite3

from hdttools.database import (
    _flatten,
    save_scale_ticket,
    save_trailer_tag,
    save_truck_tag,
)
from hdttools.models import ScaleTicketData, TireSpec, TrailerTagData, TruckTagData


def test_flatten_prefixes_nested_dataclass_fields():
    truck = TruckTagData(
        vehicle_name="Goose",
        source_image="g.jpg",
        front_tire=TireSpec(tire="225/70R19.5", dual=False),
        rear_tire=TireSpec(tire="225/70R19.5", dual=True),
    )
    flat = _flatten(truck)

    assert flat["vehicle_name"] == "Goose"
    assert flat["front_tire_tire"] == "225/70R19.5"
    assert flat["front_tire_dual"] is False
    assert flat["rear_tire_dual"] is True


def test_save_scale_ticket_creates_table_and_row(tmp_path):
    db_path = tmp_path / "test.db"
    record = ScaleTicketData(source_image="x.jpg", ticket_number="123", gross_weight_lb=34400.0)

    row_id = save_scale_ticket(record, db_path=db_path)
    assert row_id == 1

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT source_image, ticket_number, gross_weight_lb FROM scale_tickets WHERE id = ?",
        (row_id,),
    ).fetchone()
    assert row == ("x.jpg", "123", 34400.0)


def test_save_truck_tag_flattens_tires(tmp_path):
    db_path = tmp_path / "test.db"
    truck = TruckTagData(
        vehicle_name="Goose",
        source_image="g.jpg",
        vin="1FT8W4DM7REF01313",
        front_tire=TireSpec(tire="225/70R19.5", dual=False),
        rear_tire=TireSpec(tire="225/70R19.5", dual=True),
    )
    row_id = save_truck_tag(truck, db_path=db_path)

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT vehicle_name, vin, front_tire_dual, rear_tire_dual FROM truck_tags WHERE id = ?",
        (row_id,),
    ).fetchone()
    assert row == ("Goose", "1FT8W4DM7REF01313", 0, 1)


def test_save_trailer_tag(tmp_path):
    db_path = tmp_path / "test.db"
    trailer = TrailerTagData(
        vehicle_name="Addie",
        source_image="a.jpg",
        tire=TireSpec(tire="ST215/75R17.5"),
    )
    row_id = save_trailer_tag(trailer, db_path=db_path)

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT vehicle_name, tire_tire FROM trailer_tags WHERE id = ?", (row_id,)
    ).fetchone()
    assert row == ("Addie", "ST215/75R17.5")


def test_multiple_saves_increment_row_id(tmp_path):
    db_path = tmp_path / "test.db"
    record = ScaleTicketData(source_image="a.jpg")

    first_id = save_scale_ticket(record, db_path=db_path)
    second_id = save_scale_ticket(record, db_path=db_path)

    assert second_id == first_id + 1
