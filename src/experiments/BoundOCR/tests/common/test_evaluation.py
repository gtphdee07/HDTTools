from pathlib import Path

from experiments.BoundOCR.common.evaluation import evaluate_directory

_REPO_ROOT = Path(__file__).resolve().parents[5]
_IMAGES_DIR = (
    _REPO_ROOT / "ExampleDocs" / "scans" / "truck" / "f150_blue_goose_uncropped"
)


def test_evaluate_directory_runs_pipeline_fn_over_every_image_and_scores_it():
    calls = []

    def fake_pipeline(image):
        calls.append(image)
        return {"gvwr_lb": 7100.0, "front_gawr_lb": None}

    expected = {"gvwr_lb": 7100.0, "front_gawr_lb": 3525.0}

    report = evaluate_directory(fake_pipeline, _IMAGES_DIR, expected)

    image_count = len(list(_IMAGES_DIR.glob("*.jpg")))
    assert len(report) == image_count
    assert len(calls) == image_count

    for row in report:
        assert set(row.keys()) >= {"image", "scores"}
        assert row["scores"]["gvwr_lb"]["correct"] is True
        assert row["scores"]["front_gawr_lb"]["correct"] is False
