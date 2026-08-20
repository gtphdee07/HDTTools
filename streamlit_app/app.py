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
from hdttools.api.breakdown import DEFAULT_PIN_WEIGHT_PCT, compute_breakdown, verdict_for  # noqa: E402
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

# Persistent (shown every time it's relevant, not a one-time acknowledge-
# and-forget dialog like DISCLAIMER_TEXT above) caution for any breakdown
# row derived from pin-weight-percentage math rather than a real scale
# reading - most commonly the pre-purchase "no rig yet" case.
PREDICTIVE_ESTIMATE_NOTICE = (
    "**⚠️ Estimated Figures — Confirm Before You Buy**\n\n"
    "- Trim, engine, axle ratio, cab/bed size, and factory options change a "
    "specific vehicle's real payload — a GVWR/GAWR from a compliance label "
    "is a rating, not a guarantee for every configuration.\n"
    "- This estimate doesn't account for passengers, cargo in the cab or "
    "bed, or aftermarket accessories — all of which reduce what's actually "
    "left for towing.\n"
    "- Before buying, confirm the actual ratings on that specific vehicle's "
    "own certification label, and the trailer's own data plate — not an "
    "average, a brochure figure, or this estimate.\n"
    "- Actual results may differ. You are solely responsible for safe "
    "towing and for complying with all applicable federal and state "
    "regulations, including FMCSA and DOT requirements."
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
    st.session_state.setdefault("truck_skipped", False)
    st.session_state.setdefault("trailer_skipped", False)
    st.session_state.setdefault("scale_skipped", False)
    st.session_state.setdefault("recent_rigs", load_recent_rigs())
    st.session_state.setdefault("session_history", [])
    st.session_state.setdefault("result", None)
    st.session_state.setdefault("disclaimer_acknowledged", False)
    # Whole percentage points (15-25), not a 0-1 fraction - converted
    # when calling compute_breakdown. Only used when
    # truck.standalone_weight_lb isn't known from a real tow-vehicle-only
    # scale reading.
    st.session_state.setdefault("pin_weight_pct", round(DEFAULT_PIN_WEIGHT_PCT * 100))
    st.session_state.setdefault("standalone_ticket_processed_id", None)


def _reset_wizard() -> None:
    st.session_state["step"] = 0
    st.session_state["rig_nickname"] = ""
    st.session_state["truck"] = {}
    st.session_state["trailer"] = {}
    st.session_state["scale"] = {}
    st.session_state["truck_extracted"] = False
    st.session_state["trailer_extracted"] = False
    st.session_state["scale_extracted"] = False
    st.session_state["truck_skipped"] = False
    st.session_state["trailer_skipped"] = False
    st.session_state["scale_skipped"] = False
    st.session_state["result"] = None
    st.session_state["pin_weight_pct"] = round(DEFAULT_PIN_WEIGHT_PCT * 100)
    st.session_state["standalone_ticket_processed_id"] = None


def _extract_fields(module_key: str, uploaded_file) -> tuple[dict, str]:
    ensure_tesseract_configured()
    image = Image.open(uploaded_file)
    text = ocr_text(preprocess_image(image))
    parsed = _PARSERS[module_key](text)
    keep = {name for name, _label, _type in FIELDS[module_key]}
    fields = {k: v for k, v in parsed.items() if k in keep}
    return fields, text


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

    raw_text = st.session_state.get(f"{module_key}_raw_text", "")
    if st.session_state.get(f"{module_key}_skipped"):
        st.info("No photo provided — fill in what you know below, or leave fields blank.")
    elif not raw_text.strip():
        st.warning(
            "Tesseract returned no text at all from this photo — that points to an "
            "OCR engine/environment problem (e.g. missing language data) rather than "
            "a hard-to-read photo, since even a blurry photo usually yields some text."
        )
    elif not any(st.session_state[module_key].values()):
        st.warning(
            "Tesseract read text from the photo, but none of it matched the fields "
            "we look for — expand below to see what it actually read. This usually "
            "means a label layout our patterns haven't been tuned for yet."
        )
    if raw_text.strip():
        with st.expander("Raw OCR text (for debugging)"):
            st.text(raw_text)

    data = dict(st.session_state[module_key])
    for name, label, field_type in FIELDS[module_key]:
        current = data.get(name)
        if field_type == "number":
            data[name] = st.number_input(
                label,
                value=float(current) if current is not None else None,
                step=1.0,
                key=f"{module_key}_{name}",
                placeholder="Not entered",
            )
        else:
            data[name] = st.text_input(label, value=current or "", key=f"{module_key}_{name}") or None
    st.session_state[module_key] = data


def _render_standalone_ticket_section() -> None:
    """Truck-step-only extra (folded in rather than a new wizard step):
    an optional second upload for a tow-vehicle-only CAT Scale ticket,
    reusing the scale-ticket OCR pipeline (same ticket format, just no
    trailer-axle line) to fill in standalone_weight_lb directly. If it's
    not provided, expose the pin/hitch weight % used as the fallback
    estimate instead of leaving that 15-25% assumption silently hardcoded.
    """
    st.markdown("**Don't know your tow vehicle's stand-alone weight?**")
    st.caption(
        "Scan a CAT Scale ticket weighing just your tow vehicle (no trailer "
        "attached) and we'll fill in the field above for you."
    )
    standalone_file = st.file_uploader(
        "Tow-vehicle-only scale ticket (optional)",
        type=["jpg", "jpeg", "png", "webp"],
        key="standalone_ticket_upload",
    )
    # file_id changes every time a genuinely new file is picked - guards
    # against reprocessing the same upload on every rerun this widget's
    # persisted selection would otherwise trigger.
    if standalone_file is not None and standalone_file.file_id != st.session_state["standalone_ticket_processed_id"]:
        with st.spinner("Reading the ticket..."):
            try:
                extracted, _raw_text = _extract_fields("scale", standalone_file)
            except Exception as exc:  # noqa: BLE001 - surface any OCR failure to the user
                st.error(f"Could not read that photo: {exc}")
                return
        st.session_state["standalone_ticket_processed_id"] = standalone_file.file_id
        standalone = None
        if extracted.get("steer_axle_lb") is not None and extracted.get("drive_axle_lb") is not None:
            standalone = extracted["steer_axle_lb"] + extracted["drive_axle_lb"]
        elif extracted.get("gross_weight_lb") is not None:
            standalone = extracted["gross_weight_lb"]
        if standalone is None:
            st.error("Couldn't find a weight on that ticket — try a clearer photo, or enter it manually above.")
        else:
            st.session_state["truck"]["standalone_weight_lb"] = standalone
            # Can't seed the number_input's own widget key directly here -
            # _render_review (called before this function) has already
            # instantiated it this run, and Streamlit forbids writing to a
            # widget's key after it's been instantiated. Stash it instead;
            # _module_step applies it *before* _render_review runs on the
            # next pass. Without this, the widget's own stale cached state
            # (still blank from before this scan) would silently overwrite
            # this update right back to blank the next time _render_review
            # rebuilds st.session_state["truck"] from its fields - a real
            # bug, caught via a genuine ExampleDocs/ photo walkthrough, not
            # by mocked tests.
            st.session_state["_pending_standalone_weight_lb"] = standalone
            st.success(f"Stand-alone weight set to {standalone:,.0f} lb.")
            st.rerun()

    if not st.session_state["truck"].get("standalone_weight_lb"):
        st.session_state["pin_weight_pct"] = st.slider(
            "No ticket? Estimate pin/hitch weight as this % of the trailer's weight",
            min_value=15,
            max_value=25,
            value=st.session_state["pin_weight_pct"],
        )
        st.caption("Industry recommendations are typically 15-25% — we default to 20%.")


def _module_step(module_key: str) -> None:
    st.header(TITLES[module_key])
    is_scale = module_key == "scale"

    if module_key == "truck" and "_pending_standalone_weight_lb" in st.session_state:
        # Must apply before _render_review below instantiates the
        # truck_standalone_weight_lb widget - see the comment where this
        # gets stashed in _render_standalone_ticket_section.
        st.session_state["truck_standalone_weight_lb"] = st.session_state.pop("_pending_standalone_weight_lb")

    if not st.session_state[f"{module_key}_extracted"]:
        if is_scale:
            st.caption(
                "No CAT scale ticket? You can skip this step and still build an "
                "estimated model from your truck and trailer tag ratings."
            )
        uploaded = st.file_uploader(
            "Upload a photo", type=["jpg", "jpeg", "png", "webp"], key=f"upload_{module_key}"
        )
        if uploaded is not None:
            with st.spinner("Reading the photo..."):
                try:
                    extracted, raw_text = _extract_fields(module_key, uploaded)
                except Exception as exc:  # noqa: BLE001 - surface any OCR failure to the user
                    st.error(f"Could not read that photo: {exc}")
                    return
            st.session_state[module_key] = extracted
            st.session_state[f"{module_key}_raw_text"] = raw_text
            st.session_state[f"{module_key}_extracted"] = True
            st.session_state[f"{module_key}_skipped"] = False
            st.rerun()

        skip_label = "No Image / Enter Weight Manually" if is_scale else "I don't have this image"
        if st.button(skip_label, key=f"skip_{module_key}"):
            st.session_state[f"{module_key}_extracted"] = True
            st.session_state[f"{module_key}_skipped"] = True
            st.rerun()
        if is_scale and st.button("Build Estimated Model / No CAT scale info", key="skip_scale_estimated"):
            st.session_state[f"{module_key}_extracted"] = True
            st.session_state[f"{module_key}_skipped"] = True
            st.rerun()
        return

    _render_review(module_key)
    if module_key == "truck":
        _render_standalone_ticket_section()
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
    pin_weight_pct = st.session_state["pin_weight_pct"] / 100
    items = compute_breakdown(truck, trailer, scale, pin_weight_pct)
    verdict_info = verdict_for(items)
    # verdict_info["status"] is explicit ("pass"/"fail"/"partial"/
    # "insufficient") - never derive it by sniffing whether the headline
    # starts with "Not" (both "Not Safe to Tow" and "Not Enough
    # Information" do, which would misclassify insufficient data as a
    # real failure).
    verdict = verdict_info["status"]

    if verdict == "pass":
        st.success(f"**{verdict_info['headline']}** — {verdict_info['subline']}")
    elif verdict == "fail":
        st.error(f"**{verdict_info['headline']}** — {verdict_info['subline']}")
    else:
        st.info(f"**{verdict_info['headline']}** — {verdict_info['subline']}")

    if any(item["estimated"] for item in items):
        st.warning(PREDICTIVE_ESTIMATE_NOTICE)

    for item in items:
        # st.metric infers delta color from a leading "-" on the string, but
        # our badge labels ("720 lb over", "380 lb to spare") never start
        # with one, so it would show green for both pass and fail. Drive the
        # color from our own already-correct tone instead: "inverse" flips
        # a non-"-"-prefixed string from green to red; "off" leaves
        # insufficient rows uncolored rather than falsely red or green.
        delta_color = "normal" if item["tone"] == "success" else "off" if item["tone"] == "insufficient" else "inverse"
        st.metric(item["label"], item["actualLabel"], delta=item["badgeLabel"], delta_color=delta_color)
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

    _VERDICT_ICONS = {"pass": "✅", "fail": "⚠️", "partial": "❔", "insufficient": "❔"}
    if st.session_state["session_history"]:
        with st.sidebar:
            st.subheader("This session's checks")
            for entry in st.session_state["session_history"]:
                icon = _VERDICT_ICONS.get(entry["verdict"], "❔")
                st.write(f"{icon} **{entry['nickname']}** — {entry['date']}")


main()
