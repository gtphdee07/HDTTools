from pathlib import Path

import pytest
from PIL import Image

from experiments.BoundOCR.common.evaluation import score_image
from experiments.BoundOCR.common.ground_truth import parse_spec_file
from experiments.BoundOCR.pipelines.contour_quad.pipeline import detect_and_extract
from hdttools.ocr_common import ensure_tesseract_configured

_REPO_ROOT = Path(__file__).resolve().parents[4]
_IMAGES_DIR = _REPO_ROOT / "ExampleDocs" / "scans" / "truck" / "f150_blue_goose_uncropped"
_SPEC_PATH = _IMAGES_DIR / "F-150Spec.txt"
_IMAGE_NAMES = sorted(p.name for p in _IMAGES_DIR.glob("*.jpg"))


@pytest.mark.parametrize("image_name", _IMAGE_NAMES)
def test_pipeline_against_all_ten_real_f150_photos(image_name):
    ensure_tesseract_configured()
    expected = parse_spec_file(_SPEC_PATH)
    image = Image.open(_IMAGES_DIR / image_name)

    result = detect_and_extract(image)
    scores = score_image(result, expected)

    incorrect = {field: s for field, s in scores.items() if not s["correct"]}
    assert not incorrect, (
        f"{image_name}: fields incorrect - {incorrect} "
        f"(expected {expected}, got {result})"
    )
