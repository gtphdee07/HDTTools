"""FastAPI app: image extraction + weight breakdown computation for the
RigCheck web frontend. Stateless — no persistence, each platform (web,
Streamlit, Android) is self-contained and keeps its own recent-rigs/
history state locally. Run locally with:

    uv run uvicorn hdttools.api.main:app --reload --port 8000
"""

from __future__ import annotations

import dataclasses
import io
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

from .. import scale_ticket, scale_ticket_ocr, trailer_tag, trailer_tag_ocr, truck_tag, truck_tag_ocr
from ..ocr_common import ensure_tesseract_configured, get_ocr_backend, ocr_text, preprocess_image
from .breakdown import DEFAULT_PIN_WEIGHT_PCT, compute_breakdown, verdict_for
from .schemas import (
    BreakdownRequest,
    BreakdownResponse,
    ScaleTicketOut,
    TrailerTagOut,
    TruckTagOut,
)

app = FastAPI(title="RigCheck API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _dataclasses_to_dicts(fields: dict[str, Any]) -> dict[str, Any]:
    return {
        key: (dataclasses.asdict(value) if dataclasses.is_dataclass(value) else value)
        for key, value in fields.items()
    }


def _require_image_upload(file: UploadFile) -> None:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "Uploaded file must be an image.")


async def _ocr_upload(file: UploadFile) -> str:
    _require_image_upload(file)
    ensure_tesseract_configured()
    data = await file.read()
    try:
        image = Image.open(io.BytesIO(data))
    except Exception as exc:
        raise HTTPException(400, "Could not read that file as an image.") from exc
    return ocr_text(preprocess_image(image))


# Per-doc-type dispatch (mirroring streamlit_app/app.py's own _PARSERS
# dict) for the two OCR backends get_ocr_backend() can select between.
# Values are (module, attribute-name) pairs rather than the bound
# function objects themselves, resolved via getattr() at call time - so
# a test's monkeypatch.setattr(main.truck_tag_ocr, "_parse_fields", ...)
# (or the matching Claude-side attribute) still takes effect, the same
# way the original three route bodies' direct `truck_tag_ocr._parse_fields(text)`
# attribute access already did.
_TESSERACT_PARSERS = {
    "truck-tag": (truck_tag_ocr, "_parse_fields"),
    "trailer-tag": (trailer_tag_ocr, "_parse_fields"),
    "scale-ticket": (scale_ticket_ocr, "_parse_fields"),
}
_CLAUDE_EXTRACTORS = {
    "truck-tag": (truck_tag, "extract_truck_tag_fields"),
    "trailer-tag": (trailer_tag, "extract_trailer_tag_fields"),
    "scale-ticket": (scale_ticket, "extract_scale_ticket_fields"),
}


async def _extract_fields(doc_type: str, file: UploadFile) -> dict:
    """Dispatches to the Tesseract or Claude-vision path per
    get_ocr_backend(), returning the same fields-dict shape (nested
    TireSpec objects, not yet converted to plain dicts) either way."""
    if get_ocr_backend() == "tesseract":
        text = await _ocr_upload(file)
        module, attr = _TESSERACT_PARSERS[doc_type]
        return getattr(module, attr)(text)

    _require_image_upload(file)
    data = await file.read()
    module, attr = _CLAUDE_EXTRACTORS[doc_type]
    try:
        return getattr(module, attr)(data, file.content_type)
    except Exception as exc:
        # Distinct from _require_image_upload's 400 above - this is an
        # upstream-API failure (Claude vision itself), not a bad upload.
        raise HTTPException(502, "Claude vision extraction failed.") from exc


@app.post("/api/extract/truck-tag", response_model=TruckTagOut)
async def extract_truck_tag(file: UploadFile):
    fields = await _extract_fields("truck-tag", file)
    return _dataclasses_to_dicts(fields)


@app.post("/api/extract/trailer-tag", response_model=TrailerTagOut)
async def extract_trailer_tag(file: UploadFile):
    fields = await _extract_fields("trailer-tag", file)
    return _dataclasses_to_dicts(fields)


@app.post("/api/extract/scale-ticket", response_model=ScaleTicketOut)
async def extract_scale_ticket(file: UploadFile):
    fields = await _extract_fields("scale-ticket", file)
    return _dataclasses_to_dicts(fields)


@app.post("/api/breakdown", response_model=BreakdownResponse)
def create_breakdown(payload: BreakdownRequest):
    pin_weight_pct = payload.pin_weight_pct if payload.pin_weight_pct is not None else DEFAULT_PIN_WEIGHT_PCT
    items = compute_breakdown(payload.truck, payload.trailer, payload.scale, pin_weight_pct)
    verdict_info = verdict_for(items)
    return {
        "date": datetime.now(timezone.utc).strftime("%b %d, %Y"),
        "verdict": verdict_info["status"],
        "breakdownItems": items,
        "verdictInfo": verdict_info,
    }
