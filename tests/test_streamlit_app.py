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
