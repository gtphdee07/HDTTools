"""FastAPI app: image extraction + rig/check persistence for the RigCheck
web frontend. Run locally with:

    uv run uvicorn hdttools.api.main:app --reload --port 8000
"""

from __future__ import annotations

import dataclasses
import io
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

from .. import scale_ticket_ocr, trailer_tag_ocr, truck_tag_ocr
from ..database import DEFAULT_DB_PATH
from ..ocr_common import ensure_tesseract_configured, ocr_text, preprocess_image
from . import store
from .breakdown import compute_breakdown, verdict_for
from .schemas import (
    CheckCreateRequest,
    CheckCreateResponse,
    CheckOut,
    RigOut,
    ScaleTicketOut,
    TrailerTagOut,
    TruckTagOut,
)


def get_db_path() -> Path:
    return DEFAULT_DB_PATH


def get_initialized_db_path(db_path: Path = Depends(get_db_path)) -> Path:
    """Ensures the rigs/checks tables (and seed rig) exist for whichever
    db_path was resolved — runs on every request rather than only at
    startup so test overrides of `get_db_path` still get initialized."""
    store.init_db(db_path)
    return db_path


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


@app.get("/api/rigs", response_model=list[RigOut])
def get_rigs(db_path: Path = Depends(get_initialized_db_path)):
    return store.list_rigs(db_path)


@app.get("/api/checks", response_model=list[CheckOut])
def get_checks(db_path: Path = Depends(get_initialized_db_path)):
    return store.list_checks(db_path)


@app.post("/api/checks", response_model=CheckCreateResponse)
def create_check(payload: CheckCreateRequest, db_path: Path = Depends(get_initialized_db_path)):
    rig = store.get_rig(payload.rig_id, db_path)
    if rig is None:
        raise HTTPException(404, f"No rig with id {payload.rig_id}.")

    items = compute_breakdown(payload.truck, payload.trailer, payload.scale)
    verdict_info = verdict_for(items)
    verdict = "fail" if verdict_info["headline"].startswith("Not") else "pass"

    saved = store.save_check(
        rig_id=payload.rig_id,
        truck_name=rig["truck_name"],
        trailer_name=rig["trailer_name"],
        verdict=verdict,
        breakdown=items,
        db_path=db_path,
    )
    return {
        "id": saved["id"],
        "date": saved["date"],
        "verdict": verdict,
        "breakdownItems": items,
        "verdictInfo": verdict_info,
    }
