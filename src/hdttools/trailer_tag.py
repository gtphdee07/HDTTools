"""Reader for trailer Safety Compliance Certification labels."""

from __future__ import annotations

from .database import save_trailer_tag
from .models import TireSpec, TrailerTagData
from .review_form import review_and_edit
from .vision_client import extract_via_claude, prompt_vehicle_name, select_image_file

_SYSTEM_PROMPT = (
    "You are reading a Vehicle Safety Compliance Certification label for a "
    "travel trailer / RV. It lists a single GAWR that applies to each axle "
    "(not separate front/rear values), and may list a UVW (unloaded vehicle "
    "weight). Leave a field null if it is not present on the label."
)

_TIRE_SCHEMA = {
    "type": "object",
    "properties": {
        "tire": {"type": ["string", "null"]},
        "rim": {"type": ["string", "null"]},
        "cold_pressure_kpa": {"type": ["number", "null"]},
        "cold_pressure_psi": {"type": ["number", "null"]},
        "dual": {"type": "boolean"},
    },
    "required": ["tire", "rim", "cold_pressure_kpa", "cold_pressure_psi", "dual"],
}

_SCHEMA = {
    "type": "object",
    "properties": {
        "manufacturer": {"type": ["string", "null"]},
        "date": {"type": ["string", "null"]},
        "vin": {"type": ["string", "null"]},
        "vehicle_type": {"type": ["string", "null"]},
        "gvwr_kg": {"type": ["number", "null"]},
        "gvwr_lb": {"type": ["number", "null"]},
        "gawr_per_axle_kg": {"type": ["number", "null"]},
        "gawr_per_axle_lb": {"type": ["number", "null"]},
        "uvw_kg": {"type": ["number", "null"]},
        "uvw_lb": {"type": ["number", "null"]},
        "tire": _TIRE_SCHEMA,
    },
    "required": [
        "manufacturer",
        "date",
        "vin",
        "vehicle_type",
        "gvwr_kg",
        "gvwr_lb",
        "gawr_per_axle_kg",
        "gawr_per_axle_lb",
        "uvw_kg",
        "uvw_lb",
        "tire",
    ],
}


def read_trailer_tag() -> TrailerTagData | None:
    """Prompt the user to pick a trailer compliance-label image and a
    vehicle name, let them review and repair the extracted fields, save
    the result, and return it. Returns None if the user cancels the
    review instead of saving."""
    image_path = select_image_file("Select a trailer compliance label image")
    vehicle_name = prompt_vehicle_name()

    fields = extract_via_claude(
        image_path=image_path,
        system_prompt=_SYSTEM_PROMPT,
        tool_name="record_trailer_tag",
        tool_description="Record the fields extracted from a trailer compliance label.",
        schema=_SCHEMA,
    )

    tire = TireSpec(**fields.pop("tire"))

    record = TrailerTagData(
        vehicle_name=vehicle_name,
        source_image=str(image_path),
        tire=tire,
        **fields,
    )

    reviewed = review_and_edit(record)
    if reviewed is None:
        return None

    save_trailer_tag(reviewed)
    return reviewed
