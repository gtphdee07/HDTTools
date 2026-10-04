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

from hdttools import scale_ticket, trailer_tag, truck_tag
from hdttools.api.breakdown import DEFAULT_PIN_WEIGHT_PCT
from hdttools.models import TireSpec

_APP_PATH = Path(__file__).resolve().parent.parent / "streamlit_app" / "app.py"
_EXAMPLE_DOCS = Path(__file__).resolve().parent.parent / "ExampleDocs"
_GOLDEN = json.loads((_EXAMPLE_DOCS / "golden_fields.json").read_text(encoding="utf-8"))

# Needed to import recent_rigs below - app.py relies on Streamlit adding
# its own script directory to sys.path at run time, which pytest doesn't
# do for us when just importing the module directly.
sys.path.insert(0, str(_APP_PATH.parent))
import recent_rigs  # noqa: E402
from fields import TITLES  # noqa: E402

pytestmark = [pytest.mark.streamlit, pytest.mark.minor]


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


def _skip_all_three_modules_to_disclaimer(at: AppTest) -> AppTest:
    for module_key in ("truck", "trailer", "scale"):
        at.button(key=f"skip_{module_key}").click().run()
        assert not at.exception
        at.button(key=f"continue_{module_key}").click().run()
        assert not at.exception
    return at


def test_results_is_hidden_until_the_disclaimer_is_acknowledged():
    # The gate itself (roadmap item from the Streamlit test audit): until
    # now this was only ever clicked through (see the test above), never
    # asserted to actually hide Results beforehand - a regression that
    # deleted the `if not disclaimer_acknowledged` early-return in
    # _results_step would still pass every other test in this file.
    at = AppTest.from_file(str(_APP_PATH))
    _start_test_rig(at)
    _skip_all_three_modules_to_disclaimer(at)

    assert any("Before you see your results" in h.value for h in at.header)
    assert not any(h.value == "Results" for h in at.header)
    assert not at.metric
    assert not at.success
    assert not at.error

    [b for b in at.button if "Understand" in b.label][0].click().run()

    assert not at.exception
    assert any(h.value == "Results" for h in at.header)
    assert at.metric


def test_disclaimer_wording_warns_it_is_experimental_and_not_for_safety_decisions():
    at = AppTest.from_file(str(_APP_PATH))
    _start_test_rig(at)
    _skip_all_three_modules_to_disclaimer(at)

    warnings = [w.value for w in at.warning]
    assert any("Experimental Tool" in w and "Not for Safety Decisions" in w for w in warnings)
    assert any("Do not use this tool to decide whether your rig is safe to tow" in w for w in warnings)
    assert any("entirely at your own risk and responsibility" in w for w in warnings)


def test_start_another_check_resets_the_wizard_but_keeps_session_history():
    at = AppTest.from_file(str(_APP_PATH))
    _start_test_rig(at)
    _skip_all_three_modules_to_disclaimer(at)
    [b for b in at.button if "Understand" in b.label][0].click().run()
    assert not at.exception
    assert len(at.session_state["session_history"]) == 1

    [b for b in at.button if b.label == "Start Another Check"][0].click().run()

    assert not at.exception
    assert at.session_state["step"] == 0
    assert at.session_state["rig_nickname"] == ""
    assert at.session_state["truck"] == {}
    assert at.session_state["trailer"] == {}
    assert at.session_state["scale"] == {}
    assert at.session_state["truck_extracted"] is False
    assert at.session_state["trailer_extracted"] is False
    assert at.session_state["scale_extracted"] is False
    assert at.session_state["truck_skipped"] is False
    assert at.session_state["trailer_skipped"] is False
    assert at.session_state["scale_skipped"] is False
    assert at.session_state["result"] is None
    assert at.session_state["pin_weight_pct"] == round(DEFAULT_PIN_WEIGHT_PCT * 100)
    assert at.session_state["standalone_ticket_processed_id"] is None
    # Deliberately NOT reset by _reset_wizard - it's the sidebar's running
    # tally of every check made this session, not per-rig wizard state.
    assert len(at.session_state["session_history"]) == 1
    assert any(h.value == "Which rig are you checking?" for h in at.header)


def _skip_trailer_with_manual_gvwr(at: AppTest, gvwr_lb: float = 10000.0) -> AppTest:
    at.button(key="skip_trailer").click().run()
    at.number_input(key="trailer_gvwr_lb").set_value(gvwr_lb).run()
    at.button(key="continue_trailer").click().run()
    return at


