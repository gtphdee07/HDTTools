"""Function tests for scripts/ui_inventory.py (#188): the Android UI inventory's JSON is the source of truth, and the
CSV, the app's UiTags object and the screens must agree with it. The real files are checked, and each rule is shown
to fail by changing one input in a temporary copy."""

import importlib.util
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
