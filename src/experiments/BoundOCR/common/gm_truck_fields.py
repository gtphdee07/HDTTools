import re

_KG_LB_TAIL = r"\W{0,4}([\d,]+)\s*KG\s*\W{0,3}([\d,]+)\s*[L1I][B8]S?"


def _kg_lb(label_pattern: str, text: str) -> tuple[float | None, float | None]:
    match = re.search(label_pattern + _KG_LB_TAIL, text, re.IGNORECASE)
    if not match:
        return None, None
    return float(match.group(1).replace(",", "")), float(match.group(2).replace(",", ""))


def parse_gm_fields(text: str) -> dict:
    flat = re.sub(r"[ \t]+", " ", text)
    flat = re.sub(r"\s*\n\s*", " ", flat).strip()

    gvwr_kg, gvwr_lb = _kg_lb(r"GVWR", flat)
    gcwr_kg, gcwr_lb = _kg_lb(r"GCWR", flat)
    rgawr_kg, rgawr_lb = _kg_lb(r"RGAWR", flat)
    curb_weight_kg, curb_weight_lb = _kg_lb(r"CURB\s*WEIGHT", flat)
    max_payload_kg, max_payload_lb = _kg_lb(r"MAX\s*PAYLOAD", flat)
    conventional_twr_kg, conventional_twr_lb = _kg_lb(r"CONVENTIONAL\s*TWR", flat)
    gooseneck_twr_kg, gooseneck_twr_lb = _kg_lb(r"GOOSENECK\s*TWR", flat)

    tongue_matches = list(
        re.finditer(r"MAX\s*TONGUE\s*WEIGHT" + _KG_LB_TAIL, flat, re.IGNORECASE)
    )

    def tongue(index: int) -> tuple[float | None, float | None]:
        if index < len(tongue_matches):
            match = tongue_matches[index]
            return float(match.group(1).replace(",", "")), float(match.group(2).replace(",", ""))
        return None, None

    max_tongue_weight_conventional_kg, max_tongue_weight_conventional_lb = tongue(0)
    max_tongue_weight_gooseneck_kg, max_tongue_weight_gooseneck_lb = tongue(1)

    vin_match = re.search(r"\b([A-HJ-NPR-Z0-9]{17})\b", flat, re.IGNORECASE)
    vin = vin_match.group(1) if vin_match else None

    return {
        "vin": vin,
        "gvwr_kg": gvwr_kg,
        "gvwr_lb": gvwr_lb,
        "gcwr_kg": gcwr_kg,
        "gcwr_lb": gcwr_lb,
        "rgawr_kg": rgawr_kg,
        "rgawr_lb": rgawr_lb,
        "curb_weight_kg": curb_weight_kg,
        "curb_weight_lb": curb_weight_lb,
        "max_payload_kg": max_payload_kg,
        "max_payload_lb": max_payload_lb,
        "conventional_twr_kg": conventional_twr_kg,
        "conventional_twr_lb": conventional_twr_lb,
        "gooseneck_twr_kg": gooseneck_twr_kg,
        "gooseneck_twr_lb": gooseneck_twr_lb,
        "max_tongue_weight_conventional_kg": max_tongue_weight_conventional_kg,
        "max_tongue_weight_conventional_lb": max_tongue_weight_conventional_lb,
        "max_tongue_weight_gooseneck_kg": max_tongue_weight_gooseneck_kg,
        "max_tongue_weight_gooseneck_lb": max_tongue_weight_gooseneck_lb,
    }