def test_build_estimated_model_skip_button_reaches_an_estimated_results_notice():
    # Covers both the scale step's second skip button - distinct from
    # "No Image / Enter Weight Manually" but wired to the identical state
    # update (app.py:319-326) - and the predictive-estimate notice it
    # makes reachable: with no scale reading and no stand-alone weight at
    # all, the Trailer Total row falls back to the trailer's rated GVWR
    # (compute_breakdown's final estimate branch), which is what flags an
    # item "estimated" and surfaces PREDICTIVE_ESTIMATE_NOTICE at Results.
    at = AppTest.from_file(str(_APP_PATH))
    _start_test_rig(at)

    at.button(key="skip_truck").click().run()
    at.button(key="continue_truck").click().run()
    _skip_trailer_with_manual_gvwr(at)

    [b for b in at.button if b.label == "Build Estimated Model / No CAT scale info"][0].click().run()
    assert not at.exception
    assert at.session_state["scale_extracted"] is True
    assert at.session_state["scale_skipped"] is True

    at.button(key="continue_scale").click().run()
    [b for b in at.button if "Understand" in b.label][0].click().run()

    assert not at.exception
    assert any("Estimated Figures" in w.value and "Confirm Before You Buy" in w.value for w in at.warning)


def test_pin_weight_slider_feeds_the_trailer_total_estimate():
    # No standalone-ticket upload and no hitched scale reading means
    # compute_breakdown estimates the trailer total off the axle reading
    # and this slider's percentage (app.py:276-283) - the slider's default
    # (20%, app.py:277-282 falls back to DEFAULT_PIN_WEIGHT_PCT) is never
    # otherwise exercised or changed by any existing test.
    at = AppTest.from_file(str(_APP_PATH))
    _start_test_rig(at)
    at.button(key="skip_truck").click().run()

    slider = [s for s in at.slider if "pin/hitch weight" in s.label][0]
    assert slider.value == round(DEFAULT_PIN_WEIGHT_PCT * 100)

    slider.set_value(25).run()
    assert at.session_state["pin_weight_pct"] == 25

    at.button(key="continue_truck").click().run()
    _skip_trailer_with_manual_gvwr(at)
    at.button(key="skip_scale").click().run()
    at.number_input(key="scale_trailer_axle_lb").set_value(8000.0).run()
    at.button(key="continue_scale").click().run()
    [b for b in at.button if "Understand" in b.label][0].click().run()

    assert not at.exception
    # 1 - 0.25 == 75%, quoted straight from compute_breakdown's own note
    # for this branch - a direct line from the slider's value to the
    # number actually used in the estimate, not just that it was clicked.
    assert any("75%" in c.value for c in at.caption)


_RECENT_RIG_TRUCK_FIELDS = {
    "manufacturer": "Ford",
    "gvwr_lb": 14000.0,
    "front_gawr_lb": 6000.0,
    "rear_gawr_lb": 9000.0,
    "standalone_weight_lb": 9000.0,
}
_RECENT_RIG_TRAILER_FIELDS = {
    "manufacturer": "Brinkley RV",
    "gvwr_lb": 14000.0,
    "gawr_per_axle_lb": 5000.0,
}
_RECENT_RIG_SCALE_FIELDS = {
    "location_name": "Example Scale",
    "steer_axle_lb": 5000.0,
    "drive_axle_lb": 7000.0,
    "trailer_axle_lb": 9000.0,
    "gross_weight_lb": 20500.0,
}


