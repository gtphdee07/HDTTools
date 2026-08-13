"""Local-OCR reader for trailer Safety Compliance Certification labels.

Drop-in alternative to `hdttools.trailer_tag`: same function name,
signature, and return type (`TrailerTagData`), but extracts the data with
Tesseract OCR + regex instead of the Claude API, so no API key or network
access is required.

Trade-off: unlike the CAT Scale ticket's fixed layout, compliance labels
vary by manufacturer, and RV labels are often bilingual (English/French,
per Canadian requirements) as seen in `ExampleDocs/GooseTag.jpg`. The
regexes below tolerate the French text interleaved between English labels
and values (e.g. "GVWR / PNBV ... KG (... LB)") without trying to parse it.
`manufacturer`/`gvwr_lb`/`gawr_per_axle_lb`/`uvw_lb` (the fields the web
review step actually shows) extract reliably from a clean photo; VIN, tire
spec, and the dual-tire flag are best-effort and may need manual review.

Requires the Tesseract OCR engine to be installed separately — see
`hdttools.scale_ticket_ocr` for setup notes.
"""

from __future__ import annotations

import re

from .database import save_trailer_tag
from .file_picker import prompt_vehicle_name, select_image_file
from .models import TireSpec, TrailerTagData
from .ocr_common import (
    ensure_tesseract_configured as _ensure_tesseract_configured,
    find_str as _find_str,
    ocr_text as _ocr_text,
    open_image as _open_image,
    preprocess_image as _preprocess_image,
)
from .review_form import review_and_edit


def _preprocess(image_path):
    return _preprocess_image(_open_image(image_path))


def _kg_lb(label_pattern: str, text: str) -> tuple[float | None, float | None]:
    # "LB" is tolerant of common OCR digit/letter confusion (see the same
    # note in truck_tag_ocr._kg_lb).
    match = re.search(rf"{label_pattern}.*?([\d,]+)\s*KG\s*\(?\s*([\d,]+)\s*[L1I][B8]", text, re.IGNORECASE)
    if not match:
        return None, None
    return float(match.group(1).replace(",", "")), float(match.group(2).replace(",", ""))


def _parse_fields(raw_text: str) -> dict:
    flat = re.sub(r"[ \t]+", " ", raw_text)
    flat = re.sub(r"\s*\n\s*", " ", flat).strip()
    flat_no_dots = flat.replace(".", "")

    gvwr_kg, gvwr_lb = _kg_lb(r"\bGVWR\b", flat)
    gawr_kg, gawr_lb = _kg_lb(r"GAWR.*?EACH\s*AXLE", flat)
    uvw_kg, uvw_lb = _kg_lb(r"\bUVW\b", flat)

    tire = _find_str(r"TIRE\S*\s+(\S+)\s+RIM", flat)
    rim = _find_str(r"RIM\S*\s+(.+?)\s+COLD", flat)
    pressure = re.search(r"COLD.*?([\d,]+)\s*KPA\s*\(?\s*([\d,]+)\s*PSI", flat, re.IGNORECASE)
    kpa = float(pressure.group(1).replace(",", "")) if pressure else None
    psi = float(pressure.group(2).replace(",", "")) if pressure else None
    dual = bool(re.search(r"\bDUAL\b", flat, re.IGNORECASE))

    manufacturer = _find_str(
        r"(?:MANUFACTURED\s*BY|MFD\.?\s*BY)[^:]{0,40}:\s*(.+?)\s+DATE", flat
    ) or _find_str(r"(?:MANUFACTURED\s*BY|MFD\.?\s*BY)\s+(.+?)\s+DATE", flat)

    return {
        "manufacturer": manufacturer,
        "date": _find_str(r"DATE:?\s*(\d{1,2}/\d{2,4})", flat),
        "vin": _find_str(r"VIN(?:/\S+)?:?\s*([A-Z0-9]{11,17})", flat_no_dots),
        "vehicle_type": _find_str(r"\bTYPE(?:/\S+)?:?\s*(\S+)", flat),
        "gvwr_kg": gvwr_kg,
        "gvwr_lb": gvwr_lb,
        "gawr_per_axle_kg": gawr_kg,
        "gawr_per_axle_lb": gawr_lb,
        "uvw_kg": uvw_kg,
        "uvw_lb": uvw_lb,
        "tire": TireSpec(tire=tire, rim=rim, cold_pressure_kpa=kpa, cold_pressure_psi=psi, dual=dual),
    }


def read_trailer_tag_ocr() -> TrailerTagData | None:
    """Prompt the user to pick a trailer compliance-label image and a
    vehicle name, let them review and repair the OCR'd fields (accuracy is
    lower than the API version, so expect to fix more), save the result,
    and return it. Returns None if the user cancels the review instead of
    saving."""
    _ensure_tesseract_configured()
    image_path = select_image_file("Select a trailer compliance label image")
    vehicle_name = prompt_vehicle_name()

    image = _preprocess(image_path)
    text = _ocr_text(image)
    fields = _parse_fields(text)

    record = TrailerTagData(vehicle_name=vehicle_name, source_image=str(image_path), **fields)

    reviewed = review_and_edit(record)
    if reviewed is None:
        return None

    save_trailer_tag(reviewed)
    return reviewed
