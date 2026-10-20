"""The cases the Claude vision External test runs, resolved from the shared file.

Standalone test infrastructure (like scripts/pass_pool.py), not application code. The cases
live in test-vectors/vision_external_cases.json, which the Worker's External test reads too
(workers/scan-proxy/src/external/visionCases.ts), so both sides look at the same photos. The
expected field values and known_ocr_limitations are read from the 'photos' section of
ExampleDocs/golden_fields.json and are not copied anywhere.
"""

from __future__ import annotations

import json
import mimetypes
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_DOCS = ROOT / "ExampleDocs"
CASES_FILE = ROOT / "test-vectors" / "vision_external_cases.json"
GOLDEN_FILE = EXAMPLE_DOCS / "golden_fields.json"


@dataclass(frozen=True)
class VisionCase:
    doc_type: str
    image: str
    golden: str
    fields: dict = field(compare=False)
    known_ocr_limitations: dict = field(compare=False, default_factory=dict)

    @property
    def image_path(self) -> Path:
        return EXAMPLE_DOCS / self.image

    @property
    def media_type(self) -> str:
        return mimetypes.guess_type(self.image)[0] or "image/jpeg"


def load_cases() -> list[VisionCase]:
    """Every case in the shared file, with its expected values from golden_fields.json.
    A case whose golden entry is missing raises KeyError naming it."""
    shared = json.loads(CASES_FILE.read_text(encoding="utf-8"))
    photos = json.loads(GOLDEN_FILE.read_text(encoding="utf-8"))["photos"]
    cases = []
    for raw in shared["cases"]:
        entry = photos[raw["golden"]]
        cases.append(
            VisionCase(
                doc_type=raw["doc_type"],
                image=raw["image"],
                golden=raw["golden"],
                fields=entry["fields"],
                known_ocr_limitations=entry.get("known_ocr_limitations", {}),
            )
        )
    return cases


def new_mismatches(case: VisionCase, extracted: dict) -> dict:
    """Fields whose extracted value differs from the golden value, other than the ones the
    golden entry documents in known_ocr_limitations: {field: (got, expected)}."""
    return {
        name: (extracted.get(name), expected)
        for name, expected in case.fields.items()
        if extracted.get(name) != expected and name not in case.known_ocr_limitations
    }
