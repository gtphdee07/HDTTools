"""Function tests for scripts/design_compare.py (#197): the finished app's measured layout against the designer's map.

The rules (what a size means, the tolerance, the order, the exceptions) are shown on small made-up elements; the real
data must have no open problem and the committed report must be what the script writes."""

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.minor]

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))
spec = importlib.util.spec_from_file_location("design_compare", _SCRIPTS / "design_compare.py")
compare = importlib.util.module_from_spec(spec)
sys.modules["design_compare"] = compare
spec.loader.exec_module(compare)

Dim = compare.Dim
Expected = compare.Expected


def _expected(element_id="x.a", width="wrap", height="wrap", status="kept", screen="s", added=False):
    return Expected(
        id=element_id, screen=screen, tag="x_a", status=status,
        width=compare.parse_dim(width), height=compare.parse_dim(height), added=added,
    )


def _box(x=16.0, y=100.0, width=380.0, height=56.0, state="s__default", visible=True):
    return {"x": x, "y": y, "width": width, "height": height, "visible": visible, "count": 1, "seen_in_states": 1, "state": state}


# ---- what a size in the map means

@pytest.mark.parametrize(
    ("text", "kind", "dp", "approx"),
    [
        ("fill", "fill", None, False),
        ("wrap", "wrap", None, False),
        ("wrap (~44dp)", "wrap", 44.0, True),
        ("56dp", "fixed", 56.0, False),
        ("892dp", "fixed", 892.0, False),
        ("125dp", "fixed", 125.0, False),
        (None, "none", None, False),
        ("", "none", None, False),
    ],
)
def test_parse_dim(text, kind, dp, approx):
    dim = compare.parse_dim(text)
    assert (dim.kind, dim.dp, dim.approx) == (kind, dp, approx)


def test_a_fixed_size_is_held_to_one_and_a_half_dp_and_an_estimate_to_four_or_ten_percent():
    assert compare.parse_dim("56dp").tolerance == 1.5
    assert compare.parse_dim("wrap (~30dp)").tolerance == 4.0
    assert compare.parse_dim("wrap (~480dp)").tolerance == pytest.approx(48.0)


# ---- sizes

def _size(expected, measured, frame_width=412.0):
    return [p.detail for p in compare.size_problems(expected, measured, frame_width)]


def test_a_fixed_height_inside_the_tolerance_passes_and_outside_it_fails():
    assert _size(_expected(height="56dp"), _box(height=57.4)) == []
    assert _size(_expected(height="56dp"), _box(height=57.6))
    assert _size(_expected(height="56dp"), _box(height=54.4))


def test_an_estimated_height_is_held_to_its_wider_tolerance():
    assert _size(_expected(height="wrap (~30dp)"), _box(height=33.9)) == []
    assert _size(_expected(height="wrap (~30dp)"), _box(height=34.1))
    assert _size(_expected(height="wrap (~480dp)"), _box(height=527.0)) == []  # 10 percent of a tall block


def test_a_wrap_with_no_estimate_has_no_size_to_check():
    assert _size(_expected(width="wrap", height="wrap"), _box(width=10, height=900)) == []


def test_a_fill_must_be_at_least_half_the_screen_and_not_wider_than_it():
    assert _size(_expected(width="fill"), _box(width=380)) == []
    assert _size(_expected(width="fill"), _box(width=206)) == []  # half of 412
    assert _size(_expected(width="fill"), _box(width=200))  # a button that wraps its text is not a fill
    assert _size(_expected(width="fill"), _box(width=420))  # wider than the 412 dp screen
    # Where an element's content starts is not compared: the capture reads x inside the element's own padding.
    assert _size(_expected(width="fill"), _box(x=32, width=380)) == []


def test_an_element_that_holds_several_controls_has_no_box_to_measure():
    assert _size(_expected(width="fill", height="56dp"), {"variants": {"t": _box()}}) == []


# ---- order

