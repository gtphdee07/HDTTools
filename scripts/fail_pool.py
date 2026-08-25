"""Resolves a random known-illegible real photo for the fail-pool piece
of the constrained-random OCR testing design
(FUTURE_CONSTRAINED_RANDOM_OCR_TESTING.md, roadmap item #13 in
NEXT_STEPS.md).

Standalone module (like scripts/pass_pool.py / scripts/coverage_lib.py),
not part of the `hdttools` app package -- this is test infrastructure,
not application code, so it stays out of src/.

Every fail-pool vehicle is self-contained (unlike scripts/pass_pool.py's
legacy JSON-referencing shape): each vehicle entry carries its own
"expected_none_fields" directly, whether it's defined in
golden_fields.json or discovered from ExampleDocs/scans/ by
scripts/vehicle_discovery.py (see that module's docstring for the
vehicle.json schema) - there's no "photos" entry to reference either
way, since these images are, by definition, not registered there.
"""

import json
import random
from pathlib import Path

import vehicle_discovery

_EXAMPLE_DOCS = Path(__file__).resolve().parent.parent / "ExampleDocs"


def _load_golden() -> dict:
    golden = json.loads((_EXAMPLE_DOCS / "golden_fields.json").read_text(encoding="utf-8"))
    discovered = vehicle_discovery.discover_vehicles()
    for doc_type, vehicles in discovered["fail_pool"].items():
        golden.setdefault("fail_pool", {}).setdefault(doc_type, []).extend(vehicles)
    return golden


def registered_doc_types() -> list[str]:
    """doc_types with at least one fail-pool vehicle registered, from
    either golden_fields.json or directory discovery.
    """
    return [dt for dt in _load_golden().get("fail_pool", {}) if dt != "_readme"]


def resolve_fail_pool_image(doc_type: str, rng: random.Random | None = None) -> tuple[str, dict]:
    """Randomly picks one fail-pool image registered for `doc_type` and
    returns `(filename, vehicle_entry)`, where `vehicle_entry` is that
    image's vehicle group from golden_fields.json's "fail_pool" section
    (including its "expected_none_fields" failure signature).
    """
    golden = _load_golden()
    vehicles = golden.get("fail_pool", {}).get(doc_type)
    if not vehicles:
        raise ValueError(f"no fail-pool vehicles registered for doc_type {doc_type!r}")

    rng = rng if rng is not None else random.Random()
    vehicle = rng.choice(vehicles)
    filename = rng.choice(vehicle["images"])
    return filename, vehicle
