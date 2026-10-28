"""Function tests for scripts/ui_inventory.py (#188): the Android UI inventory's JSON is the source of truth, and the
CSV, the app's UiTags object and the screens must agree with it. The real files are checked, and each rule is shown
to fail by changing one input in a temporary copy."""

import csv
import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.minor]

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
spec = importlib.util.spec_from_file_location("ui_inventory", _SCRIPTS / "ui_inventory.py")
ui_inventory = importlib.util.module_from_spec(spec)
sys.modules["ui_inventory"] = ui_inventory
spec.loader.exec_module(ui_inventory)


def test_the_repository_inventory_csv_ui_tags_and_screens_agree():
    assert ui_inventory.problems() == []


def test_a_tag_in_the_inventory_but_not_in_ui_tags_is_reported(monkeypatch):
    constants = ui_inventory.ui_tags_constants()
    dropped = constants.pop("OPEN_HISTORY")
    monkeypatch.setattr(ui_inventory, "ui_tags_constants", lambda: constants)

    assert any(f"test_tag_new {dropped!r} is in ui-inventory.json but not in UiTags" in p for p in ui_inventory.problems())


def test_a_ui_tags_value_that_is_in_no_element_is_reported(monkeypatch):
    constants = {**ui_inventory.ui_tags_constants(), "MADE_UP": "made_up_tag"}
    monkeypatch.setattr(ui_inventory, "ui_tags_constants", lambda: constants)

    assert any("'made_up_tag', which is in no test_tag_new" in p for p in ui_inventory.problems())


def test_a_ui_tags_constant_that_no_screen_sets_is_reported(monkeypatch):
    sources = ui_inventory.main_sources_outside_ui_tags().replace("UiTags.OPEN_HISTORY", "")
    monkeypatch.setattr(ui_inventory, "main_sources_outside_ui_tags", lambda: sources)

    assert any("UiTags.OPEN_HISTORY" in p and "set by no screen" in p for p in ui_inventory.problems())


def test_a_tag_the_displayed_test_only_taps_is_not_counted_as_shown(monkeypatch, tmp_path):
    text = ui_inventory.DISPLAYED_TEST.read_text(encoding="utf-8")
    # OPEN_HISTORY stays named in the file, but not as an assertShown argument.
    edited = text.replace("UiTags.OPEN_HISTORY, ", "", 1) + "\n// composeRule.onNodeWithTag(UiTags.OPEN_HISTORY).performClick()\n"
    assert edited != text
    copy = tmp_path / "UiTagsDisplayedTest.kt"
    copy.write_text(edited, encoding="utf-8")
    monkeypatch.setattr(ui_inventory, "DISPLAYED_TEST", copy)

    assert any("UiTags.OPEN_HISTORY" in p and "is not shown by UiTagsDisplayedTest" in p for p in ui_inventory.problems())


def test_a_csv_that_is_not_what_the_generator_writes_is_reported(monkeypatch, tmp_path):
    stale = tmp_path / "ui-inventory.csv"
    stale.write_bytes(ui_inventory.INVENTORY_CSV.read_bytes() + b"extra,row\r\n")
    monkeypatch.setattr(ui_inventory, "INVENTORY_CSV", stale)

    assert any("ui-inventory.csv is not what" in p for p in ui_inventory.problems())


def test_a_missing_csv_is_reported(monkeypatch, tmp_path):
    monkeypatch.setattr(ui_inventory, "INVENTORY_CSV", tmp_path / "missing.csv")

    assert any("ui-inventory.csv is not what" in p for p in ui_inventory.problems())


def test_an_element_edited_in_the_json_makes_the_committed_csv_stale():
    inventory = json.loads(json.dumps(ui_inventory.load_inventory()))
    inventory["elements"][0]["name"] += " (edited)"

    assert ui_inventory.csv_bytes(inventory) != ui_inventory.INVENTORY_CSV.read_bytes()


