"""Function tests for review_form.py's field-discovery/reconstruction
logic (item #8, 2026-09-09) - extracted from add_fields()/rebuild()'s
closures specifically so this doesn't need a real Tkinter window/event
loop, matching test_review_form_coerce.py's own approach for _coerce.
The remaining GUI-wiring (widget creation, .grid() layout, the actual
tk.Tk()/mainloop() call) stays thin, untested glue - same class of gap
this project already accepts for shell-out I/O elsewhere (TESTING.md).
"""

from __future__ import annotations

import dataclasses

import pytest

from hdttools.review_form import _leaf_fields, _rebuild_from_values


@dataclasses.dataclass
class TireSpecLike:
    size: str
    pressure_psi: float | None


@dataclasses.dataclass
class FlatRecord:
    name: str
    weight_lb: float
    is_verified: bool


@dataclasses.dataclass
class NestedRecord:
    company: str
    tire: TireSpecLike


def test_leaf_fields_returns_flat_fields_in_declaration_order():
    record = FlatRecord(name="Goose", weight_lb=34400.0, is_verified=True)
    paths = [path for path, _hint in _leaf_fields(record)]
    assert paths == [("name",), ("weight_lb",), ("is_verified",)]


def test_leaf_fields_resolves_each_fields_real_type_hint():
    record = FlatRecord(name="Goose", weight_lb=34400.0, is_verified=True)
    hints = dict(_leaf_fields(record))
    assert hints[("name",)] is str
    assert hints[("weight_lb",)] is float
    assert hints[("is_verified",)] is bool


def test_leaf_fields_descends_into_a_nested_dataclass_with_a_prefixed_path():
    record = NestedRecord(company="Wandering Trails", tire=TireSpecLike(size="ST205", pressure_psi=50.0))
    paths = [path for path, _hint in _leaf_fields(record)]
    assert paths == [("company",), ("tire", "size"), ("tire", "pressure_psi")]


def test_rebuild_from_values_reconstructs_a_flat_record():
    record = FlatRecord(name="", weight_lb=0.0, is_verified=False)
    values = {("name",): "Goose", ("weight_lb",): "34,400", ("is_verified",): "yes"}
    rebuilt = _rebuild_from_values(record, values)
    assert rebuilt == FlatRecord(name="Goose", weight_lb=34400.0, is_verified=True)


def test_rebuild_from_values_reconstructs_a_nested_record():
    record = NestedRecord(company="", tire=TireSpecLike(size="", pressure_psi=None))
    values = {
        ("company",): "Wandering Trails",
        ("tire", "size"): "ST205",
        ("tire", "pressure_psi"): "50",
    }
    rebuilt = _rebuild_from_values(record, values)
    assert rebuilt == NestedRecord(company="Wandering Trails", tire=TireSpecLike(size="ST205", pressure_psi=50.0))


def test_rebuild_from_values_propagates_a_real_coercion_error():
    record = FlatRecord(name="Goose", weight_lb=0.0, is_verified=False)
    values = {("name",): "Goose", ("weight_lb",): "not-a-number", ("is_verified",): "no"}
    with pytest.raises(ValueError):
        _rebuild_from_values(record, values)


def test_leaf_fields_and_rebuild_from_values_round_trip_through_each_other():
    # Real end-to-end proof: build a values dict from _leaf_fields' own
    # paths (as the widget layer would from live Entry widgets), and
    # confirm _rebuild_from_values reconstructs the identical record -
    # exactly the round trip review_and_edit's Save button performs.
    original = NestedRecord(company="Wandering Trails", tire=TireSpecLike(size="ST205", pressure_psi=50.0))
    values = {path: str(getattr(_resolve_path(original, path[:-1]), path[-1])) for path, _hint in _leaf_fields(original)}
    assert _rebuild_from_values(original, values) == original


def _resolve_path(record, prefix: tuple[str, ...]):
    for name in prefix:
        record = getattr(record, name)
    return record
