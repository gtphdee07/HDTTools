"""Reader for CAT Scale (or similar) weigh tickets."""

from __future__ import annotations

from .database import save_scale_ticket
from .models import ScaleTicketData
from .review_form import review_and_edit
from .vision_client import extract_via_claude, image_bytes_and_media_type, select_image_file

_SYSTEM_PROMPT = (
    "You are reading a truck weigh scale ticket (e.g. a CAT Scale ticket). "
    "Extract the fields exactly as printed. Weights are in pounds unless "
    "otherwise noted. Leave a field null if it is not present on the ticket."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "ticket_number": {"type": ["string", "null"]},
        "weigh_number": {"type": ["string", "null"]},
        "date": {"type": ["string", "null"]},
        "time": {"type": ["string", "null"]},
        "scale_number": {"type": ["string", "null"]},
        "location_name": {"type": ["string", "null"]},
        "location_address": {"type": ["string", "null"]},
        "city": {"type": ["string", "null"]},
        "state": {"type": ["string", "null"]},
        "steer_axle_lb": {"type": ["number", "null"]},
        "drive_axle_lb": {"type": ["number", "null"]},
        "trailer_axle_lb": {"type": ["number", "null"]},
        "gross_weight_lb": {"type": ["number", "null"]},
        "company": {"type": ["string", "null"]},
        "commodity": {"type": ["string", "null"]},
        "tractor_number": {"type": ["string", "null"]},
        "trailer_number": {"type": ["string", "null"]},
    },
    "required": [
        "ticket_number",
        "weigh_number",
        "date",
        "time",
        "scale_number",
        "location_name",
        "location_address",
        "city",
        "state",
        "steer_axle_lb",
        "drive_axle_lb",
        "trailer_axle_lb",
        "gross_weight_lb",
        "company",
        "commodity",
        "tractor_number",
        "trailer_number",
    ],
}


def extract_scale_ticket_fields(image_bytes: bytes, media_type: str) -> dict:
    """Headless, pure Claude-vision extraction for a weigh scale ticket -
    see truck_tag.extract_truck_tag_fields's docstring for the shape/
    rationale. No nested TireSpec to unpack here, so this is a thin
    pass-through, kept for the same reason (a headless caller with image
    bytes but no file/vehicle-name/review-form/database context)."""
    return extract_via_claude(
        image_bytes=image_bytes,
        media_type=media_type,
        system_prompt=_SYSTEM_PROMPT,
        tool_name="record_scale_ticket",
        tool_description="Record the fields extracted from a weigh scale ticket.",
        schema=_SCHEMA,
    )


def read_scale_ticket() -> ScaleTicketData | None:
    """Prompt the user to pick a weigh-ticket image, let them review and
    repair the extracted fields, save the result, and return it. Returns
    None if the user cancels the review instead of saving."""
    image_path = select_image_file("Select a scale ticket image")

    image_bytes, media_type = image_bytes_and_media_type(image_path)
    fields = extract_scale_ticket_fields(image_bytes, media_type)

    record = ScaleTicketData(source_image=str(image_path), **fields)

    reviewed = review_and_edit(record)
    if reviewed is None:
        return None

    save_scale_ticket(reviewed)
    return reviewed