def test_the_csv_is_utf8_with_a_byte_order_mark_and_one_row_per_element():
    data = ui_inventory.csv_bytes(ui_inventory.load_inventory())

    assert data.startswith(b"\xef\xbb\xbf")
    assert data.decode("utf-8-sig").count("\r\n") >= len(ui_inventory.load_inventory()["elements"]) + 1


def test_refreshing_the_test_references_names_the_test_files_that_use_each_tag():
    inventory = ui_inventory.refresh_tests_referencing(json.loads(json.dumps(ui_inventory.load_inventory())))
    history_button = next(e for e in inventory["elements"] if e["id"] == "picker.history_button")
    next_steps = next(e for e in inventory["elements"] if e["id"] == "scan_error.next_step_button")

    assert history_button["tests_referencing"]["UiTagsDisplayedTest.kt"] >= 1
    assert "HistoryNavigationTest.kt" in history_button["tests_referencing"]
    # An element that carries several tags counts the uses of every one of them.
    assert next_steps["tests_referencing"]["UiTagsDisplayedTest.kt"] >= 6


def test_an_element_with_variants_lists_every_tag_it_carries():
    element = {"test_tag_new": "group", "test_tag_variants": ["a", "b"]}

    assert ui_inventory.element_tags(element) == ["group", "a", "b"]
    assert ui_inventory.element_tags({"test_tag_new": None}) == []


# --- merging the layout capture's bounds (#189) -----------------------------------------------------------------

def _box(x=0.0, y=0.0, width=10.0, height=20.0, visible=True, count=1):
    return {"x": x, "y": y, "width": width, "height": height, "visible": visible, "count": count}


def _bounds_file(screen, state, order, elements, frame="412x892"):
    return {"screen": screen, "state": state, "order": order, "frame": {"name": frame}, "elements": elements}


def _element(element_id, screen, tag, **extra):
    return {"id": element_id, "screen": screen, "test_tag_new": tag, "today": {"width": "wrap"}, "redesign": {}, **extra}


def _inventory(*elements):
    return {"meta": {}, "screens": [{"id": "picker"}, {"id": "chooser"}], "elements": list(elements)}


def _write_frames(root, frames):
    """frames: {frame name: [bounds file, ...]} written as <root>/<frame>/<screen>__<state>.json."""
    for frame, files in frames.items():
        (root / frame).mkdir(parents=True)
        for f in files:
            (root / frame / f"{f['screen']}__{f['state']}.json").write_text(json.dumps(f), encoding="utf-8")
            (root / frame / f"{f['screen']}__{f['state']}.png").write_bytes(b"not read")
    return root


def test_merging_writes_the_measurement_of_every_tag_found_and_reports_the_ones_never_found():
    inventory = _inventory(_element("picker.title", "picker", "picker_title"), _element("picker.gone", "picker", "picker_gone"))
    frames = {"412x892": [_bounds_file("picker", "empty", 0, {"picker_title": _box(x=20.0, y=44.4, width=96.0, height=32.0)})]}

    problems = ui_inventory.merge_bounds(inventory, frames)

    assert inventory["elements"][0]["today_measured"] == {
        "412x892": {
            "state": "picker__empty", "x": 20.0, "y": 44.4, "width": 96.0, "height": 32.0, "visible": True, "count": 1,
            "seen_in_states": 1,
        }
    }
    assert inventory["elements"][1]["today_measured"] is None
    assert problems == ["picker.gone (picker_gone) on picker was never found in any captured state"]


def test_an_element_without_a_tag_is_not_reported_as_missing():
    inventory = _inventory(_element("picker.toast", "picker", None))

    assert ui_inventory.merge_bounds(inventory, {"412x892": [_bounds_file("picker", "empty", 0, {})]}) == []
    assert inventory["elements"][0]["today_measured"] is None


