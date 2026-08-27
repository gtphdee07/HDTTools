from pathlib import Path

from experiments.BoundOCR.common.ground_truth import parse_gm_spec_file, parse_spec_file

_REPO_ROOT = Path(__file__).resolve().parents[5]
_SPEC_PATH = (
    _REPO_ROOT
    / "ExampleDocs"
    / "scans"
    / "truck"
    / "f150_blue_goose_uncropped"
    / "F-150Spec.txt"
)
_GM_SPEC_PATH = (
    _REPO_ROOT / "ExampleDocs" / "scans" / "truck" / "gm_truck" / "GMTruck-Spec.txt"
)


def test_parse_spec_file_reads_the_real_f150_spec():
    result = parse_spec_file(_SPEC_PATH)

    assert result == {
        "manufacturer": "FORD MOTOR CO",
        "gvwr_lb": 7100.0,
        "front_gawr_lb": 3525.0,
        "rear_gawr_lb": 3800.0,
    }


def test_parse_gm_spec_file_reads_the_real_gm_spec():
    result = parse_gm_spec_file(_GM_SPEC_PATH)

    assert result == {
        "vin": "1GT49ME75NF161372",
        "gvwr_lb": 10650.0,
        "gcwr_lb": 24000.0,
        "rgawr_lb": 6600.0,
        "curb_weight_lb": 7172.0,
        "max_payload_lb": 3478.0,
        "conventional_twr_lb": 14500.0,
        "max_tongue_weight_conventional_lb": 1450.0,
        "gooseneck_twr_lb": 16620.0,
        "max_tongue_weight_gooseneck_lb": 2490.0,
    }