def _complete_a_rig_via_mocked_claude_backend(
    monkeypatch, nickname: str, truck_fields: dict, trailer_fields: dict, scale_fields: dict
) -> AppTest:
    """Drive a full rig walkthrough through the mocked Claude backend (no
    Tesseract, no real photos needed) all the way to an acknowledged
    Results screen, so tests of what happens *after* a completed check -
    the recent-rig chooser, a "pass" verdict - don't need real example
    photos of their own, the same way the existing claude-backend dispatch
    tests below avoid them for the upload step alone.
    """
    monkeypatch.setenv("HDTTOOLS_OCR_BACKEND", "claude")
    monkeypatch.setattr(truck_tag, "extract_truck_tag_fields", lambda image_bytes, media_type: dict(truck_fields))
    monkeypatch.setattr(
        trailer_tag, "extract_trailer_tag_fields", lambda image_bytes, media_type: dict(trailer_fields)
    )
    monkeypatch.setattr(scale_ticket, "extract_scale_ticket_fields", lambda image_bytes, media_type: dict(scale_fields))

    at = AppTest.from_file(str(_APP_PATH))
    at.run()
    at.text_input(key="new_rig_nickname").set_value(nickname)
    at.run()
    [b for b in at.button if b.label == "Start New Rig"][0].click().run()

    at.file_uploader(key="upload_truck").set_value(("truck.jpg", b"fake-bytes", "image/jpeg")).run()
    assert not at.exception
    at.button(key="continue_truck").click().run()

    at.file_uploader(key="upload_trailer").set_value(("trailer.jpg", b"fake-bytes", "image/jpeg")).run()
    assert not at.exception
    at.button(key="continue_trailer").click().run()

    at.file_uploader(key="upload_scale").set_value(("scale.jpg", b"fake-bytes", "image/jpeg")).run()
    assert not at.exception
    at.button(key="continue_scale").click().run()

    [b for b in at.button if "Understand" in b.label][0].click().run()
    assert not at.exception
    return at


def test_full_mocked_walkthrough_reaches_a_pass_verdict(monkeypatch):
    # Every existing walkthrough test (real-photo and mocked-Claude alike)
    # only ever reaches "fail" or "insufficient" - this is the first test
    # anywhere, Streamlit or Core, that exercises the Results "pass"
    # banner (app.py:364, `st.success`). Field values are hand-picked so
    # every compute_breakdown row is a real, present reading inside its
    # rated limit - see the audit's worked numbers for why this specific
    # combination lands on "Safe to Tow" with no estimated rows.
    at = _complete_a_rig_via_mocked_claude_backend(
        monkeypatch,
        "Pass Rig",
        _RECENT_RIG_TRUCK_FIELDS,
        _RECENT_RIG_TRAILER_FIELDS,
        _RECENT_RIG_SCALE_FIELDS,
    )

    assert any("Safe to Tow" in s.value for s in at.success)
    assert at.session_state["result"]["verdict"] == "pass"
    # Distinguishes this from the estimated-notice test above: every row
    # here comes from a real reading, so the predictive-estimate notice
    # must not appear.
    assert not any("Estimated Figures" in w.value for w in at.warning)


def test_choosing_a_recent_rig_skips_to_scale_step_with_prefilled_data(monkeypatch):
    _complete_a_rig_via_mocked_claude_backend(
        monkeypatch,
        "Big Blue",
        _RECENT_RIG_TRUCK_FIELDS,
        _RECENT_RIG_TRAILER_FIELDS,
        _RECENT_RIG_SCALE_FIELDS,
    )

    # A fresh session (new AppTest) picks the saved rig up from the same
    # (test-isolated) recent_rigs.json the walkthrough above just wrote.
    at = AppTest.from_file(str(_APP_PATH))
    at.run()

    assert any("Big Blue" in m.value for m in at.markdown)
    assert any("Ford + Brinkley RV" in m.value for m in at.markdown)

    at.button(key="choose_Big Blue").click().run()

    assert not at.exception
    assert at.session_state["step"] == 3
    assert at.session_state["rig_nickname"] == "Big Blue"
    assert at.session_state["truck"]["manufacturer"] == "Ford"
    assert at.session_state["trailer"]["manufacturer"] == "Brinkley RV"
    assert any(h.value == TITLES["scale"] for h in at.header)


_STANDALONE_PHOTO_NAME = "CatScale-GooseOnly.jpg"
_STANDALONE_PHOTO = _EXAMPLE_DOCS / _STANDALONE_PHOTO_NAME
# Ground truth lives in golden_fields.json (single source of truth, shared
# with tests/test_real_photo_ocr_accuracy.py) - the app computes
# standalone_weight_lb as steer + drive for a truck-only weighing.
_STANDALONE_WEIGHT_LB = (
    _golden_fields(_STANDALONE_PHOTO_NAME)["steer_axle_lb"] + _golden_fields(_STANDALONE_PHOTO_NAME)["drive_axle_lb"]
)


@pytest.mark.slow
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


@pytest.mark.slow
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


