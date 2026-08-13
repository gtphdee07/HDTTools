"""RigCheck - Streamlit frontend.

Self-contained alternative to the React/FastAPI web app: no HTTP hop, no
separate server process. Imports the core hdttools OCR-parsing and
breakdown logic directly and runs everything in this one process.

Run with:

    uv run --extra streamlit streamlit run streamlit_app/app.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st
from PIL import Image

from fields import FIELDS, TITLES
from recent_rigs import load_recent_rigs, save_recent_rig

# Make the sibling `src/hdttools` package importable without relying on it
# being pip-installed - a relative path in requirements.txt would resolve
# against pip's current working directory, which isn't reliably known on
# every host (confirmed to differ from "this file's directory" locally,
# and undocumented for Streamlit Community Cloud). __file__ is always
# correct regardless of where the process was launched from.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from hdttools import scale_ticket_ocr, trailer_tag_ocr, truck_tag_ocr  # noqa: E402
from hdttools.api.breakdown import compute_breakdown, verdict_for  # noqa: E402
from hdttools.ocr_common import ensure_tesseract_configured, ocr_text, preprocess_image  # noqa: E402

st.set_page_config(page_title="RigCheck", page_icon="🚚")

MODULE_ORDER = ["truck", "trailer", "scale"]
STEP_LABELS = ["Rig", "Truck Tag", "Trailer Tag", "Scale Ticket", "Results"]

DISCLAIMER_TEXT = (
    "**Experimental Tool — Not for Safety Decisions**\n\n"
    "RigCheck is an experimental project built to learn AI-assisted software "
    "development, not a certified or professional weight-safety tool. Its "
    "numbers come from OCR-read photos, manually reviewed by you, and "
    "simplified math — any step of that chain can be wrong.\n\n"
    "Do not use this tool to decide whether your rig is safe to tow. Always "
    "verify actual weights and ratings using a certified scale and your "
    "vehicle's official documentation, and consult a qualified professional "
    "if you're unsure. You use this tool, and any decisions you make based "
    "on it, entirely at your own risk and responsibility."
)

_PARSERS = {
    "truck": truck_tag_ocr._parse_fields,
    "trailer": trailer_tag_ocr._parse_fields,
    "scale": scale_ticket_ocr._parse_fields,
}


def _init_state() -> None:
    st.session_state.setdefault("step", 0)
    st.session_state.setdefault("rig_nickname", "")
    st.session_state.setdefault("truck", {})
    st.session_state.setdefault("trailer", {})
    st.session_state.setdefault("scale", {})
    st.session_state.setdefault("truck_extracted", False)
    st.session_state.setdefault("trailer_extracted", False)
    st.session_state.setdefault("scale_extracted", False)
    st.session_state.setdefault("recent_rigs", load_recent_rigs())
    st.session_state.setdefault("session_history", [])
    st.session_state.setdefault("result", None)
    st.session_state.setdefault("disclaimer_acknowledged", False)


def _reset_wizard() -> None:
    st.session_state["step"] = 0
    st.session_state["rig_nickname"] = ""
    st.session_state["truck"] = {}
    st.session_state["trailer"] = {}
    st.session_state["scale"] = {}
    st.session_state["truck_extracted"] = False
    st.session_state["trailer_extracted"] = False
    st.session_state["scale_extracted"] = False
    st.session_state["result"] = None


def _extract_fields(module_key: str, uploaded_file) -> dict:
    ensure_tesseract_configured()
    image = Image.open(uploaded_file)
    text = ocr_text(preprocess_image(image))
    parsed = _PARSERS[module_key](text)
    keep = {name for name, _label, _type in FIELDS[module_key]}
    return {k: v for k, v in parsed.items() if k in keep}


def _rig_step() -> None:
    st.header("Which rig are you checking?")

    recent = st.session_state["recent_rigs"]
    if recent:
        st.write("Pick a recent rig — we'll skip straight to the scale ticket:")
        for rig in recent:
            cols = st.columns([4, 1])
            subtitle = " + ".join(
                filter(None, [rig["truck"].get("manufacturer"), rig["trailer"].get("manufacturer")])
            )
            cols[0].markdown(f"**{rig['nickname']}**" + (f"  \n{subtitle}" if subtitle else ""))
            if cols[1].button("Choose", key=f"choose_{rig['nickname']}"):
                st.session_state["rig_nickname"] = rig["nickname"]
                st.session_state["truck"] = dict(rig["truck"])
                st.session_state["trailer"] = dict(rig["trailer"])
                st.session_state["step"] = 3
                st.rerun()
        st.divider()

    st.write("Or start a new rig:")
    nickname = st.text_input("Rig nickname", key="new_rig_nickname", placeholder="e.g. Big Blue")
    if st.button("Start New Rig", disabled=not nickname.strip()):
        st.session_state["rig_nickname"] = nickname.strip()
        st.session_state["step"] = 1
        st.rerun()


def _render_review(module_key: str) -> None:
    st.subheader("Check the numbers")
    st.caption("Here's what we read off your photo. Fix anything that looks off.")
    data = dict(st.session_state[module_key])
    for name, label, field_type in FIELDS[module_key]:
        current = data.get(name)
        if field_type == "number":
            data[name] = st.number_input(
                label, value=float(current) if current else 0.0, step=1.0, key=f"{module_key}_{name}"
            )
        else:
            data[name] = st.text_input(label, value=current or "", key=f"{module_key}_{name}") or None
    st.session_state[module_key] = data


def _module_step(module_key: str) -> None:
    st.header(TITLES[module_key])

    if not st.session_state[f"{module_key}_extracted"]:
        uploaded = st.file_uploader(
            "Upload a photo", type=["jpg", "jpeg", "png", "webp"], key=f"upload_{module_key}"
        )
        if uploaded is not None:
            with st.spinner("Reading the photo..."):
                try:
                    extracted = _extract_fields(module_key, uploaded)
                except Exception as exc:  # noqa: BLE001 - surface any OCR failure to the user
                    st.error(f"Could not read that photo: {exc}")
                    return
            st.session_state[module_key] = extracted
            st.session_state[f"{module_key}_extracted"] = True
            st.rerun()
        return

    _render_review(module_key)
    if st.button("Continue", key=f"continue_{module_key}"):
        current_index = MODULE_ORDER.index(module_key)
        st.session_state["step"] = current_index + 2  # steps are 1-indexed, rig is step 0
        st.rerun()


def _show_disclaimer() -> None:
    st.header("Before you see your results")
    st.warning(DISCLAIMER_TEXT)
    if st.button("I Understand — Continue"):
        st.session_state["disclaimer_acknowledged"] = True
        st.rerun()


def _results_step() -> None:
    if not st.session_state.get("disclaimer_acknowledged"):
        _show_disclaimer()
        return

    st.header("Results")
    truck, trailer, scale = st.session_state["truck"], st.session_state["trailer"], st.session_state["scale"]
    items = compute_breakdown(truck, trailer, scale)
    verdict_info = verdict_for(items)
    verdict = "fail" if verdict_info["headline"].startswith("Not") else "pass"

    if verdict == "pass":
        st.success(f"**{verdict_info['headline']}** — {verdict_info['subline']}")
    else:
        st.error(f"**{verdict_info['headline']}** — {verdict_info['subline']}")

    for item in items:
        st.metric(item["label"], item["actualLabel"], delta=item["badgeLabel"])
        st.progress(min(item["pct"], 100) / 100, text=f"Limit: {item['limitLabel']}")
        if item["note"]:
            st.caption(item["note"])

    if st.session_state["result"] is None:
        date = datetime.now(timezone.utc).strftime("%b %d, %Y")
        st.session_state["recent_rigs"] = save_recent_rig(st.session_state["rig_nickname"], truck, trailer)
        st.session_state["session_history"].insert(
            0, {"nickname": st.session_state["rig_nickname"], "date": date, "verdict": verdict}
        )
        st.session_state["result"] = {"date": date, "verdict": verdict}

    if st.button("Start Another Check"):
        _reset_wizard()
        st.rerun()


def main() -> None:
    _init_state()

    st.title("🚚 RigCheck")
    st.caption(" → ".join(STEP_LABELS[: st.session_state["step"] + 1]))

    step = st.session_state["step"]
    if step == 0:
        _rig_step()
    elif step in (1, 2, 3):
        _module_step(MODULE_ORDER[step - 1])
    else:
        _results_step()

    if st.session_state["session_history"]:
        with st.sidebar:
            st.subheader("This session's checks")
            for entry in st.session_state["session_history"]:
                icon = "✅" if entry["verdict"] == "pass" else "⚠️"
                st.write(f"{icon} **{entry['nickname']}** — {entry['date']}")


main()
