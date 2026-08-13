"""Local-OCR reader for CAT Scale (or similar) weigh tickets.

Drop-in alternative to `hdttools.scale_ticket`: same function name,
signature, and return type (`ScaleTicketData`), but extracts the data with
Tesseract OCR + regex instead of the Claude API, so no API key or network
access is required.

Trade-off: this ticket layout is two-column (scale/location info on the
left, axle weights on the right), and plain OCR reading order can jumble
text across columns. The single-line labeled numeric fields (ticket/weigh
number, date, scale number, axle weights, gross weight, tractor/trailer #)
extract reliably. `location_name`/`location_address`/`city`/`state` are
best-effort and may need manual review.

Requires the Tesseract OCR engine to be installed separately (this only
installs the `pytesseract` Python wrapper). On Windows, install it via the
community builds at https://github.com/UB-Mannheim/tesseract/wiki (the
installer referenced by pytesseract's own docs), then either add it to
PATH or set `pytesseract.pytesseract.tesseract_cmd` to its full path.
"""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image

from .database import save_scale_ticket
from .models import ScaleTicketData
from .ocr_common import (
    ensure_tesseract_configured as _ensure_tesseract_configured,
    find_num as _find_num,
    find_str as _find_str,
    ocr_text as _ocr_text,
    open_image as _open_image,
    preprocess_image as _preprocess_image,
)

# file_picker/review_form (tkinter) are imported lazily inside
# read_scale_ticket() below, not here - this keeps _parse_fields() (used
# by the FastAPI/Streamlit frontends, which never call read_scale_ticket)
# free of a tkinter dependency that isn't always present on headless
# hosts (confirmed: Streamlit Community Cloud's Python build lacks it).


def _preprocess(image_path: Path) -> Image.Image:
    return _preprocess_image(_open_image(image_path))


def _parse_fields(raw_text: str) -> dict:
    flat = re.sub(r"[ \t]+", " ", raw_text)
    flat = re.sub(r"\s*\n\s*", " ", flat).strip()

    fields = {
        "ticket_number": _find_str(r"(\d{8,}).{0,40}?TICKET\s*NUMBER", flat),
        "weigh_number": _find_str(r"WEIGH\s*NUMBER.{0,30}?(\d{3,6})(?!\d)", flat),
        "date": _find_str(r"DATE:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})", flat),
        "time": _find_str(r"\b([0-2]?\d:[0-5]\d)\b", flat),
        "scale_number": _find_str(r"SC[A-Z]{2,5}:?\s{0,3}(\d{2,6})", flat),
        "steer_axle_lb": _find_num(r"STEER\s*AXLE\s*([\d,]+)\s*LB", flat),
        "drive_axle_lb": _find_num(r"DRIVE\s*AXLE\s*([\d,]+)\s*LB", flat),
        "trailer_axle_lb": _find_num(r"TRAILER\s*AXLE\s*([\d,]+)\s*LB", flat),
        "gross_weight_lb": _find_num(r"GROSS\s*WEI[GC]HT\s*([\d,]+)\s*LB", flat),
        "company": _find_str(r"COMPANY\s+(.{1,40}?)\s+TRACTOR\s*#?", flat),
        "commodity": _find_str(r"ARTICLE\s+WEIGHED\s+(.{1,60}?)\s+COMPANY\b", flat),
        "tractor_number": _find_str(r"TRACTOR\s*#?\s*(\S+)", flat),
        "trailer_number": _find_str(r"TRAILER\s*#\s*(\S+)", flat),
    }

    if fields["gross_weight_lb"] is None:
        # Every "___ LB" weight on a CAT Scale ticket appears in a fixed
        # order: steer, drive, trailer, then gross last. If the "GROSS
        # WEIGHT" label itself gets OCR-mangled, the last weight value in
        # document order is still reliably the gross weight.
        all_weights = re.findall(r"([\d,]+)\s*LB", flat, re.IGNORECASE)
        if all_weights:
            fields["gross_weight_lb"] = float(all_weights[-1].replace(",", ""))

    location_block = _find_str(
        r"LOCATION:?\s*(.{1,150}?)\s*(?:STEER\s*AXLE|\*?\s*GROSS\s*WEI[GC]HT)", flat
    )
    location_name = None
    state = None
    if location_block:
        words = location_block.split()
        if words and len(words[-1]) == 2 and words[-1].isalpha():
            state = words[-1].upper()
            words = words[:-1]
        location_name = " ".join(words) or None

    fields.update(location_name=location_name, location_address=None, city=None, state=state)
    return fields


def read_scale_ticket() -> ScaleTicketData | None:
    """Prompt the user to pick a weigh-ticket image, let them review and
    repair the OCR'd fields (accuracy is lower than the API version, so
    expect to fix more), save the result, and return it. Returns None if
    the user cancels the review instead of saving."""
    from .file_picker import select_image_file
    from .review_form import review_and_edit

    _ensure_tesseract_configured()
    image_path = select_image_file("Select a scale ticket image")

    image = _preprocess(image_path)
    text = _ocr_text(image)
    fields = _parse_fields(text)

    record = ScaleTicketData(source_image=str(image_path), **fields)

    reviewed = review_and_edit(record)
    if reviewed is None:
        return None

    save_scale_ticket(reviewed)
    return reviewed