# Claude-backend dispatch (roadmap item #16): HDTTOOLS_OCR_BACKEND=claude
# routes _extract_fields through the matching new headless extractor
# function instead of real Tesseract - extractor mocked (module-level,
# same object app.py itself imported, so the patch takes effect there
# too), no real ANTHROPIC_API_KEY/network call involved.


def test_claude_backend_truck_upload_calls_the_matching_extractor(monkeypatch):
    monkeypatch.setenv("HDTTOOLS_OCR_BACKEND", "claude")
    monkeypatch.setattr(
        truck_tag,
        "extract_truck_tag_fields",
        lambda image_bytes, media_type: {
            "manufacturer": "Ford",
            "gvwr_lb": 14000.0,
            "front_gawr_lb": 6000.0,
            "rear_gawr_lb": 9900.0,
            "front_tire": TireSpec(tire="225/70R19.5"),
            "rear_tire": TireSpec(tire="225/70R19.5", dual=True),
        },
    )

    at = AppTest.from_file(str(_APP_PATH))
    _start_test_rig(at)
    at.file_uploader(key="upload_truck").set_value(("truck.jpg", b"fake-bytes", "image/jpeg")).run()

    assert not at.exception
    assert at.session_state["truck"]["manufacturer"] == "Ford"
    assert at.session_state["truck"]["gvwr_lb"] == 14000.0
    assert at.session_state["truck_raw_text"] == ""


def test_claude_backend_trailer_upload_calls_the_matching_extractor(monkeypatch):
    monkeypatch.setenv("HDTTOOLS_OCR_BACKEND", "claude")
    monkeypatch.setattr(
        trailer_tag,
        "extract_trailer_tag_fields",
        lambda image_bytes, media_type: {
            "manufacturer": "Brinkley RV",
            "gvwr_lb": 23500.0,
            "gawr_per_axle_lb": 8000.0,
            "uvw_lb": 20554.0,
            "tire": TireSpec(tire="ST215/75R17.5"),
        },
    )

    at = AppTest.from_file(str(_APP_PATH))
    _start_test_rig(at)
    at.button(key="skip_truck").click().run()
    at.button(key="continue_truck").click().run()
    at.file_uploader(key="upload_trailer").set_value(("trailer.jpg", b"fake-bytes", "image/jpeg")).run()

    assert not at.exception
    assert at.session_state["trailer"]["manufacturer"] == "Brinkley RV"
    assert at.session_state["trailer"]["gawr_per_axle_lb"] == 8000.0
    assert at.session_state["trailer_raw_text"] == ""


def test_claude_backend_scale_upload_calls_the_matching_extractor(monkeypatch):
    monkeypatch.setenv("HDTTOOLS_OCR_BACKEND", "claude")
    monkeypatch.setattr(
        scale_ticket,
        "extract_scale_ticket_fields",
        lambda image_bytes, media_type: {
            "location_name": "Loves Country Store",
            "steer_axle_lb": 5620.0,
            "drive_axle_lb": 9040.0,
            "trailer_axle_lb": 11380.0,
            "gross_weight_lb": 26040.0,
        },
    )

    at = AppTest.from_file(str(_APP_PATH))
    _start_test_rig(at)
    at.button(key="skip_truck").click().run()
    at.button(key="continue_truck").click().run()
    at.button(key="skip_trailer").click().run()
    at.button(key="continue_trailer").click().run()
    at.file_uploader(key="upload_scale").set_value(("ticket.jpg", b"fake-bytes", "image/jpeg")).run()

    assert not at.exception
    assert at.session_state["scale"]["gross_weight_lb"] == 26040.0
    assert at.session_state["scale_raw_text"] == ""


def test_claude_backend_never_shows_the_tesseract_raw_text_warning(monkeypatch):
    # The real bug this guards against: raw_text is always "" under the
    # Claude backend (there's no OCR text at all), so the pre-existing
    # `elif not raw_text.strip():` branch would otherwise show "Tesseract
    # returned no text at all..." on every single successful Claude
    # extraction - a false claim, since nothing here even calls
    # Tesseract. Confirmed against a genuinely successful extraction
    # (real-looking, non-empty fields), not a degenerate all-null one.
    monkeypatch.setenv("HDTTOOLS_OCR_BACKEND", "claude")
    monkeypatch.setattr(
        truck_tag,
        "extract_truck_tag_fields",
        lambda image_bytes, media_type: {
            "manufacturer": "Ford",
            "gvwr_lb": 14000.0,
            "front_gawr_lb": 6000.0,
            "rear_gawr_lb": 9900.0,
            "front_tire": TireSpec(),
            "rear_tire": TireSpec(),
        },
    )

    at = AppTest.from_file(str(_APP_PATH))
    _start_test_rig(at)
    at.file_uploader(key="upload_truck").set_value(("truck.jpg", b"fake-bytes", "image/jpeg")).run()

    assert not at.exception
    assert not any("Tesseract returned no text" in w.value for w in at.warning)


