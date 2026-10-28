"""Function tests for scripts/design_return_check.py (#191): the designer's hand-back for the Android re-skin is
checked against the inventory. The real files must pass, and each rule is shown to fail on a broken copy of them."""

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.minor]

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "design_return_check.py"
spec = importlib.util.spec_from_file_location("design_return_check", _SCRIPT)
check = importlib.util.module_from_spec(spec)
sys.modules["design_return_check"] = check
spec.loader.exec_module(check)


@pytest.fixture(scope="module")
def real():
    return check.load_parts()


@pytest.fixture
def parts(real):
    return copy.deepcopy(real)


def _first_map_entry(parts, element_id):
    return next(e for e in parts["map"]["elements"] if e["id"] == element_id)


def _problems_with(parts, text):
    return [p for p in check.problems(parts) if text in p]


def test_the_real_hand_back_passes(real):
    assert check.problems(real) == []


def test_the_command_exits_zero_on_the_real_hand_back():
    result = subprocess.run([sys.executable, str(_SCRIPT)], capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0, result.stdout
    assert result.stdout.startswith("ok: 167 inventory ids, 26 added")


def test_the_command_exits_non_zero_when_a_rule_fails(tmp_path, monkeypatch, capsys, real):
    broken = copy.deepcopy(real)
    broken["tokens"].pop("opacity")
    monkeypatch.setattr(check, "load_parts", lambda: broken)

    assert check.main([]) == 1
    assert "tokens.json lacks the group opacity" in capsys.readouterr().out


# Rule: every inventory id has a status from meta.status_values.
def test_an_id_with_a_status_outside_the_list_fails(parts):
    _first_map_entry(parts, "picker.history_button")["redesign"]["status"] = "improved"
    assert _problems_with(parts, "picker.history_button has status 'improved'")


def test_an_inventory_id_missing_from_both_maps_fails(parts):
    parts["map"]["elements"] = [e for e in parts["map"]["elements"] if e["id"] != "picker.history_button"]
    assert _problems_with(parts, "picker.history_button is in the inventory but has no entry")


# Rule: no id is renamed, reused for another function, or dropped without status removed and a reason.
def test_a_renamed_id_fails_both_ways(parts):
    _first_map_entry(parts, "picker.history_button")["id"] = "picker.past_checks_button"
    assert _problems_with(parts, "picker.past_checks_button is in a map but not in the inventory")
    assert _problems_with(parts, "picker.history_button is in the inventory but has no entry")


def test_an_id_reused_for_another_function_fails(parts):
    _first_map_entry(parts, "picker.history_button")["function"] = "Deletes every saved rig."
    assert _problems_with(parts, "picker.history_button is not the same element as the inventory's (differs in function)")


@pytest.mark.parametrize("field", ["screen", "kind", "name", "text", "visible_when", "navigates_to", "test_tag_new"])
def test_every_identity_field_is_compared(parts, field):
    entry = _first_map_entry(parts, "picker.history_button")
    entry[field] = "changed" if entry.get(field) != "changed" else "changed again"
    assert _problems_with(parts, f"differs in {field}")


def test_a_removed_element_with_no_reason_fails(parts):
    _first_map_entry(parts, "picker.header_divider")["redesign"]["notes"] = ""
    assert _problems_with(parts, "picker.header_divider is removed with no reason")


def test_dropping_an_element_by_removing_its_status_fails(parts):
    _first_map_entry(parts, "picker.history_button")["redesign"]["status"] = None
    assert _problems_with(parts, "picker.history_button has status None")


def test_an_id_in_both_maps_fails(parts):
    parts["followup"]["elements"].append(copy.deepcopy(_first_map_entry(parts, "picker.history_button")))
    assert _problems_with(parts, "picker.history_button has 2 entries across the two maps")


def test_the_followup_revision_replaces_the_first_maps_entry(parts):
    # The first map has the toast with no tag; the follow-up revises it. Both must be accepted, and the revised
    # tag must be the one compared.
    revised = parts["followup"]["revised_elements"][0]
    assert revised["id"] == "paywall.toast"
    revised["redesign"]["status"] = "improved"
    assert _problems_with(parts, "paywall.toast has status 'improved'")


# Rule: the first map's copy may differ from today's inventory only where the drift is known and recorded.
def test_a_stale_known_drift_entry_is_reported(parts):
    drifted = next(e for e in parts["inventory"]["elements"] if e["id"] == "scan_error.next_step_button")
    drifted["test_tag_variants"] = None
    assert _problems_with(parts, "KNOWN_DRIFT for scan_error.next_step_button lists test_tag_variants")


def test_drift_outside_the_known_fields_is_still_reported(parts):
    _first_map_entry(parts, "paywall.back")["screen"] = "account"
    assert _problems_with(parts, "paywall.back is not the same element as the inventory's (differs in screen)")


# The inventory gained measured fields (#189) after the hand-back; the maps' copies do not have them.
def test_a_map_entry_without_the_measured_fields_passes(parts):
    inventory_element = next(e for e in parts["inventory"]["elements"] if e["id"] == "picker.history_button")
    assert "today_measured" in inventory_element
    entry = _first_map_entry(parts, "picker.history_button")
    assert "today_measured" not in entry
    assert _problems_with(parts, "picker.history_button") == []


def test_a_measured_field_that_differs_is_ignored(parts):
    inventory_element = next(e for e in parts["inventory"]["elements"] if e["id"] == "picker.history_button")
    inventory_element["today_measured"] = {"412x892": {"x": 0, "y": 0, "width": 1, "height": 1}}
    inventory_element["after_measured"] = {"412x892": {"x": 9}}
    inventory_element["tests_referencing"] = {"SomeNewTest.kt": 3}
    assert check.problems(parts) == []


# Rule: an added element has its screen's prefix and a unique id.
def test_an_added_id_with_another_screens_prefix_fails(parts):
    parts["map"]["added_elements"][0]["id"] = "results.logo"
    assert _problems_with(parts, "results.logo has the prefix of ['results'] but is on 'rig_picker'")


def test_an_added_id_with_no_prefix_fails(parts):
    parts["map"]["added_elements"][0]["id"] = "logo"
    assert _problems_with(parts, "logo is an added element with no screen prefix")


def test_an_added_id_used_twice_fails(parts):
    parts["map"]["added_elements"][1]["id"] = parts["map"]["added_elements"][0]["id"]
    assert _problems_with(parts, "is an added element but the id is already used")


def test_an_added_id_that_is_an_inventory_id_fails(parts):
    parts["map"]["added_elements"][0]["id"] = "picker.history_button"
    assert _problems_with(parts, "picker.history_button is an added element but the id is already used")


def test_an_added_element_for_a_screen_that_has_no_prefix_must_use_its_own_screen(parts):
    splash = next(a for a in parts["map"]["added_elements"] if a["id"].startswith("splash."))
    splash["screen"] = "paywall"
    assert _problems_with(parts, "has a prefix that is no screen's and is not its own screen")


# Rule: a non-removed element has every new_* field.
@pytest.mark.parametrize(
    "field",
    ["new_screen", "new_region", "new_order", "new_width", "new_height", "new_style", "new_test_tag", "notes"],
)
def test_a_missing_new_field_fails(parts, field):
    _first_map_entry(parts, "picker.history_button")["redesign"][field] = None
    assert _problems_with(parts, f"picker.history_button lacks {field}")


def test_a_missing_new_field_on_an_added_element_fails(parts):
    parts["map"]["added_elements"][0]["redesign"]["new_height"] = ""
    assert _problems_with(parts, f"{parts['map']['added_elements'][0]['id']} lacks new_height")


def test_new_text_may_stay_null(parts):
    assert _first_map_entry(parts, "picker.history_button")["redesign"]["new_text"] is None
    assert check.problems(parts) == []


# Rule: every screen has frames named <screen>__<state>.png, and each frame has a legend.
def test_a_screen_with_no_frame_fails(parts):
    parts["frames"] = [f for f in parts["frames"] if not f.startswith("history__")]
    parts["legends"] = {k: v for k, v in parts["legends"].items() if not k.startswith("history__")}
    assert _problems_with(parts, "screen history has no frame named history__<state>.png")


def test_a_frame_named_for_no_screen_fails(parts):
    parts["frames"].append("settings__default")
    parts["legends"]["settings__default"] = []
    assert _problems_with(parts, "frame settings__default.png is not named <screen>__<state>.png for a known screen")


def test_a_frame_without_the_double_underscore_fails(parts):
    parts["frames"].append("history_default")
    parts["legends"]["history_default"] = []
    assert _problems_with(parts, "frame history_default.png is not named")


def test_a_frame_with_no_legend_fails(parts):
    del parts["legends"]["history__few_entries"]
    assert _problems_with(parts, "frame history__few_entries.png has no entry in annotation-legends.json")


def test_a_legend_with_no_frame_fails(parts):
    parts["frames"].remove("history__few_entries")
    assert _problems_with(parts, "annotation-legends.json names history__few_entries, which has no frame")


def test_a_frame_the_followup_map_lists_but_is_missing_fails(parts):
    parts["frames"].remove("rig_picker__feedback_no_mail")
    del parts["legends"]["rig_picker__feedback_no_mail"]
    assert _problems_with(parts, "the follow-up map lists frame rig_picker__feedback_no_mail.png, which is missing")


# Rule: tokens.json has the required groups.
@pytest.mark.parametrize("group", ["colors", "typography", "material3_mapping", "sizes_dp", "radii_dp", "opacity"])
def test_a_missing_token_group_fails(parts, group):
    del parts["tokens"][group]
    assert _problems_with(parts, f"tokens.json lacks the group {group}")


def test_a_missing_token_subgroup_fails(parts):
    del parts["tokens"]["colors"]["neutral"]
    assert _problems_with(parts, "tokens.json lacks colors.neutral")


@pytest.mark.parametrize("key", ["gradients", "spacing_dp", "screen_margin_dp", "elevation", "motion"])
def test_a_missing_top_level_token_key_fails(parts, key):
    del parts["tokens"][key]
    assert _problems_with(parts, f"tokens.json lacks {key}")


# Rule: every element has an implemented flag, false until a re-skin ticket builds it.
def test_every_element_starts_not_implemented(real):
    assert not any(real["implemented"]["implemented"].values())
    assert len(real["implemented"]["implemented"]) == 167 + 26


def test_an_element_without_a_flag_fails(parts):
    del parts["implemented"]["implemented"]["picker.history_button"]
    assert _problems_with(parts, "picker.history_button has no implemented flag")


def test_a_flag_for_an_unknown_id_fails(parts):
    parts["implemented"]["implemented"]["picker.nope"] = False
    assert _problems_with(parts, "implemented has picker.nope")


def test_a_flag_that_is_not_a_boolean_fails(parts):
    parts["implemented"]["implemented"]["picker.history_button"] = "yes"
    assert _problems_with(parts, "picker.history_button has implemented 'yes'")


def test_a_missing_status_file_fails(parts):
    parts["implemented"] = None
    assert _problems_with(parts, "implementation-status.json is missing")


def test_set_implemented_writes_the_flag_and_refuses_unknown_ids(tmp_path, monkeypatch):
    status = tmp_path / "implementation-status.json"
    status.write_text(json.dumps({"implemented": {"a.b": False, "c.d": False}}), encoding="utf-8")
    monkeypatch.setattr(check, "IMPLEMENTED_JSON", status)

    assert check.set_implemented(["a.b"], True) == []
    assert json.loads(status.read_text(encoding="utf-8"))["implemented"] == {"a.b": True, "c.d": False}
    assert check.set_implemented(["a.b"], False) == []
    assert json.loads(status.read_text(encoding="utf-8"))["implemented"]["a.b"] is False
    # An unknown id among the known ones writes nothing.
    assert check.set_implemented(["c.d", "nope.x"], True) == ["nope.x"]
    assert json.loads(status.read_text(encoding="utf-8"))["implemented"]["c.d"] is False
