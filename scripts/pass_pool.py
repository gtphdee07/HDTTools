"""Resolves a random real-photo fixture for the constrained-random OCR
pass-pool design (FUTURE_CONSTRAINED_RANDOM_OCR_TESTING.md, roadmap item
#13 in NEXT_STEPS.md).

Standalone module (like scripts/coverage_lib.py), not part of the
`hdttools` app package -- this is test infrastructure, not application
code, so it stays out of src/.

Two ways a vehicle ends up in the pass-pool:

1. **Legacy, JSON-referencing** (today's `AddieTag.jpg`/`GooseTag.jpg`):
   ExampleDocs/golden_fields.json's "photos" section is one photo
   filename -> its fields + known_ocr_limitations; a "pass_pool" entry
   just lists which filenames belong to which vehicle, and this module
   resolves the filename back through "photos" -- no second, drift-prone
   copy of the field data. Kept as-is since other tests
   (test_real_photo_ocr_accuracy.py, test_streamlit_app.py) also
   reference these same two files at their current location.
2. **Directory-discovered, self-contained** (every vehicle added going
   forward): scripts/vehicle_discovery.py walks
   ExampleDocs/scans/<truck|trailer|scale>/<vehicle_slug>/ for a
   vehicle.json + sibling images -- see that module's docstring for the
   schema. A discovered vehicle carries its own "fields" directly, so
   there's no "photos" entry to reference at all.

Both shapes end up as plain dicts in golden["pass_pool"][doc_type], so
resolve_pass_pool_image treats them uniformly except for the one branch
below that tells them apart.
"""

import json
import random
from pathlib import Path

import vehicle_discovery

_EXAMPLE_DOCS = Path(__file__).resolve().parent.parent / "ExampleDocs"


def _load_golden() -> dict:
    golden = json.loads((_EXAMPLE_DOCS / "golden_fields.json").read_text(encoding="utf-8"))
    discovered = vehicle_discovery.discover_vehicles()
    for doc_type, vehicles in discovered["pass_pool"].items():
        golden.setdefault("pass_pool", {}).setdefault(doc_type, []).extend(vehicles)
    return golden


def registered_doc_types() -> list[str]:
    """doc_types with at least one pass-pool vehicle registered, from
    either golden_fields.json or directory discovery.
    """
    return [dt for dt in _load_golden().get("pass_pool", {}) if dt != "_readme"]


def resolve_pass_pool_image(doc_type: str, rng: random.Random | None = None) -> tuple[str, dict]:
    """Randomly picks one pass-pool image registered for `doc_type` and
    returns `(filename, photo_entry)`, where `photo_entry` is that
    image's fields + any known_ocr_limitations, resolved fresh every
    call.
    """
    golden = _load_golden()
    vehicles = golden.get("pass_pool", {}).get(doc_type)
    if not vehicles:
        raise ValueError(f"no pass-pool vehicles registered for doc_type {doc_type!r}")

    rng = rng if rng is not None else random.Random()
    vehicle = rng.choice(vehicles)
    filename = rng.choice(vehicle["images"])

    if "fields" in vehicle:
        photo = {"doc_type": doc_type, "fields": vehicle["fields"]}
        if "known_ocr_limitations" in vehicle:
            photo["known_ocr_limitations"] = vehicle["known_ocr_limitations"]
        return filename, photo

    return filename, golden["photos"][filename]
