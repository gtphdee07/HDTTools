"""Directory-convention auto-discovery for the pass-pool/fail-pool
(FUTURE_CONSTRAINED_RANDOM_OCR_TESTING.md, roadmap item #13 in
NEXT_STEPS.md).

Standalone module (like scripts/pass_pool.py / scripts/fail_pool.py /
scripts/coverage_lib.py), not part of the `hdttools` app package.

Walks `ExampleDocs/scans/<truck|trailer|scale>/<vehicle_slug>/`. Each
vehicle folder needs exactly one `vehicle.json` sidecar - `doc_type` is
deliberately *not* a field in it, since it's already implied by which
bucket directory the vehicle sits under (one source of truth, not two
that could drift). Every image file (.jpg/.jpeg/.png, case-insensitive)
sitting next to `vehicle.json` is automatically a pool member: adding
one more photo of an already-registered vehicle needs no file edit at
all, only a new `vehicle.json` is needed for a genuinely new vehicle.

`vehicle.json` schema:
    {"pool": "pass", "fields": {...}, "known_ocr_limitations": {...}}
    {"pool": "fail", "expected_none_fields": [...]}

Returns the same per-vehicle dict shape (`vehicle`, `images`, plus
`fields`/`expected_none_fields`) golden_fields.json's own `pass_pool`/
`fail_pool` sections already use, so scripts/pass_pool.py and
scripts/fail_pool.py can merge this in with a plain list-append.
"""

import json
from pathlib import Path

_EXAMPLE_DOCS = Path(__file__).resolve().parent.parent / "ExampleDocs"
_DEFAULT_SCANS_ROOT = _EXAMPLE_DOCS / "scans"
_DOC_TYPE_BY_BUCKET = {"truck": "truck_tag", "trailer": "trailer_tag", "scale": "scale_ticket"}
_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def discover_vehicles(scans_root: Path | None = None) -> dict:
    """Returns {"pass_pool": {doc_type: [vehicle, ...]}, "fail_pool":
    {doc_type: [vehicle, ...]}} built entirely from the real directory
    tree under `scans_root` (default: ExampleDocs/scans/).
    """
    root = scans_root if scans_root is not None else _DEFAULT_SCANS_ROOT
    result: dict = {"pass_pool": {}, "fail_pool": {}}
    if not root.is_dir():
        return result

    for bucket_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        doc_type = _DOC_TYPE_BY_BUCKET.get(bucket_dir.name)
        if doc_type is None:
            continue

        for vehicle_dir in sorted(p for p in bucket_dir.iterdir() if p.is_dir()):
            sidecar = vehicle_dir / "vehicle.json"
            if not sidecar.is_file():
                continue
            _add_vehicle(result, root, doc_type, vehicle_dir, sidecar)

    return result


def _add_vehicle(result: dict, root: Path, doc_type: str, vehicle_dir: Path, sidecar: Path) -> None:
    entry = json.loads(sidecar.read_text(encoding="utf-8"))
    pool = entry.get("pool")
    if pool not in ("pass", "fail"):
        raise ValueError(f"{sidecar}: 'pool' must be 'pass' or 'fail', got {pool!r}")

    images = sorted(
        p.relative_to(root.parent).as_posix()
        for p in vehicle_dir.iterdir()
        if p.suffix.lower() in _IMAGE_EXTENSIONS
    )
    if not images:
        raise ValueError(f"{vehicle_dir}: has a vehicle.json but no image files")

    vehicle = {"vehicle": vehicle_dir.name, "images": images}

    if pool == "pass":
        if "fields" not in entry:
            raise ValueError(f"{sidecar}: pass-pool vehicle.json needs a 'fields' object")
        vehicle["fields"] = entry["fields"]
        if "known_ocr_limitations" in entry:
            vehicle["known_ocr_limitations"] = entry["known_ocr_limitations"]
        result["pass_pool"].setdefault(doc_type, []).append(vehicle)
    else:
        if "expected_none_fields" not in entry:
            raise ValueError(f"{sidecar}: fail-pool vehicle.json needs an 'expected_none_fields' list")
        vehicle["expected_none_fields"] = entry["expected_none_fields"]
        result["fail_pool"].setdefault(doc_type, []).append(vehicle)
