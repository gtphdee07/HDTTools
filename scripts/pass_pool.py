"""Resolves a random real-photo fixture for the constrained-random OCR
pass-pool design (FUTURE_CONSTRAINED_RANDOM_OCR_TESTING.md, roadmap item
#13 in NEXT_STEPS.md).

Standalone module (like scripts/coverage_lib.py), not part of the
`hdttools` app package -- this is test infrastructure, not application
code, so it stays out of src/.

ExampleDocs/golden_fields.json's existing "photos" section is one photo
filename -> its fields + known_ocr_limitations. A pass-pool groups those
same filenames by real vehicle instead, under a new "pass_pool" section,
so a test can pick one image at random per doc_type (truck_tag,
trailer_tag, ...) and still resolve the exact golden truth for whichever
image got picked -- without a second, drift-prone copy of the field
data. See golden_fields.json's own "pass_pool" entry for the schema and
its rationale.
"""

import json
import random
from pathlib import Path

_EXAMPLE_DOCS = Path(__file__).resolve().parent.parent / "ExampleDocs"


def _load_golden() -> dict:
    return json.loads((_EXAMPLE_DOCS / "golden_fields.json").read_text(encoding="utf-8"))


def resolve_pass_pool_image(doc_type: str, rng: random.Random | None = None) -> tuple[str, dict]:
    """Randomly picks one pass-pool image registered for `doc_type` and
    returns `(filename, photo_entry)`, where `photo_entry` is that
    filename's own entry from golden_fields.json's "photos" section
    (fields + any known_ocr_limitations), resolved fresh every call.
    """
    golden = _load_golden()
    vehicles = golden.get("pass_pool", {}).get(doc_type)
    if not vehicles:
        raise ValueError(f"no pass-pool vehicles registered for doc_type {doc_type!r}")

    rng = rng if rng is not None else random.Random()
    vehicle = rng.choice(vehicles)
    filename = rng.choice(vehicle["images"])
    return filename, golden["photos"][filename]
