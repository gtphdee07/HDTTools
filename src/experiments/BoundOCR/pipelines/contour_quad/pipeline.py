from experiments.BoundOCR.common.confidence import gate_fields, word_confidences
from experiments.BoundOCR.common.geometry import pad_quad, warp_to_quad
from experiments.BoundOCR.pipelines.contour_quad.contour_locate import locate_label
from hdttools.ocr_common import ocr_text, preprocess_image
from hdttools.truck_tag_ocr import _parse_fields

_NOT_FOUND_RESULT = {
    "manufacturer": None,
    "gvwr_lb": None,
    "front_gawr_lb": None,
    "rear_gawr_lb": None,
    "label_found": False,
    "overall_confidence": 0.0,
    "box": None,
}


def extract_from_box(image, box, field_parser=_parse_fields) -> dict:
    crop = warp_to_quad(image, pad_quad(box))
    preprocessed = preprocess_image(crop)

    confidences = word_confidences(preprocessed)
    overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    fields = field_parser(ocr_text(preprocessed))
    gated = gate_fields(fields, overall_confidence)

    return {
        **gated,
        "label_found": True,
        "overall_confidence": overall_confidence,
        "box": box,
    }


def detect_and_extract(image, field_parser=_parse_fields) -> dict:
    box = locate_label(image)
    if box is None:
        return dict(_NOT_FOUND_RESULT)
    return extract_from_box(image, box, field_parser=field_parser)
