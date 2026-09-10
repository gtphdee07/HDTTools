"""Shared helpers for picking an image file and extracting structured
data from it via the Claude vision API."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

import anthropic

from .file_picker import prompt_vehicle_name, select_image_file

__all__ = [
    "DEFAULT_MODEL",
    "extract_via_claude",
    "image_bytes_and_media_type",
    "prompt_vehicle_name",
    "select_image_file",
]

DEFAULT_MODEL = "claude-sonnet-5"


def image_bytes_and_media_type(image_path: Path) -> tuple[bytes, str]:
    """Reads an on-disk image and resolves its media type - the small
    local helper each interactive caller (truck_tag.py/trailer_tag.py/
    scale_ticket.py) uses at its own call site, so the
    `mimetypes.guess_type` line isn't repeated three times."""
    media_type = mimetypes.guess_type(image_path.name)[0] or "image/jpeg"
    return image_path.read_bytes(), media_type


def extract_via_claude(
    image_bytes: bytes,
    media_type: str,
    system_prompt: str,
    tool_name: str,
    tool_description: str,
    schema: dict,
    model: str = DEFAULT_MODEL,
) -> dict:
    """Send an image to Claude and return the tool-use input matching `schema`."""
    image_data = base64.standard_b64encode(image_bytes).decode("utf-8")

    client = anthropic.Anthropic()
    tool = {
        "name": tool_name,
        "description": tool_description,
        "input_schema": schema,
    }

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=system_prompt,
        tools=[tool],
        tool_choice={"type": "tool", "name": tool_name},
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": "Extract the requested fields from this image.",
                    },
                ],
            }
        ],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == tool_name:
            return block.input

    raise RuntimeError("Claude did not return the expected structured data.")
