from pathlib import Path

from hdttools.ocr_common import find_num, find_str


def parse_spec_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    return {
        "manufacturer": find_str(r"MFD\.?\s*BY\s+(.+)", text),
        "gvwr_lb": find_num(r"GVWR:?\s*([\d,]+)\s*LB", text),
        "front_gawr_lb": find_num(r"GAWR:?\s*([\d,]+)\s*LB", text),
        "rear_gawr_lb": find_num(r"REAR\s*GAWR:?\s*([\d,]+)", text),
    }


def parse_gm_spec_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    return {
        "vin": find_str(r"VIN:?\s*([A-HJ-NPR-Z0-9]{17})", text),
        "gvwr_lb": find_num(r"GVWR:?\s*([\d,]+)\s*LBS", text),
        "gcwr_lb": find_num(r"GCWR:?\s*([\d,]+)\s*LBS", text),
        "rgawr_lb": find_num(r"RGAWR:?\s*([\d,]+)\s*LBS", text),
        "curb_weight_lb": find_num(r"CURB\s*WEIGHT:?\s*([\d,]+)\s*LBS", text),
        "max_payload_lb": find_num(r"MAX\s*PAYLOAD:?\s*([\d,]+)\s*LBS", text),
        "conventional_twr_lb": find_num(r"CONVENTIONAL\s*TWR:?\s*([\d,]+)\s*LBS", text),
        "max_tongue_weight_conventional_lb": find_num(
            r"MAX\s*TONGUE\s*WEIGHT\s*\(CONVENTIONAL\):?\s*([\d,]+)\s*LBS", text
        ),
        "gooseneck_twr_lb": find_num(r"GOOSENECK\s*TWR:?\s*([\d,]+)\s*LBS", text),
        "max_tongue_weight_gooseneck_lb": find_num(
            r"MAX\s*TONGUE\s*WEIGHT\s*\(GOOSENECK\):?\s*([\d,]+)\s*LBS", text
        ),
    }
