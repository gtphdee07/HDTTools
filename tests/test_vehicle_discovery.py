"""Function tests for scripts/vehicle_discovery.py's directory-convention
auto-discovery: the mechanism behind item #13's "drop images + a
vehicle.json into a folder, tests pick it up automatically" workflow
(NEXT_STEPS.md, FUTURE_CONSTRAINED_RANDOM_OCR_TESTING.md).

Builds a fake `<tmp>/scans/` tree under `tmp_path` for every case rather
than touching the real ExampleDocs/scans/ - this file only proves the
discovery mechanics in isolation. `scans_root`'s *parent* is what image
paths come back relative to (mirroring production, where
ExampleDocs/scans/'s parent is ExampleDocs/ itself - the same base
tests/test_pass_pool_regression.py and tests/test_fail_pool_regression.py
join filenames against), so every fixture here nests under a `scans/`
subdirectory of `tmp_path`, not `tmp_path` directly. See those two files
for the real, non-isolated proof that discovered vehicles actually
resolve and run through real OCR.
"""

import json
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))  # vehicle_discovery.py is a standalone module, like pass_pool.py

import vehicle_discovery  # noqa: E402


def _scans_root(tmp_path):
    return tmp_path / "scans"


def _write_vehicle(tmp_path, bucket, slug, sidecar, image_names=("photo.jpg",)):
    vehicle_dir = _scans_root(tmp_path) / bucket / slug
    vehicle_dir.mkdir(parents=True)
    (vehicle_dir / "vehicle.json").write_text(json.dumps(sidecar), encoding="utf-8")
    for name in image_names:
        (vehicle_dir / name).write_bytes(b"fake-image-bytes")
    return vehicle_dir


def test_discovers_a_pass_pool_vehicle_with_fields(tmp_path):
    _write_vehicle(
        tmp_path,
        "truck",
        "chevy_silverado",
        {"pool": "pass", "fields": {"manufacturer": "CHEVROLET", "gvwr_lb": 10000.0}},
    )

    result = vehicle_discovery.discover_vehicles(scans_root=_scans_root(tmp_path))

    vehicles = result["pass_pool"]["truck_tag"]
    assert len(vehicles) == 1
    assert vehicles[0]["vehicle"] == "chevy_silverado"
    assert vehicles[0]["images"] == ["scans/truck/chevy_silverado/photo.jpg"]
    assert vehicles[0]["fields"] == {"manufacturer": "CHEVROLET", "gvwr_lb": 10000.0}


def test_discovers_a_fail_pool_vehicle_with_expected_none_fields(tmp_path):
    _write_vehicle(
        tmp_path,
        "trailer",
        "unreadable_rv",
        {"pool": "fail", "expected_none_fields": ["manufacturer", "gvwr_lb"]},
        image_names=("a.jpg", "b.png"),
    )

    result = vehicle_discovery.discover_vehicles(scans_root=_scans_root(tmp_path))

    vehicles = result["fail_pool"]["trailer_tag"]
    assert len(vehicles) == 1
    assert vehicles[0]["images"] == [
        "scans/trailer/unreadable_rv/a.jpg",
        "scans/trailer/unreadable_rv/b.png",
    ]
    assert vehicles[0]["expected_none_fields"] == ["manufacturer", "gvwr_lb"]


def test_a_stray_non_image_file_is_ignored(tmp_path):
    _write_vehicle(
        tmp_path,
        "truck",
        "f150",
        {"pool": "fail", "expected_none_fields": ["manufacturer"]},
        image_names=("photo.jpg",),
    )
    (_scans_root(tmp_path) / "truck" / "f150" / "Spec.txt").write_text("not an image", encoding="utf-8")

    result = vehicle_discovery.discover_vehicles(scans_root=_scans_root(tmp_path))

    assert result["fail_pool"]["truck_tag"][0]["images"] == ["scans/truck/f150/photo.jpg"]


def test_an_unrecognized_bucket_directory_is_ignored(tmp_path):
    vehicle_dir = _scans_root(tmp_path) / "not_a_real_bucket" / "some_vehicle"
    vehicle_dir.mkdir(parents=True)
    (vehicle_dir / "vehicle.json").write_text(json.dumps({"pool": "pass", "fields": {}}), encoding="utf-8")
    (vehicle_dir / "photo.jpg").write_bytes(b"x")

    result = vehicle_discovery.discover_vehicles(scans_root=_scans_root(tmp_path))

    assert result == {"pass_pool": {}, "fail_pool": {}}


@pytest.mark.parametrize(
    "sidecar",
    [
        {"fields": {}},  # missing "pool" entirely
        {"pool": "not_pass_or_fail", "fields": {}},
    ],
)
def test_an_invalid_pool_value_raises_value_error(tmp_path, sidecar):
    _write_vehicle(tmp_path, "truck", "bad_pool", sidecar)

    with pytest.raises(ValueError, match="pool"):
        vehicle_discovery.discover_vehicles(scans_root=_scans_root(tmp_path))


def test_a_pass_pool_entry_missing_fields_raises_value_error(tmp_path):
    _write_vehicle(tmp_path, "truck", "no_fields", {"pool": "pass"})

    with pytest.raises(ValueError, match="fields"):
        vehicle_discovery.discover_vehicles(scans_root=_scans_root(tmp_path))


def test_a_fail_pool_entry_missing_expected_none_fields_raises_value_error(tmp_path):
    _write_vehicle(tmp_path, "truck", "no_signature", {"pool": "fail"})

    with pytest.raises(ValueError, match="expected_none_fields"):
        vehicle_discovery.discover_vehicles(scans_root=_scans_root(tmp_path))


def test_a_vehicle_folder_with_no_images_raises_value_error(tmp_path):
    vehicle_dir = _scans_root(tmp_path) / "truck" / "no_images"
    vehicle_dir.mkdir(parents=True)
    (vehicle_dir / "vehicle.json").write_text(
        json.dumps({"pool": "pass", "fields": {"manufacturer": "X"}}), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="no_images"):
        vehicle_discovery.discover_vehicles(scans_root=_scans_root(tmp_path))


def test_a_missing_scans_root_returns_empty_pools(tmp_path):
    result = vehicle_discovery.discover_vehicles(scans_root=tmp_path / "does_not_exist")
    assert result == {"pass_pool": {}, "fail_pool": {}}