# OCR-failure error branches (app.py:248-250, 255-256, 258, 309-311) - the
# extraction call can fail for either upload widget (the main per-module
# upload and the truck step's optional standalone-ticket upload), and the
# standalone ticket has its own, separate "found text but no weight in it"
# failure mode. All three previously went untested; reusing the mocked
# Claude backend from the dispatch tests above keeps them offline and
# deterministic rather than needing a real corrupt photo.


def _raising_extractor(message: str):
    def _raise(image_bytes, media_type):
        raise RuntimeError(message)

    return _raise


def _start_rig_and_upload_a_standalone_ticket() -> AppTest:
    at = AppTest.from_file(str(_APP_PATH))
    _start_test_rig(at)
    at.button(key="skip_truck").click().run()
    at.file_uploader(key="standalone_ticket_upload").set_value(
        ("standalone.jpg", b"fake-bytes", "image/jpeg")
    ).run()
    return at


def test_main_upload_failure_shows_an_error_without_crashing(monkeypatch):
    monkeypatch.setenv("HDTTOOLS_OCR_BACKEND", "claude")
    monkeypatch.setattr(truck_tag, "extract_truck_tag_fields", _raising_extractor("vision API unavailable"))

    at = AppTest.from_file(str(_APP_PATH))
    _start_test_rig(at)
    at.file_uploader(key="upload_truck").set_value(("truck.jpg", b"fake-bytes", "image/jpeg")).run()

    assert not at.exception
    assert any(
        "Could not read that photo" in e.value and "vision API unavailable" in e.value for e in at.error
    )
    assert at.session_state["truck_extracted"] is False


def test_standalone_ticket_upload_failure_shows_an_error_without_crashing(monkeypatch):
    monkeypatch.setenv("HDTTOOLS_OCR_BACKEND", "claude")
    monkeypatch.setattr(scale_ticket, "extract_scale_ticket_fields", _raising_extractor("vision API unavailable"))

    at = _start_rig_and_upload_a_standalone_ticket()

    assert not at.exception
    assert any(
        "Could not read that photo" in e.value and "vision API unavailable" in e.value for e in at.error
    )
    assert at.session_state["truck"].get("standalone_weight_lb") is None


def test_standalone_ticket_falls_back_to_gross_weight_with_no_axle_split(monkeypatch):
    # The other half of the standalone-weight derivation (app.py:253-256):
    # steer+drive wins when both are present, but a ticket that only
    # reports a single gross weight (no per-axle split) still works, via
    # the `elif extracted.get("gross_weight_lb")` branch.
    monkeypatch.setenv("HDTTOOLS_OCR_BACKEND", "claude")
    monkeypatch.setattr(
        scale_ticket,
        "extract_scale_ticket_fields",
        lambda image_bytes, media_type: {
            "location_name": "Example Scale",
            "steer_axle_lb": None,
            "drive_axle_lb": None,
            "trailer_axle_lb": None,
            "gross_weight_lb": 12345.0,
        },
    )

    at = _start_rig_and_upload_a_standalone_ticket()

    assert not at.exception
    assert at.session_state["truck"]["standalone_weight_lb"] == 12345.0


def test_standalone_ticket_with_no_weight_found_shows_an_error(monkeypatch):
    monkeypatch.setenv("HDTTOOLS_OCR_BACKEND", "claude")
    monkeypatch.setattr(
        scale_ticket,
        "extract_scale_ticket_fields",
        lambda image_bytes, media_type: {
            "location_name": "Example Scale",
            "steer_axle_lb": None,
            "drive_axle_lb": None,
            "trailer_axle_lb": None,
            "gross_weight_lb": None,
        },
    )

    at = _start_rig_and_upload_a_standalone_ticket()

    assert not at.exception
    assert any("Couldn't find a weight on that ticket" in e.value for e in at.error)
    assert at.session_state["truck"].get("standalone_weight_lb") is None
