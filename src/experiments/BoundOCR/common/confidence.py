import pytesseract
from pytesseract import Output

DEFAULT_CONFIDENCE_THRESHOLD = 50.0


def word_confidences(image) -> list[float]:
    data = pytesseract.image_to_data(image, output_type=Output.DICT)
    # Tesseract's own "no detection" sentinel is -1, not a low real score.
    return [float(c) for c in data["conf"] if float(c) >= 0]


def _is_plausible_weight(value) -> bool:
    return isinstance(value, (int, float)) and 0 < value < 50000


_WEIGHT_FIELD_NAMES = [
    "gvwr_lb", "gvwr_kg",
    "front_gawr_lb", "front_gawr_kg",
    "rear_gawr_lb", "rear_gawr_kg",
    "gcwr_lb", "gcwr_kg",
    "rgawr_lb", "rgawr_kg",
    "curb_weight_lb", "curb_weight_kg",
    "max_payload_lb", "max_payload_kg",
    "conventional_twr_lb", "conventional_twr_kg",
    "gooseneck_twr_lb", "gooseneck_twr_kg",
    "max_tongue_weight_conventional_lb", "max_tongue_weight_conventional_kg",
    "max_tongue_weight_gooseneck_lb", "max_tongue_weight_gooseneck_kg",
]

FIELD_VALIDATORS = {name: _is_plausible_weight for name in _WEIGHT_FIELD_NAMES}
FIELD_VALIDATORS["manufacturer"] = (
    lambda v: isinstance(v, str) and v.strip() != "" and not any(c.isdigit() for c in v)
)


def gate_fields(fields: dict, overall_confidence: float,
                threshold: float = DEFAULT_CONFIDENCE_THRESHOLD) -> dict:
    if overall_confidence < threshold:
        return {key: None for key in fields}

    gated = {}
    for key, value in fields.items():
        validator = FIELD_VALIDATORS.get(key)
        gated[key] = value if (value is None or validator is None or validator(value)) else None
    return gated
