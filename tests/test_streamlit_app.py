"""Streamlit UI regression tests via streamlit.testing.v1.AppTest.

Covers the skip-image feature end to end at the app-script level (not
just compute_breakdown in isolation), since the real bug this guards
against lived in app.py's own widget wiring: st.number_input cannot
return None, so simply rendering the review screen was silently turning
every un-entered field into a real 0.0 instead of leaving it blank. That
defeated compute_breakdown's presence-based "insufficient" tracking and
crashed with a ZeroDivisionError once a fully-skipped rig reached
Results - a failure compute_breakdown's own unit tests can't see, because
they call it directly with genuinely blank dicts.
"""

import json
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

_APP_PATH = Path(__file__).resolve().parent.parent / "streamlit_app" / "app.py"
_EXAMPLE_DOCS = Path(__file__).resolve().parent.parent / "ExampleDocs"
_GOLDEN = json.loads((_EXAMPLE_DOCS / "golden_fields.json").read_text(encoding="utf-8"))

# Needed to import recent_rigs below - app.py relies on Streamlit adding
# its own script directory to sys.path at run time, which pytest doesn't
# do for us when just importing the module directly.
sys.path.insert(0, str(_APP_PATH.parent))
import recent_rigs  # noqa: E402


def _photo_bytes(filename: str) -> bytes:
    return (_EXAMPLE_DOCS / filename).read_bytes()


def _golden_fields(filename: str) -> dict:
    return _GOLDEN["photos"][filename]["fields"]


def _known_limitations(filename: str) -> set[str]:
    return set(_GOLDEN["photos"][filename].get("known_ocr_limitations", {}))


@pytest.fixture(autouse=True)
def _isolate_recent_rigs(tmp_path, monkeypatch):
    # Every test in this file drives the real app.py, including its real
    # (non-mocked) recent-rigs persistence - without this, completing a
    # checkout here would write test rig nicknames straight into the
    # developer's actual ~/.rigcheck/recent_rigs.json.
    monkeypatch.setattr(recent_rigs, "RECENT_RIGS_PATH", tmp_path / "recent_rigs.json")


def _start_test_rig(at: AppTest) -> AppTest:
    at.run()
    at.text_input(key="new_rig_nickname").set_value("Test Rig")
    at.run()
    [b for b in at.button if b.label == "Start New Rig"][0].click().run()
    return at


def test_skipping_all_three_images_reaches_results_without_crashing():
    at = AppTest.from_file(str(_APP_PATH))
    _start_test_rig(at)

    for module_key in ("truck", "trailer", "scale"):
        at.button(key=f"skip_{module_key}").click().run()
        assert not at.exception
        at.button(key=f"continue_{module_key}").click().run()
        assert not at.exception

    [b for b in at.button if "Understand" in b.label][0].click().run()

    assert not at.exception
    assert any("Not Enough Information" in info.value for info in at.info)


def test_skipped_module_shows_a_skip_notice_not_an_ocr_failure_warning():
    at = AppTest.from_file(str(_APP_PATH))
    _start_test_rig(at)

    at.button(key="skip_truck").click().run()

    assert not at.exception
    assert any("No photo provided" in info.value for info in at.info)
    assert not any("Tesseract returned no text" in w.value for w in at.warning)


_STANDALONE_PHOTO_NAME = "CatScale-GooseOnly.jpg"
_STANDALONE_PHOTO = _EXAMPLE_DOCS / _STANDALONE_PHOTO_NAME
# Ground truth lives in golden_fields.json (single source of truth, shared
# with tests/test_real_photo_ocr_accuracy.py) - the app computes
# standalone_weight_lb as steer + drive for a truck-only weighing.
_STANDALONE_WEIGHT_LB = (
    _golden_fields(_STANDALONE_PHOTO_NAME)["steer_axle_lb"] + _golden_fields(_STANDALONE_PHOTO_NAME)["drive_axle_lb"]
)


def test_scanning_a_real_tow_vehicle_only_photo_fills_in_standalone_weight():
    # Regression test for a real bug: scanning the ticket set
    # truck["standalone_weight_lb"] correctly, but the very next render of
    # the review form silently overwrote it back to blank. The
    # truck_standalone_weight_lb number_input widget's own cached state
    # (still blank from before the scan) took priority over the freshly
    # updated dict on rerun - a classic Streamlit "stale widget value"
    # trap. Fixed by seeding the widget's own session_state key (via a
    # pending-update handoff, since Streamlit forbids writing to a
    # widget's key after it's already been instantiated in the same run)
    # instead of only updating the underlying data dict. Uses the real
    # tow-vehicle-only CAT Scale photo through real Tesseract OCR - the
    # mocked-everything unit tests can't see this class of bug at all,
    # since it lives entirely in app.py's own widget/rerun wiring.
    assert _STANDALONE_PHOTO.is_file(), f"expected the example photo at {_STANDALONE_PHOTO}"

    at = AppTest.from_file(str(_APP_PATH))
    _start_test_rig(at)
    at.button(key="skip_truck").click().run()

    at.file_uploader(key="standalone_ticket_upload").set_value(
        (_STANDALONE_PHOTO_NAME, _photo_bytes(_STANDALONE_PHOTO_NAME), "image/jpeg")
    ).run()

    assert not at.exception
    assert at.session_state["truck"]["standalone_weight_lb"] == _STANDALONE_WEIGHT_LB
    assert at.number_input(key="truck_standalone_weight_lb").value == _STANDALONE_WEIGHT_LB


