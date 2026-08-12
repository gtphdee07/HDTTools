"""Reader for truck Safety Compliance Certification labels."""

from __future__ import annotations

from .database import save_truck_tag
from .models import TireSpec, TruckTagData
from .review_form import review_and_edit
from .vision_client import extract_via_claude, prompt_vehicle_name, select_image_file

_SYSTEM_PROMPT = (
    "You are reading a Ford-style Vehicle Safety Compliance Certification "
    "label for a truck, mounted on the door jamb. It lists separate Front "
    "and Rear GAWR values and separate front/rear tire and rim specs. "
    "Leave a field null if it is not present on the label."
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
        "front_gawr_kg": {"type": ["number", "null"]},
        "front_gawr_lb": {"type": ["number", "null"]},
        "rear_gawr_kg": {"type": ["number", "null"]},
        "rear_gawr_lb": {"type": ["number", "null"]},
        "front_tire": _TIRE_SCHEMA,
        "rear_tire": _TIRE_SCHEMA,
    },
    "required": [
        "manufacturer",
        "date",
        "vin",
        "vehicle_type",
        "gvwr_kg",
        "gvwr_lb",
        "front_gawr_kg",
        "front_gawr_lb",
        "rear_gawr_kg",
        "rear_gawr_lb",
        "front_tire",
        "rear_tire",
    ],
}


def read_truck_tag() -> TruckTagData | None:
    """Prompt the user to pick a truck compliance-label image and a vehicle
    name, let them review and repair the extracted fields, save the
    result, and return it. Returns None if the user cancels the review
    instead of saving."""
    image_path = select_image_file("Select a truck compliance label image")
    vehicle_name = prompt_vehicle_name()

    fields = extract_via_claude(
        image_path=image_path,
        system_prompt=_SYSTEM_PROMPT,
        tool_name="record_truck_tag",
        tool_description="Record the fields extracted from a truck compliance label.",
        schema=_SCHEMA,
    )

    front_tire = TireSpec(**fields.pop("front_tire"))
    rear_tire = TireSpec(**fields.pop("rear_tire"))

    record = TruckTagData(
        vehicle_name=vehicle_name,
        source_image=str(image_path),
        front_tire=front_tire,
        rear_tire=rear_tire,
        **fields,
    )

    reviewed = review_and_edit(record)
    if reviewed is None:
        return None

    save_truck_tag(reviewed)
    return reviewed