def test_the_first_state_where_the_element_is_on_show_is_the_one_recorded():
    inventory = _inventory(_element("picker.row", "picker", "row"))
    files = [
        _bounds_file("picker", "first", 0, {"row": _box(y=900.0, visible=False)}),
        _bounds_file("picker", "second", 1, {"row": _box(y=100.0)}),
        _bounds_file("picker", "third", 2, {"row": _box(y=300.0)}),
    ]

    ui_inventory.merge_bounds(inventory, {"412x892": files})

    measured = inventory["elements"][0]["today_measured"]["412x892"]
    assert (measured["state"], measured["y"], measured["seen_in_states"]) == ("picker__second", 100.0, 3)


def test_an_element_that_is_never_on_show_is_recorded_from_the_first_state_that_has_it():
    inventory = _inventory(_element("picker.row", "picker", "row"))
    files = [_bounds_file("picker", "a", 0, {"row": _box(y=900.0, visible=False)}), _bounds_file("picker", "b", 1, {"row": _box(y=950.0, visible=False)})]

    ui_inventory.merge_bounds(inventory, {"412x892": files})

    measured = inventory["elements"][0]["today_measured"]["412x892"]
    assert (measured["state"], measured["visible"]) == ("picker__a", False)


def test_a_tag_is_only_looked_for_on_the_screen_of_its_element():
    # Two screens can use one tag (the Scan notice), so the other screen's state must not supply the position.
    inventory = _inventory(_element("picker.title", "picker", "shared"))
    frames = {"412x892": [_bounds_file("chooser", "x", 0, {"shared": _box(x=5.0)})]}

    problems = ui_inventory.merge_bounds(inventory, frames)

    assert inventory["elements"][0]["today_measured"] is None
    assert len(problems) == 1


def test_each_frame_is_measured_on_its_own():
    inventory = _inventory(_element("picker.title", "picker", "t"))
    frames = {
        "412x892": [_bounds_file("picker", "empty", 0, {"t": _box(width=96.0)})],
        "360x640": [_bounds_file("picker", "empty", 0, {"t": _box(width=88.0)}, frame="360x640")],
    }

    ui_inventory.merge_bounds(inventory, frames)

    measured = inventory["elements"][0]["today_measured"]
    assert (measured["412x892"]["width"], measured["360x640"]["width"]) == (96.0, 88.0)


def test_an_element_holding_several_controls_lists_each_one_that_was_found():
    group = _element("dialog.steps", "chooser", "steps", test_tag_variants=["step_a", "step_b", "step_c"])
    inventory = _inventory(group)
    files = [_bounds_file("chooser", "all", 0, {"steps": _box(height=120.0), "step_a": _box(y=1.0), "step_b": _box(y=2.0)})]

    problems = ui_inventory.merge_bounds(inventory, {"412x892": files})

    measured = inventory["elements"][0]["today_measured"]["412x892"]
    assert measured["height"] == 120.0
    assert sorted(measured["variants"]) == ["step_a", "step_b"]
    assert problems == []


def test_a_bounds_file_for_a_screen_the_inventory_does_not_have_is_reported():
    inventory = _inventory(_element("picker.title", "picker", "t"))
    frames = {"412x892": [_bounds_file("pickr", "typo", 0, {"t": _box()}), _bounds_file("picker", "ok", 1, {"t": _box()})]}

    problems = ui_inventory.merge_bounds(inventory, frames)

    assert problems == ["412x892/pickr__typo is for a screen that is not in the inventory"]


def test_merging_after_measured_leaves_today_measured_alone():
    inventory = _inventory(_element("picker.title", "picker", "t"))
    ui_inventory.merge_bounds(inventory, {"412x892": [_bounds_file("picker", "s", 0, {"t": _box(x=1.0)})]})
    ui_inventory.merge_bounds(inventory, {"412x892": [_bounds_file("picker", "s", 0, {"t": _box(x=2.0)})]}, "after_measured")

    element = inventory["elements"][0]
    assert (element["today_measured"]["412x892"]["x"], element["after_measured"]["412x892"]["x"]) == (1.0, 2.0)
    assert "after_measured" in inventory["meta"] and "today_measured" in inventory["meta"]


