from hdttools.models import ScaleTicketData, TireSpec, TrailerTagData, TruckTagData


def test_scale_ticket_defaults_to_none():
    record = ScaleTicketData(source_image="a.jpg")
    assert record.source_image == "a.jpg"
    assert record.ticket_number is None
    assert record.gross_weight_lb is None


def test_tire_spec_defaults():
    tire = TireSpec()
    assert tire.tire is None
    assert tire.dual is False


def test_truck_tag_holds_front_and_rear_tires():
    truck = TruckTagData(
        vehicle_name="Goose",
        source_image="g.jpg",
        front_tire=TireSpec(tire="225/70R19.5"),
        rear_tire=TireSpec(tire="225/70R19.5", dual=True),
    )
    assert truck.vehicle_name == "Goose"
    assert truck.front_tire.tire == "225/70R19.5"
    assert truck.rear_tire.dual is True


def test_trailer_tag_holds_single_tire():
    trailer = TrailerTagData(
        vehicle_name="Addie",
        source_image="a.jpg",
        tire=TireSpec(tire="ST215/75R17.5"),
    )
    assert trailer.vehicle_name == "Addie"
    assert trailer.tire.tire == "ST215/75R17.5"
