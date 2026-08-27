from pathlib import Path

from experiments.BoundOCR.common.evaluation import evaluate_directory
from experiments.BoundOCR.common.ground_truth import parse_gm_spec_file
from experiments.BoundOCR.common.gm_truck_fields import parse_gm_fields
from experiments.BoundOCR.pipelines.contour_quad.pipeline import detect_and_extract
from hdttools.ocr_common import ensure_tesseract_configured

_REPO_ROOT = Path(__file__).resolve().parents[4]
_IMAGES_DIR = _REPO_ROOT / "ExampleDocs" / "scans" / "truck" / "gm_truck"
_SPEC_PATH = _IMAGES_DIR / "GMTruck-Spec.txt"


def test_pipeline_against_the_real_gm_truck_photo():
    ensure_tesseract_configured()
    expected = parse_gm_spec_file(_SPEC_PATH)

    def pipeline_fn(image):
        return detect_and_extract(image, field_parser=parse_gm_fields)

    report = evaluate_directory(pipeline_fn, _IMAGES_DIR, expected)

    assert len(report) == 1
    row = report[0]
    incorrect = {field: s for field, s in row["scores"].items() if not s["correct"]}
    assert not incorrect, f"{row['image']}: fields incorrect - {incorrect}"