_VERDICT_ELEMENTS = {"pass": "success", "fail": "error"}


@pytest.mark.parametrize("rig", _GOLDEN["rigs"], ids=[rig["name"] for rig in _GOLDEN["rigs"]])
def test_full_walkthrough_with_real_photos_reaches_a_real_verdict(rig):
    # The actual gap roadmap item #6 closes: every existing "full
    # walkthrough" test in this repo (this file and web/'s Playwright
    # suite both) only drives the zero-image, skip-everything path. This
    # is the first test anywhere that uploads a real truck tag, a real
    # standalone ticket, a real trailer tag, AND a real full-rig scale
    # ticket through the real (unmocked) app, via real Tesseract OCR, all
    # the way to a real Results verdict - not a guessed one, computed by
    # hand against compute_breakdown/verdict_for and recorded on this
    # rig's golden_fields.json entry (see its own "_verdict_note").
    # Parametrized over golden_fields.json's "rigs" - a future combination
    # needs a new rig entry there, not new test code.
    truck_photo, trailer_photo = rig["truck_photo"], rig["trailer_photo"]
    scale_photo, standalone_photo = rig["scale_photo"], rig["standalone_scale_photo"]

    at = AppTest.from_file(str(_APP_PATH))
    _start_test_rig(at)

    # Truck tag, then the standalone tow-vehicle-only ticket (both real
    # photos, both feed truck's own session_state before Continue).
    at.file_uploader(key="upload_truck").set_value(
        (truck_photo, _photo_bytes(truck_photo), "image/jpeg")
    ).run()
    assert not at.exception
    for field, expected in _golden_fields(truck_photo).items():
        if field in _known_limitations(truck_photo):
            continue
        assert at.session_state["truck"].get(field) == expected, f"{truck_photo}: {field}"

    at.file_uploader(key="standalone_ticket_upload").set_value(
        (standalone_photo, _photo_bytes(standalone_photo), "image/jpeg")
    ).run()
    assert not at.exception
    standalone_fields = _golden_fields(standalone_photo)
    expected_standalone_weight = standalone_fields["steer_axle_lb"] + standalone_fields["drive_axle_lb"]
    assert at.session_state["truck"]["standalone_weight_lb"] == expected_standalone_weight

    at.button(key="continue_truck").click().run()
    assert not at.exception

    # Trailer tag - axle_count is manual-only (never OCR-extracted, see
    # golden_fields.json's own note on this field), so it's entered via
    # its widget directly, same as a real user would.
    at.file_uploader(key="upload_trailer").set_value(
        (trailer_photo, _photo_bytes(trailer_photo), "image/jpeg")
    ).run()
    assert not at.exception
    for field, expected in _golden_fields(trailer_photo).items():
        if field in _known_limitations(trailer_photo):
            continue
        assert at.session_state["trailer"].get(field) == expected, f"{trailer_photo}: {field}"

    at.number_input(key="trailer_axle_count").set_value(rig["trailer_axle_count"]).run()
    assert not at.exception
    assert at.session_state["trailer"]["axle_count"] == rig["trailer_axle_count"]

    at.button(key="continue_trailer").click().run()
    assert not at.exception

    # Full-rig scale ticket.
    at.file_uploader(key="upload_scale").set_value(
        (scale_photo, _photo_bytes(scale_photo), "image/jpeg")
    ).run()
    assert not at.exception
    for field, expected in _golden_fields(scale_photo).items():
        # scale_number isn't in fields.py's FIELDS["scale"] - _extract_fields'
        # `keep` filter drops it before it ever reaches session_state.
        if field == "scale_number" or field in _known_limitations(scale_photo):
            continue
        assert at.session_state["scale"].get(field) == expected, f"{scale_photo}: {field}"

    at.button(key="continue_scale").click().run()
    assert not at.exception

    # Disclaimer -> Results.
    [b for b in at.button if "Understand" in b.label][0].click().run()
    assert not at.exception

    expected_status = rig["expected_verdict_status"]
    expected_headline = rig["expected_verdict_headline"]
    element_kind = _VERDICT_ELEMENTS.get(expected_status, "info")
    elements = getattr(at, element_kind)
    assert any(expected_headline in element.value for element in elements), (
        f"expected a {element_kind!r} element containing {expected_headline!r}, "
        f"got: {[element.value for element in elements]}"
    )
