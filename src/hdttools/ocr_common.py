"""Shared, dependency-light helpers for Tesseract-based document readers.

Split out of `scale_ticket_ocr` so `truck_tag_ocr` and `trailer_tag_ocr`
(and the web API, which OCRs in-memory uploads rather than files on disk)
can reuse the same Tesseract setup, image preprocessing, and regex
extraction helpers without duplicating them.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytesseract
from PIL import Image, ImageOps

_TESSERACT_CANDIDATES = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    "/opt/homebrew/bin/tesseract",
    "/usr/local/bin/tesseract",
    "/usr/bin/tesseract",
]


def ensure_tesseract_configured() -> None:
    configured = pytesseract.pytesseract.tesseract_cmd
    if shutil.which(configured) or Path(configured).exists():
        return
    for candidate in _TESSERACT_CANDIDATES:
        if Path(candidate).exists():
            pytesseract.pytesseract.tesseract_cmd = candidate
            return
    raise RuntimeError(
        "Tesseract OCR engine was not found. Install it (Windows builds: "
        "https://github.com/UB-Mannheim/tesseract/wiki) and either add it "
        "to PATH or set pytesseract.pytesseract.tesseract_cmd to its full "
        "path before calling the reader function."
    )


def open_image(image_path: Path) -> Image.Image:
    return Image.open(image_path)


def preprocess_image(image: Image.Image) -> Image.Image:
    image = image.convert("L")
    image = ImageOps.autocontrast(image)
    if image.width < 1600:
        scale = 1600 / image.width
        new_size = (int(image.width * scale), int(image.height * scale))
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    return image


def ocr_text(image: Image.Image) -> str:
    return pytesseract.image_to_string(image, config="--psm 6")


def find_str(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


def find_num(pattern: str, text: str) -> float | None:
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    return float(match.group(1).replace(",", ""))