def _frame(*specs):
    """specs: (id, n, y, height, state, visible). Returns (measured by id, the legend of frame s__d in the order given)."""
    measured = {i: _box(y=y, height=h, state=state, visible=v) for i, _n, y, h, state, v in specs}
    return measured, {"s__d": [{"n": n, "id": i} for i, n, *_ in specs]}


def test_an_element_numbered_earlier_that_starts_below_the_end_of_a_later_one_is_out_of_order():
    found = compare.order_problems(*_frame(("a", 1, 300, 40, "s__d", True), ("b", 2, 100, 40, "s__d", True)))
    assert [p.id for p in found] == ["a"]
    assert "s__d" in found[0].detail and "before b" in found[0].detail


def test_elements_side_by_side_or_in_order_pass():
    assert compare.order_problems(*_frame(("a", 1, 100, 48, "s__d", True), ("b", 2, 110, 20, "s__d", True))) == []
    assert compare.order_problems(*_frame(("a", 1, 100, 40, "s__d", True), ("b", 2, 200, 40, "s__d", True))) == []


def test_the_numbers_are_the_legends_not_the_order_the_elements_are_listed_in():
    measured, legend = _frame(("a", 2, 300, 40, "s__d", True), ("b", 1, 100, 40, "s__d", True))
    assert compare.order_problems(measured, legend) == []  # b is numbered first and is above a


def test_elements_measured_in_another_state_or_off_screen_are_not_compared():
    assert compare.order_problems(*_frame(("a", 1, 300, 40, "s__one", True), ("b", 2, 100, 40, "s__d", True))) == []
    assert compare.order_problems(*_frame(("a", 1, 300, 40, "s__d", False), ("b", 2, 100, 40, "s__d", True))) == []


def test_an_element_in_no_legend_is_not_compared():
    measured, legend = _frame(("a", 1, 300, 40, "s__d", True), ("b", 2, 100, 40, "s__d", True))
    assert compare.order_problems(measured, {"s__other": legend["s__d"]}) == []


# ---- the whole comparison, on a made-up inventory

_CLEAN = object()


def _parts(*, measured=_CLEAN, flags=None, status="kept", width="wrap", height="56dp"):
    """measured=_CLEAN is a box the map's 56 dp height holds; measured=None is an element no state showed."""
    measured = {"412x892": _box(height=56.0)} if measured is _CLEAN else measured
    element = {"id": "x.a", "screen": "s", "test_tag_new": "x_a", "after_measured": measured}
    redesign = {"status": status, "new_region": "body", "new_order": 1, "new_width": width, "new_height": height, "new_screen": "s"}
    return {
        "inventory": {"elements": [element], "added_after_measured": {}},
        "map": {"elements": [{"id": "x.a", "screen": "s", "redesign": redesign}], "added_elements": []},
        "followup": {"elements": [], "added_elements": []},
        "legends": {},
        "implemented": {"implemented": {"x.a": True} if flags is None else flags},
    }


def test_a_clean_element_has_no_problem():
    problems, counts = compare.compare(_parts())
    assert problems == [] and counts["found"] == 1


def test_an_element_found_in_no_state_is_missing():
    problems, _ = compare.compare(_parts(measured=None))
    assert [(p.kind, p.id) for p in problems] == [("missing", "x.a")]


def test_an_element_whose_flag_is_false_is_unimplemented():
    problems, _ = compare.compare(_parts(flags={"x.a": False}))
    assert [(p.kind, p.id) for p in problems] == [("unimplemented", "x.a")]


def test_a_removed_element_must_not_be_on_a_screen_and_needs_no_flag():
    gone = compare.compare(_parts(status="removed", measured=None, flags={"x.a": False}))[0]
    assert gone == []
    still_there = compare.compare(_parts(status="removed"))[0]
    assert [(p.kind, p.id) for p in still_there] == [("missing", "x.a")]


def test_a_size_outside_the_tolerance_is_a_problem():
    problems, _ = compare.compare(_parts(height="80dp"))
    assert [(p.kind, p.id) for p in problems] == [("size", "x.a")]


