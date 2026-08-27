import re
from pathlib import Path


def _normalize(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def score_image(extracted: dict, expected: dict) -> dict:
    scores = {}
    for field, expected_value in expected.items():
        actual_value = extracted.get(field)
        if isinstance(expected_value, str):
            correct = isinstance(actual_value, str) and _normalize(actual_value) == _normalize(expected_value)
        else:
            correct = actual_value == expected_value
        scores[field] = {"expected": expected_value, "actual": actual_value, "correct": correct}
    return scores


def evaluate_directory(pipeline_fn, images_dir: Path, expected: dict) -> list[dict]:
    from PIL import Image

    report = []
    for image_path in sorted(images_dir.glob("*.jpg")):
        image = Image.open(image_path)
        result = pipeline_fn(image)
        report.append({"image": image_path.name, "scores": score_image(result, expected)})
    return report
