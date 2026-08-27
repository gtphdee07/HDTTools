from pathlib import Path

from experiments.BoundOCR.pipelines.contour_quad.pipeline import detect_and_extract
from hdttools.ocr_common import ensure_tesseract_configured, open_image

_REPO_ROOT = Path(__file__).resolve().parents[6]
_IMAGE_PATH = (
    _REPO_ROOT
    / "ExampleDocs"
    / "scans"
    / "truck"
    / "f150_blue_goose_uncropped"
    / "20260824_141530.jpg"
)


def test_detect_and_extract_wires_the_real_stages_together():
    ensure_tesseract_configured()
    image = open_image(_IMAGE_PATH)

    result = detect_and_extract(image)

    assert set(result.keys()) >= {
        "manufacturer",
        "gvwr_lb",
        "front_gawr_lb",
        "rear_gawr_lb",
        "label_found",
        "overall_confidence",
        "box",
    }
    assert isinstance(result["label_found"], bool)
    assert isinstance(result["overall_confidence"], float)
