from hdttools.trailer_tag_ocr import _parse_fields

# Transcribed OCR-like text from the real bilingual Brinkley RV label in
# ExampleDocs/GooseTag.jpg (same photo as test_readers_integration.py's
# _TRAILER_FIELDS, used here as ground truth for the GVWR/GAWR/UVW values).
_SAMPLE = """
MANUFACTURED BY/FABRIQUE PAR: Brinkley RV                    DATE: 12/2025
GVWR / PNBV 10659 KG (23500 LB)
GAWR (EACH AXLE) / PNBE (CHAQUE ESSIEU) 3629 KG (8000 LB)
UVW 9323 KG (20554 LB)
TIRE/PNEU ST215/75R17.5 RIM/JANTE 17.5 X 6.75 8-6.5
COLD INFL. PRESS/PRESS. DE GONFL. A FROID 221 KPA (125 PSI/LPC) SINGLE
THIS VEHICLE CONFORMS TO ALL APPLICABLE U.S. FEDERAL MOTOR VEHICLE SAFETY
STANDARDS IN EFFECT ON THE DATE OF MANUFACTURE SHOWN ABOVE.
V.I.N./N.I.V.: 7T0FG4836TG003166 TYPE/TYPE: TRAILER TRA/REM: Fifth Wheel
"""


def test_parse_fields_on_bilingual_trailer_label():
    fields = _parse_fields(_SAMPLE)

    assert fields["manufacturer"] == "Brinkley RV"
    assert fields["date"] == "12/2025"
    assert fields["vin"] == "7T0FG4836TG003166"
    assert fields["vehicle_type"] == "TRAILER"
    assert fields["gvwr_kg"] == 10659.0
    assert fields["gvwr_lb"] == 23500.0
    assert fields["gawr_per_axle_kg"] == 3629.0
    assert fields["gawr_per_axle_lb"] == 8000.0
    assert fields["uvw_kg"] == 9323.0
    assert fields["uvw_lb"] == 20554.0


def test_parse_fields_tire_spec():
    fields = _parse_fields(_SAMPLE)
    tire = fields["tire"]

    assert tire.tire == "ST215/75R17.5"
    assert tire.rim == "17.5 X 6.75 8-6.5"
    assert tire.cold_pressure_kpa == 221.0
    assert tire.cold_pressure_psi == 125.0
    assert tire.dual is False


def test_parse_fields_returns_none_for_absent_fields():
    fields = _parse_fields("nothing useful here")
    assert fields["manufacturer"] is None
    assert fields["gvwr_lb"] is None
    assert fields["vin"] is None
