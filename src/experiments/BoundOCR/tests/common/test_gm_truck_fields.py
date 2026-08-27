from experiments.BoundOCR.common.gm_truck_fields import parse_gm_fields

_SAMPLE_TEXT = """
TRAILERING INFORMATION
1GT49ME75NF161372
VEHICLE AND TRAILER MUST NOT EXCEED ANY OF THESE VALUES.
GVWR: 4831 KG / 10650 LBS
GCWR: 10886 KG / 24000 LBS
RGAWR: 2994 KG / 6600 LBS
CURB WEIGHT: 3254 KG / 7172 LBS
MAX PAYLOAD: 1577 KG / 3478 LBS
SAE J2807 TRAILER WEIGHT RATING (TWR) FOR VEHICLE CONFIGURATION.
CONVENTIONAL TWR: 6577 KG / 14500 LBS
MAX TONGUE WEIGHT: 658 KG / 1450 LBS
GOOSENECK TWR: 7539 KG / 16620 LBS
MAX TONGUE WEIGHT: 1129 KG / 2490 LBS
SEE OWNER'S MANUAL FOR MORE INFORMATION
"""


def test_parse_gm_fields_extracts_all_known_fields():
    fields = parse_gm_fields(_SAMPLE_TEXT)

    assert fields["vin"] == "1GT49ME75NF161372"
    assert fields["gvwr_kg"] == 4831.0
    assert fields["gvwr_lb"] == 10650.0
    assert fields["gcwr_lb"] == 24000.0
    assert fields["rgawr_lb"] == 6600.0
    assert fields["curb_weight_lb"] == 7172.0
    assert fields["max_payload_lb"] == 3478.0
    assert fields["conventional_twr_lb"] == 14500.0
    assert fields["gooseneck_twr_lb"] == 16620.0


def test_parse_gm_fields_distinguishes_tongue_weight_by_position():
    fields = parse_gm_fields(_SAMPLE_TEXT)

    assert fields["max_tongue_weight_conventional_lb"] == 1450.0
    assert fields["max_tongue_weight_gooseneck_lb"] == 2490.0
