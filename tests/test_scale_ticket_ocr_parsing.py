from hdttools.scale_ticket_ocr import _find_num, _find_str, _parse_fields


def test_find_str_matches_and_returns_none_on_miss():
    assert _find_str(r"DATE:?\s*(\S+)", "DATE: 7-12-26") == "7-12-26"
    assert _find_str(r"NOPE (\S+)", "irrelevant text") is None


def test_find_num_strips_commas_and_returns_none_on_miss():
    assert _find_num(r"WEIGHT ([\d,]+)", "WEIGHT 34,400") == 34400.0
    assert _find_num(r"WEIGHT ([\d,]+)", "no match here") is None


def test_parse_fields_on_clean_layout():
    sample = """
    1327426193441
    TICKET NUMBER
    DATE: 7-12-26
    STEER AXLE 5640 LB
    10:10 DRIVE AXLE 9080 LB
    SCALE: 3274
    LOCATION: LOVES COUNTRY STORES
    TRAILER AXLE 19680 LB
    I 25 EXIT 49
    WALSENBURG CO
    * GROSS WEIGHT 34400 LB
    LIVESTOCK, PRODUCE, PROPERTY, COMMODITY, OR ARTICLE WEIGHED RV BRINKLEY G4170
    COMPANY WANDERING TRAILS INC TRACTOR # GOOSE TRAILER # ADDIE
    WEIGH NUMBER
    2434
    """
    fields = _parse_fields(sample)

    assert fields["date"] == "7-12-26"
    assert fields["time"] == "10:10"
    assert fields["scale_number"] == "3274"
    assert fields["steer_axle_lb"] == 5640.0
    assert fields["drive_axle_lb"] == 9080.0
    assert fields["trailer_axle_lb"] == 19680.0
    assert fields["gross_weight_lb"] == 34400.0
    assert fields["company"] == "WANDERING TRAILS INC"
    assert fields["commodity"] == "RV BRINKLEY G4170"
    assert fields["tractor_number"] == "GOOSE"
    assert fields["trailer_number"] == "ADDIE"
    assert fields["weigh_number"] == "2434"
    assert fields["state"] == "CO"


def test_parse_fields_gross_weight_falls_back_to_last_lb_value():
    # Simulates the "GROSS WEIGHT" label itself getting OCR-mangled
    # (e.g. real-world misread as "crossweicHT").
    sample = "STEER AXLE 100 LB DRIVE AXLE 200 LB TRAILER AXLE 300 LB crossweicHT 999 LB"
    fields = _parse_fields(sample)
    assert fields["gross_weight_lb"] == 999.0


def test_parse_fields_returns_none_for_absent_fields():
    fields = _parse_fields("nothing useful here")
    assert fields["ticket_number"] is None
    assert fields["gross_weight_lb"] is None
    assert fields["company"] is None


def test_parse_fields_on_a_real_tow_vehicle_only_ticket():
    # Real Tesseract output (boilerplate legal text trimmed, everything
    # else verbatim including its actual garbling) from
    # ExampleDocs/CatScale-GooseOnly.jpg - a tow-vehicle-only ticket (no
    # trailer hitched, hence TRAILER AXLE 00 LB) used to populate
    # standalone_weight_lb for the predictive/pre-purchase feature.
    sample = """
    1327426192434
    TICKET NUMBER
    www.catscale.com DATE: 7-11-26 STEER AXLE 5560 LB
    DRIVE AXLE 4420 LB
    15:50 scate: 3274
    Location, LOVES COUNTRY STORES TRAILER AXLE 00 LB
    PUBLIC WEIGHMASTERS ee
    CERTIFICATE OF WALSENBURG CO GrossweicHt 9980LB
    WEIGHT & MEASURE
    LIVESTOCK, PRODUCE, PROPERTY, COMMODITY, OR ARTICLE WEIGHED RV BRINKLEY G4170 0
    company .WANDERING TRAILS INC TRACTOR # GOOSE_traiten# ADDIE
    WEIGH NUMBER
    2434
    """
    fields = _parse_fields(sample)

    # The fields the app's math actually depends on (via the standalone-
    # weight scan pipeline) all parse correctly, including the unhitched
    # trailer axle reading as a real 0.0, not a missing value.
    assert fields["steer_axle_lb"] == 5560.0
    assert fields["drive_axle_lb"] == 4420.0
    assert fields["trailer_axle_lb"] == 0.0
    assert fields["gross_weight_lb"] == 9980.0
    assert fields["date"] == "7-11-26"
    assert fields["time"] == "15:50"
    assert fields["state"] == "CO"
    assert fields["weigh_number"] == "2434"

    # Documented current behavior, not fixed: this ticket's own OCR
    # garbling ("traiten#" run onto "GOOSE" with no space, "Location,"
    # instead of "LOCATION:") defeats tractor_number/trailer_number/
    # location_name's simple regexes. None of these three feed into
    # compute_breakdown - they're cosmetic metadata only.
    assert fields["tractor_number"] == "GOOSE_traiten#"
    assert fields["trailer_number"] is None
    assert "LOVES COUNTRY STORES" in fields["location_name"]
