from hdttools.truck_tag_ocr import _kg_lb, _parse_fields

# Transcribed OCR-like text from the real Ford-style label in
# ExampleDocs/AddieTag.jpg (same photo as test_readers_integration.py's
# _TRUCK_FIELDS, used here as ground truth for the GVWR/GAWR values).
_SAMPLE = """
MFD. BY FORD MOTOR CO.                    DATE: 09/24     GVWR:    6350 KG (14000 LB)
FRONT GAWR:    2722 KG ( 6000 LB)                REAR GAWR:    4491 KG ( 9900 LB)
WITH 225/70R19.5G 128/126N TIRES              WITH 225/70R19.5G 128/126N TIRES
19.5X6.0RW RIMS                                19.5X6.0RW RIMS
AT 620 kPa/ 90 PSI COLD                        AT 550 kPa/ 80 PSI COLD DUAL
THIS VEHICLE CONFORMS TO ALL APPLICABLE FEDERAL MOTOR VEHICLE
SAFETY STANDARDS IN EFFECT ON THE DATE OF MANUFACTURE SHOWN ABOVE.
VIN: 1FT8W4DM7REF01313    TYPE: Truck
"""


def test_parse_fields_on_ford_style_label():
    fields = _parse_fields(_SAMPLE)

    assert fields["manufacturer"] == "FORD MOTOR CO."
    assert fields["date"] == "09/24"
    assert fields["vin"] == "1FT8W4DM7REF01313"
    assert fields["vehicle_type"] == "Truck"
    assert fields["gvwr_kg"] == 6350.0
    assert fields["gvwr_lb"] == 14000.0
    assert fields["front_gawr_kg"] == 2722.0
    assert fields["front_gawr_lb"] == 6000.0
    assert fields["rear_gawr_kg"] == 4491.0
    assert fields["rear_gawr_lb"] == 9900.0


def test_parse_fields_splits_front_and_rear_tire_specs():
    fields = _parse_fields(_SAMPLE)

    front = fields["front_tire"]
    rear = fields["rear_tire"]
    assert front.tire == "225/70R19.5G 128/126N"
    assert front.rim == "19.5X6.0RW"
    assert front.cold_pressure_kpa == 620.0
    assert front.cold_pressure_psi == 90.0
    assert front.dual is False

    assert rear.tire == "225/70R19.5G 128/126N"
    assert rear.cold_pressure_kpa == 550.0
    assert rear.cold_pressure_psi == 80.0
    assert rear.dual is True


def test_parse_fields_returns_none_for_absent_fields():
    fields = _parse_fields("nothing useful here")
    assert fields["manufacturer"] is None
    assert fields["gvwr_lb"] is None
    assert fields["vin"] is None


def test_parse_fields_tolerates_lb_misread_as_1b():
    # Actual Tesseract output on ExampleDocs/AddieTag.jpg mangled "REAR
    # GAWR:" (no space) and read "LB" as "1B" — regression coverage for
    # the fix in _kg_lb's trailing unit pattern.
    garbled = "REARGAWR: 4491 KG(99001B)"
    kg, lb = _kg_lb("REAR\\s*GAWR", garbled)
    assert kg == 4491.0
    assert lb == 9900.0
