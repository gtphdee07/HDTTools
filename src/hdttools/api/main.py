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

from .. import scale_ticket_ocr, trailer_tag_ocr, truck_tag_ocr
from ..ocr_common import ensure_tesseract_configured, ocr_text, preprocess_image
from .breakdown import compute_breakdown, verdict_for
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


async def _ocr_upload(file: UploadFile) -> str:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "Uploaded file must be an image.")
    ensure_tesseract_configured()
    data = await file.read()
    try:
        image = Image.open(io.BytesIO(data))
    except Exception as exc:
        raise HTTPException(400, "Could not read that file as an image.") from exc
    return ocr_text(preprocess_image(image))


@app.post("/api/extract/truck-tag", response_model=TruckTagOut)
async def extract_truck_tag(file: UploadFile):
    text = await _ocr_upload(file)
    return _dataclasses_to_dicts(truck_tag_ocr._parse_fields(text))


@app.post("/api/extract/trailer-tag", response_model=TrailerTagOut)
async def extract_trailer_tag(file: UploadFile):
    text = await _ocr_upload(file)
    return _dataclasses_to_dicts(trailer_tag_ocr._parse_fields(text))


@app.post("/api/extract/scale-ticket", response_model=ScaleTicketOut)
async def extract_scale_ticket(file: UploadFile):
    text = await _ocr_upload(file)
    return scale_ticket_ocr._parse_fields(text)


@app.post("/api/breakdown", response_model=BreakdownResponse)
def create_breakdown(payload: BreakdownRequest):
    items = compute_breakdown(payload.truck, payload.trailer, payload.scale)
    verdict_info = verdict_for(items)
    verdict = "fail" if verdict_info["headline"].startswith("Not") else "pass"
    return {
        "date": datetime.now(timezone.utc).strftime("%b %d, %Y"),
        "verdict": verdict,
        "breakdownItems": items,
        "verdictInfo": verdict_info,
    }
