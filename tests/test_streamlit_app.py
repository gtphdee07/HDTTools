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

from pathlib import Path

from streamlit.testing.v1 import AppTest

_APP_PATH = Path(__file__).resolve().parent.parent / "streamlit_app" / "app.py"


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


_STANDALONE_PHOTO = Path(__file__).resolve().parent.parent / "ExampleDocs" / "CatScale-GooseOnly.jpg"


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

    photo_bytes = _STANDALONE_PHOTO.read_bytes()
    at.file_uploader(key="standalone_ticket_upload").set_value(
        ("CatScale-GooseOnly.jpg", photo_bytes, "image/jpeg")
    ).run()

    assert not at.exception
    assert at.session_state["truck"]["standalone_weight_lb"] == 9980.0
    assert at.number_input(key="truck_standalone_weight_lb").value == 9980.0
