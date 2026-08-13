"""Local-OCR reader for truck Safety Compliance Certification labels.

Drop-in alternative to `hdttools.truck_tag`: same function name, signature,
and return type (`TruckTagData`), but extracts the data with Tesseract OCR
+ regex instead of the Claude API, so no API key or network access is
required.

Trade-off: unlike the CAT Scale ticket's fixed layout, compliance labels
vary by manufacturer. This targets the common Ford-style two-column layout
(front spec on the left, rear spec on the right, per row) as seen in
`ExampleDocs/AddieTag.jpg`. `manufacturer`/`gvwr_lb`/`front_gawr_lb`/
`rear_gawr_lb` (the fields the web review step actually shows) extract
reliably from a clean photo; VIN, tire spec, and the dual-tire flag are
best-effort and may need manual review.

Requires the Tesseract OCR engine to be installed separately — see
`hdttools.scale_ticket_ocr` for setup notes.
"""

from __future__ import annotations

import re

from .database import save_truck_tag
from .file_picker import prompt_vehicle_name, select_image_file
from .models import TireSpec, TruckTagData
from .ocr_common import (
    ensure_tesseract_configured as _ensure_tesseract_configured,
    find_num as _find_num,
    find_str as _find_str,
    ocr_text as _ocr_text,
    open_image as _open_image,
    preprocess_image as _preprocess_image,
)
from .review_form import review_and_edit


def _preprocess(image_path):
    return _preprocess_image(_open_image(image_path))


def _kg_lb(label_pattern: str, text: str) -> tuple[float | None, float | None]:
    # "LB" is tolerant of common OCR digit/letter confusion on tightly-kerned
    # labels (e.g. "9900 LB)" misread as "99001B)" — L→1, B→8 are frequent).
    match = re.search(rf"{label_pattern}:?\s*([\d,]+)\s*KG\s*\(?\s*([\d,]+)\s*[L1I][B8]", text, re.IGNORECASE)
    if not match:
        return None, None
    return float(match.group(1).replace(",", "")), float(match.group(2).replace(",", ""))


def _tire_specs(flat: str) -> tuple[TireSpec, TireSpec]:
    tires = re.findall(r"WITH\s+(.+?)\s+TIRES", flat, re.IGNORECASE)
    rims = re.findall(r"(\S+)\s*RIMS", flat, re.IGNORECASE)
    pressures = list(re.finditer(r"AT\s*([\d,]+)\s*KPA\s*/?\s*([\d,]+)\s*PSI", flat, re.IGNORECASE))
    duals = [m.start() for m in re.finditer(r"\bDUAL\b", flat, re.IGNORECASE)]

    def spec(i: int) -> TireSpec:
        tire = tires[i] if i < len(tires) else (tires[0] if tires else None)
        rim = rims[i] if i < len(rims) else (rims[0] if rims else None)
        kpa = psi = None
        is_dual = False
        if i < len(pressures):
            m = pressures[i]
            kpa = float(m.group(1).replace(",", ""))
            psi = float(m.group(2).replace(",", ""))
            window_end = pressures[i + 1].start() if i + 1 < len(pressures) else len(flat)
            is_dual = any(m.end() <= pos < window_end for pos in duals)
        return TireSpec(tire=tire, rim=rim, cold_pressure_kpa=kpa, cold_pressure_psi=psi, dual=is_dual)

    return spec(0), spec(1)


def _parse_fields(raw_text: str) -> dict:
    flat = re.sub(r"[ \t]+", " ", raw_text)
    flat = re.sub(r"\s*\n\s*", " ", flat).strip()

    gvwr_kg, gvwr_lb = _kg_lb(r"GVWR", flat)
    front_gawr_kg, front_gawr_lb = _kg_lb(r"FRONT\s*GAWR", flat)
    rear_gawr_kg, rear_gawr_lb = _kg_lb(r"REAR\s*GAWR", flat)
    front_tire, rear_tire = _tire_specs(flat)

    return {
        "manufacturer": _find_str(r"(?:MFD\.?\s*BY|MANUFACTURED\s*BY)\s+(.+?)\s+DATE", flat),
        "date": _find_str(r"DATE:?\s*(\d{1,2}/\d{2,4})", flat),
        "vin": _find_str(r"\bVIN:?\s*([A-Z0-9]{11,17})\b", flat),
        "vehicle_type": _find_str(r"\bTYPE:?\s*(\w+)", flat),
        "gvwr_kg": gvwr_kg,
        "gvwr_lb": gvwr_lb,
        "front_gawr_kg": front_gawr_kg,
        "front_gawr_lb": front_gawr_lb,
        "rear_gawr_kg": rear_gawr_kg,
        "rear_gawr_lb": rear_gawr_lb,
        "front_tire": front_tire,
        "rear_tire": rear_tire,
    }


def read_truck_tag_ocr() -> TruckTagData | None:
    """Prompt the user to pick a truck compliance-label image and a vehicle
    name, let them review and repair the OCR'd fields (accuracy is lower
    than the API version, so expect to fix more), save the result, and
    return it. Returns None if the user cancels the review instead of
    saving."""
    _ensure_tesseract_configured()
    image_path = select_image_file("Select a truck compliance label image")
    vehicle_name = prompt_vehicle_name()

    image = _preprocess(image_path)
    text = _ocr_text(image)
    fields = _parse_fields(text)

    record = TruckTagData(vehicle_name=vehicle_name, source_image=str(image_path), **fields)

    reviewed = review_and_edit(record)
    if reviewed is None:
        return None

    save_truck_tag(reviewed)
    return reviewed