def test_merging_into_a_field_that_is_not_a_measurement_is_refused():
    with pytest.raises(ValueError):
        ui_inventory.merge_bounds(_inventory(), {}, "today")


def test_today_measured_is_placed_right_after_today_and_merging_twice_changes_nothing():
    inventory = _inventory(_element("picker.title", "picker", "t"))
    frames = {"412x892": [_bounds_file("picker", "s", 0, {"t": _box()})]}

    ui_inventory.merge_bounds(inventory, frames)
    once = json.dumps(inventory)
    ui_inventory.merge_bounds(inventory, frames)

    assert json.dumps(inventory) == once
    assert list(inventory["elements"][0]) == ["id", "screen", "test_tag_new", "today", "today_measured", "redesign"]


def test_the_bounds_files_are_read_per_frame_in_the_captures_order(tmp_path):
    root = _write_frames(tmp_path / "out", {
        "360x640": [_bounds_file("picker", "late", 5, {}, "360x640"), _bounds_file("picker", "early", 2, {}, "360x640")],
        "412x892": [_bounds_file("picker", "only", 0, {})],
    })

    frames = ui_inventory.read_bounds(root)

    assert list(frames) == ["360x640", "412x892"]
    assert [f["state"] for f in frames["360x640"]] == ["early", "late"]


def test_a_missing_or_empty_bounds_directory_is_refused(tmp_path):
    (tmp_path / "empty" / "412x892").mkdir(parents=True)

    with pytest.raises(FileNotFoundError):
        ui_inventory.read_bounds(tmp_path / "nowhere")
    with pytest.raises(FileNotFoundError):
        ui_inventory.read_bounds(tmp_path / "empty")


def test_the_merge_command_updates_the_json_and_the_csv_and_the_check_still_passes(tmp_path, monkeypatch, capsys):
    json_copy = tmp_path / "ui-inventory.json"
    csv_copy = tmp_path / "ui-inventory.csv"
    json_copy.write_bytes(ui_inventory.INVENTORY_JSON.read_bytes())
    csv_copy.write_bytes(ui_inventory.INVENTORY_CSV.read_bytes())
    monkeypatch.setattr(ui_inventory, "INVENTORY_JSON", json_copy)
    monkeypatch.setattr(ui_inventory, "INVENTORY_CSV", csv_copy)
    title = next(e for e in ui_inventory.load_inventory()["elements"] if e["id"] == "picker.app_title")
    root = _write_frames(tmp_path / "out", {
        "412x892": [_bounds_file("rig_picker", "no_saved_rigs", 0, {title["test_tag_new"]: _box(x=20.0, y=48.0, width=96.0, height=32.0)})],
    })

    code = ui_inventory.main(["--merge-bounds", str(root)])

    assert code == 0
    merged = next(e for e in ui_inventory.load_inventory()["elements"] if e["id"] == "picker.app_title")
    assert merged["today_measured"]["412x892"]["width"] == 96.0
    assert "picker.app_title" not in capsys.readouterr().out
    rows = list(csv.reader(io.StringIO(csv_copy.read_text(encoding="utf-8-sig"))))
    columns = rows[0]
    values = next(r for r in rows if r[0] == "picker.app_title")
    assert [values[columns.index(f"today_measured_{c}")] for c in ("x", "y", "width", "height")] == ["20.0", "48.0", "96.0", "32.0"]
    assert ui_inventory.problems() == []


def test_the_merge_command_says_so_when_it_is_given_no_directory_or_a_missing_one(tmp_path, capsys):
    assert ui_inventory.main(["--merge-bounds"]) == 2
    assert ui_inventory.main(["--merge-bounds", str(tmp_path / "nowhere")]) == 2
    assert "no such directory" in capsys.readouterr().out