def test_an_element_the_designer_added_is_measured_from_added_after_measured():
    parts = _parts()
    parts["map"]["added_elements"] = [{"id": "x.new", "screen": "s", "redesign": {**parts["map"]["elements"][0]["redesign"], "status": "added", "new_test_tag": "x_new"}}]
    parts["implemented"]["implemented"]["x.new"] = True
    assert [p.id for p in compare.compare(parts)[0]] == ["x.new"]  # not measured: missing
    parts["inventory"]["added_after_measured"] = {"x.new": {"412x892": _box(height=56.0)}}
    assert compare.compare(parts)[0] == []


# ---- exceptions

def _problem(kind="size", element_id="x.a"):
    return compare.Problem(kind, element_id, "detail")


def test_an_exception_the_owner_accepted_takes_the_problem_out_of_the_open_list():
    exception = {"id": "x.a", "kind": "size", "reason": "text-dependent", "accepted_by": "owner", "date": "2026-10-31"}
    open_problems, accepted, stale = compare.apply_exceptions([_problem()], [exception])
    assert open_problems == [] and len(accepted) == 1 and stale == []


def test_an_exception_nobody_accepted_accepts_nothing():
    open_problems, accepted, stale = compare.apply_exceptions([_problem()], [{"id": "x.a", "kind": "size", "reason": "r", "accepted_by": None}])
    assert len(open_problems) == 1 and accepted == [] and stale == []


def test_an_exception_for_another_kind_or_id_does_not_match():
    exception = {"id": "x.a", "kind": "order", "reason": "r", "accepted_by": "owner"}
    assert len(compare.apply_exceptions([_problem("size")], [exception])[0]) == 1
    assert len(compare.apply_exceptions([_problem(element_id="x.b")], [{**exception, "kind": "size"}])[0]) == 1


def test_an_accepted_exception_that_matches_no_problem_is_reported_stale():
    exception = {"id": "x.a", "kind": "size", "reason": "r", "accepted_by": "owner"}
    assert compare.apply_exceptions([], [exception])[2] == ["size exception for x.a accepts nothing"]


# ---- the real data

@pytest.fixture(scope="module")
def real():
    parts = compare.design_return_check.load_parts()
    problems, counts = compare.compare(parts)
    return parts, problems, counts


def test_the_finished_app_has_no_problem_the_owner_has_not_accepted(real):
    _, problems, _ = real
    open_problems, _accepted, stale = compare.apply_exceptions(problems, compare.load_exceptions())
    assert [f"{p.kind} {p.id}: {p.detail}" for p in open_problems] == []
    assert stale == []


def test_every_exception_has_a_reason_and_the_owners_acceptance():
    for exception in compare.load_exceptions():
        assert exception["kind"] in compare.KINDS, exception
        assert exception["reason"].strip(), exception
        assert exception["accepted_by"] == "owner" and exception["date"], exception


def test_the_committed_report_is_what_the_script_writes(real):
    parts, problems, counts = real
    assert compare.REPORT.read_text(encoding="utf-8") == compare.report_text(parts, problems, counts, compare.load_exceptions())


def test_every_element_of_both_maps_was_compared_or_removed(real):
    parts, _, counts = real
    wanted = len(parts["map"]["elements"]) + len(parts["map"]["added_elements"]) + len(parts["followup"]["elements"]) + len(parts["followup"]["added_elements"])
    assert counts["elements"] == wanted
    assert counts["found"] > 0.9 * counts["compared"], "the measurement was not merged (run ui_inventory.py --merge-bounds --field after_measured)"


def test_breaking_the_measured_data_is_caught(real):
    parts = copy.deepcopy(real[0])
    victim = next(e for e in parts["inventory"]["elements"] if (e.get("after_measured") or {}).get("412x892", {}).get("height"))
    victim["after_measured"]["412x892"]["height"] += 500
    victim["after_measured"]["412x892"]["width"] = 5
    kinds = {p.kind for p in compare.compare(parts)[0] if p.id == victim["id"]}
    assert kinds & {"size", "order"}
