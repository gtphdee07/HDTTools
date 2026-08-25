"""Resolves a random known-illegible real photo for the fail-pool piece
of the constrained-random OCR testing design
(FUTURE_CONSTRAINED_RANDOM_OCR_TESTING.md, roadmap item #13 in
NEXT_STEPS.md).

Standalone module (like scripts/pass_pool.py / scripts/coverage_lib.py),
not part of the `hdttools` app package -- this is test infrastructure,
not application code, so it stays out of src/.

Unlike scripts/pass_pool.py, the fail-pool's golden_fields.json section
is self-contained: each vehicle entry carries its own
"expected_none_fields" directly, since these images were deliberately
never added to golden_fields.json's "photos" section (see that file's
"fail_pool" _readme), so there's no existing "photos" entry to resolve
against.
"""

import json
import random
from pathlib import Path

_EXAMPLE_DOCS = Path(__file__).resolve().parent.parent / "ExampleDocs"


def _load_golden() -> dict:
    return json.loads((_EXAMPLE_DOCS / "golden_fields.json").read_text(encoding="utf-8"))


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
