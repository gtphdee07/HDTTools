"""Copy lock for the Android re-skin (#191): the app's words must be the inventory's words, except for the changes
the owner approved in docs/android-redesign/design-return/copy-changes.md.

The inventory (`ui-inventory.json`) records the text of every visible element as it was before the redesign. This
reads the app's Kotlin sources (android/app/src/main) and checks that
  - each changed string's new text is in the sources and its old text is nowhere in them;
  - every other element's text is still there (an inventory text that lists alternatives or placeholders is split
    into its literal pieces first), so a re-skin that rewords a label fails here.
Pieces that cannot be found by design (an inventory text that describes, not quotes) are named in KNOWN_NOT_LITERAL with
the reason; one that is found again must be removed from it, so the list cannot go stale.
"""

import importlib.util
import re
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.minor]

_ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("design_return_check", _ROOT / "scripts" / "design_return_check.py")
check = importlib.util.module_from_spec(_spec)
sys.modules["design_return_check"] = check
_spec.loader.exec_module(check)

ANDROID_MAIN = _ROOT / "android" / "app" / "src" / "main"

# (element id, piece) -> why the sources do not contain that piece word for word.
KNOWN_NOT_LITERAL = {
    ("picker.credit_chip", "1 scan"): "built by creditChipLabel as '$count scan' + 's' (CreditChipLabelTest locks the wording)",
    ("picker.credit_chip", "… (not loaded)"): "a description of the placeholder; creditChipLabel returns '…'",
    ("chooser.credit_chip", "1 scan"): "built by creditChipLabel (CreditChipLabelTest)",
    ("chooser.prompt", "How do you want to enter your truck's compliance-label values? (trailer's / CAT Scale ticket values)"):
        "one inventory cell for the three module variants; the screen has each as its own sentence",
    ("truck.step_bar", "Step 1 of 3"): "built as 'Step $step of $totalSteps'",
    ("trailer.step_bar", "Step 2 of 3"): "built as 'Step $step of $totalSteps'",
    ("scale.step_bar", "Step 3 of 3"): "built as 'Step $step of $totalSteps'",
    ("truck.scan_notice", "A Scan was used and nothing could be read…"): "the inventory shortens the sentence with an ellipsis; ScanMessages.kt has it in full",
    ("trailer.scan_notice", "A Scan was used and nothing could be read…"): "same notice, same source (ScanMessages.kt)",
    ("scale.scan_notice", "A Scan was used and nothing could be read…"): "same notice, same source (ScanMessages.kt)",
    ("truck.description_field", "Description (placeholder: e.g. Ford F-450)"): "label and placeholder are two strings",
    ("trailer.description_field", "Description (placeholder: e.g. Brinkley RV)"): "label and placeholder are two strings",
    ("scale.legend", "1 Scale location   2 Steer   3 Drive   4 Trailer   5 Gross"): "built from one list of five labels",
    ("results.garage_notice", "Your Garage is full"): "the inventory elides the middle of the sentence with '(...)'",
    ("results.estimated_notice", "Confirm Before You Buy + 4 bullets"): "a description of a heading and four bullets",
    ("paywall.explainer", "scan(s) left. [Pro is a one-time purchase, yours to keep, and comes with a starter bundle of scans."):
        "one cell for the conditional sentences of the explainer",
    ("paywall.explainer", "Buy more scans any time. ]Claude reads your truck tag, trailer tag, or scale ticket for you."):
        "one cell for the conditional sentences of the explainer",
    ("account.password_field", "Password (supporting text when creating: At least 6 characters)"): "label and supporting text are two strings",
    ("crash_prompt.dismiss_button", "OK (after 'no email app')"): "a description of when the button reads OK",
}


def _sources() -> str:
    """The Kotlin sources as one text, with concatenated literals joined and the escapes undone."""
    text = "\n".join(p.read_text(encoding="utf-8") for p in sorted(ANDROID_MAIN.rglob("*.kt")))
    text = re.sub(r'"\s*\+\s*\n?\s*"', "", text)
    text = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), text)
    return text.replace('\\"', '"').replace("\\n", "\n")


def _pieces(text: str) -> list[tuple[str, bool]]:
    """The literal pieces of an inventory text, as (piece, partial).

    The text is first split into its alternatives (' | '); each is a whole string. A whole string with a line break,
    a ' — ' or a placeholder in it is cut there, and what is left are parts of strings the code builds or lays out
    differently, so they only have to appear somewhere in a literal.
    """
    pieces: list[tuple[str, bool]] = []
    if text.strip().startswith("(") and text.strip().endswith(")"):
        return pieces  # a description of an icon or a layout, not words on the screen
    for alternative in text.split(" | "):
        alternative = alternative.strip()
        if alternative.startswith(("(", "placeholder:")):
            continue
        parts = re.split(r"\n| — |<[^>]*>|\(\.\.\.\)", alternative)
        if len(parts) == 1:
            if len(alternative) >= 3:
                pieces.append((alternative, False))
            continue
        pieces.extend((p.strip(), True) for p in parts if len(p.strip()) >= 4 and not p.strip().startswith(("(", "placeholder:")))
    return pieces


def _found(piece: tuple[str, bool], sources: str) -> bool:
    """A whole short string must be a whole string literal (so "History" is not satisfied by "History is empty"); a long
    one may be the start of a longer literal, because a sentence is often continued in code; a part may be anywhere."""
    text, partial = piece
    if partial or len(text) >= 25:
        return text in sources
    return f'"{text}"' in sources


COPY_CHANGES = _ROOT / "docs" / "android-redesign" / "design-return" / "copy-changes.md"


def _table_rows(section: str) -> list[list[str]]:
    """The cells of each data row of the first table under the `## <section>` heading of copy-changes.md."""
    text = COPY_CHANGES.read_text(encoding="utf-8")
    start = text.index(f"## {section}")
    end = text.find("\n## ", start + 1)
    body = text[start : end if end != -1 else len(text)]
    rows = [[c.strip() for c in line.strip().strip("|").split(" | ")] for line in body.splitlines() if line.startswith("| `")]
    return rows


def _owner_changed_literals() -> dict[str, str]:
    """element id -> the new text, for the rows of copy-changes.md "Changed strings" whose old and new text are each one
    whole quoted string (the chip rows are rules, not strings). The designer's maps carry the hint rows; the owner
    added the others after the hand-back (the Truck panel, #197)."""
    return {
        row[0].strip("`"): row[2][1:-1]
        for row in _table_rows("Changed strings")
        if all(len(cell) > 2 and cell[0] == cell[-1] == '"' for cell in row[1:3])
    }


def _changed_literals(parts: dict) -> dict[str, str]:
    """element id -> the new text, for the changed strings that are literal text (the chip rule is not)."""
    changed = {}
    for entry in check.effective_entries(parts["map"], parts["followup"]):
        new_text = entry["redesign"].get("new_text")
        if new_text and "scans" not in new_text:
            changed[entry["id"]] = new_text
    return {**changed, **_owner_changed_literals()}


@pytest.fixture(scope="module")
def parts():
    return check.load_parts()


@pytest.fixture(scope="module")
def sources():
    return _sources()


def test_the_changed_strings_are_the_five_the_owner_approved(parts):
    assert _changed_literals(parts) == {
        "truck.reference_hint": "Tap a field to see its spot on the tag",
        "trailer.reference_hint": "Tap a field to see its spot on the tag",
        "truck.standalone_panel_body": (
            "Scan a CAT Scale ticket weighing just your tow vehicle (no trailer attached) and we'll fill in the "
            "field below for you."
        ),
    }
    # The two chip rows are in copy-changes.md as a rule, not a literal (creditChipLabel and its JVM test).
    copy_changes = (_ROOT / "docs" / "android-redesign" / "design-return" / "copy-changes.md").read_text(encoding="utf-8")
    assert "| `picker.credit_chip` |" in copy_changes and "| `chooser.credit_chip` |" in copy_changes


def test_each_changed_string_is_in_the_app_and_its_old_text_is_gone(parts, sources):
    by_id = {e["id"]: e for e in parts["inventory"]["elements"]}
    for element_id, new_text in _changed_literals(parts).items():
        assert new_text in sources, f"{element_id}: the new text {new_text!r} is not in the app"
        old_text = by_id[element_id]["text"]
        assert old_text not in sources, f"{element_id}: the old text {old_text!r} is still in the app"


def test_the_changed_hints_are_on_the_truck_and_trailer_screens_themselves():
    screens = ANDROID_MAIN / "java" / "com" / "rigcheck" / "app" / "ui" / "screens"
    for name in ("TruckTagEntryScreen.kt", "TrailerTagEntryScreen.kt"):
        text = (screens / name).read_text(encoding="utf-8")
        assert '"Tap a field to see its spot on the tag"' in text, name
        assert "Hover a field" not in text, name


def test_the_focus_badge_names_are_in_copy_changes_and_are_the_only_words_the_stored_spots_add():
    """#199: the badge naming the field the pinned card shows. The names are in copy-changes.md (new strings) and are
    the literals ReferenceSpots.kt builds its badges from; a badge with other words in it fails here."""
    copy_changes = (_ROOT / "docs" / "android-redesign" / "design-return" / "copy-changes.md").read_text(encoding="utf-8")
    assert "| `truck.reference_focus_badge` | GVWR / Front GAWR / Rear GAWR |" in copy_changes
    assert "| `trailer.reference_focus_badge` | GVWR / GAWR per axle / UVW |" in copy_changes

    spots = (ANDROID_MAIN / "java" / "com" / "rigcheck" / "app" / "ui" / "ReferenceSpots.kt").read_text(encoding="utf-8")
    badges = re.findall(r'ReferenceSpot\("([^"]+)"', spots)
    assert badges == ["GVWR", "Front GAWR", "Rear GAWR", "GVWR", "GAWR per axle", "UVW"]


def test_the_disclaimer_wording_is_the_inventorys_byte_for_byte(parts, sources):
    """#194: the Disclaimer is legally reviewed. `test_no_other_visible_string_changed` only looks for the pieces of a
    text that has a line break or a dash in it; this holds each of the four whole strings, as the inventory has them,
    to be one string literal in the app, character for character."""
    by_id = {e["id"]: e for e in parts["inventory"]["elements"]}
    for element_id in ("disclaimer.title", "disclaimer.body_1", "disclaimer.body_2", "disclaimer.accept_button"):
        text = by_id[element_id]["text"]
        assert f'"{text}"' in sources, f"{element_id}: the app does not hold {text!r} as one literal"


def test_the_chip_says_zero_scans_signed_out_in_the_shared_function():
    chip = (ANDROID_MAIN / "java" / "com" / "rigcheck" / "app" / "ui" / "CreditChipLabel.kt").read_text(encoding="utf-8")
    assert re.search(r"signedOut\s*->\s*scansText\(0\)", chip)
    assert '"…"' in chip


def test_no_other_visible_string_changed(parts, sources):
    changed = _changed_literals(parts)
    missing = []
    for element in parts["inventory"]["elements"]:
        text = element.get("text")
        if not text or element["id"] in changed:
            continue
        for piece in _pieces(text):
            if not _found(piece, sources) and (element["id"], piece[0]) not in KNOWN_NOT_LITERAL:
                missing.append(f"{element['id']}: {piece[0]!r}")
    assert not missing, "inventory text no longer in the app (reworded?):\n" + "\n".join(missing)


def test_the_known_not_literal_list_has_no_stale_entries(parts, sources):
    texts = {e["id"]: e.get("text") or "" for e in parts["inventory"]["elements"]}
    stale = []
    for (element_id, piece), reason in KNOWN_NOT_LITERAL.items():
        assert reason, f"{element_id}: give the reason"
        assert element_id in texts, f"{element_id} is not an inventory id"
        found_piece = next((p for p in _pieces(texts[element_id]) if p[0] == piece), None)
        assert found_piece, f"{element_id}: {piece!r} is not a piece of its text"
        if _found(found_piece, sources):
            stale.append(f"{element_id}: {piece!r}")
    assert not stale, "now found in the app; remove from KNOWN_NOT_LITERAL:\n" + "\n".join(stale)


def test_a_reworded_label_is_caught(parts, sources):
    """The lock must fail when the app's wording moves: shown by changing one label in a copy of the sources."""
    reworded = sources.replace('"History"', '"Past checks"')
    assert reworded != sources
    history = next(e for e in parts["inventory"]["elements"] if e["id"] == "picker.history_button")
    assert all(_found(p, sources) for p in _pieces(history["text"]))
    assert not all(_found(p, reworded) for p in _pieces(history["text"]))


def test_the_shared_components_say_the_new_status_words(sources):
    # copy-changes.md, "New strings": results.row_badge, and the content descriptions of the shared controls.
    for words in ("Within limit", "Over limit", "Not checked", "Show note", "Hide note", "Back", "Reading…"):
        assert f'"{words}"' in sources, words
    assert "Scan balance: " in sources and ". Opens the Paywall" in sources


NEW_STRINGS = "New strings (new elements, no existing text changes)"


def _new_string_pieces(text: str) -> list[str]:
    """The strings one "New strings" cell holds: its ' / ' alternatives, without a `<placeholder>` in backticks."""
    return [p for part in text.split(" / ") if (p := re.sub(r"`[^`]*`", "", part).strip())]


def test_every_new_string_in_copy_changes_is_in_the_app(sources):
    """#197: the "New strings" table of copy-changes.md lists the words the re-skin added. Each piece of each cell must be
    a string in the app, so a new element that was drawn but not built (or built with other words) fails here."""
    rows = _table_rows(NEW_STRINGS)
    assert len(rows) >= 11, "the table was not read"
    missing = [
        f"{row[0]}: {piece!r}"
        for row in rows
        for piece in _new_string_pieces(row[1])
        if not _found((piece, False), sources)
    ]
    assert not missing, "new strings of copy-changes.md that are not in the app:\n" + "\n".join(missing)


def test_the_sign_out_reason_is_the_one_copy_changes_lists(sources):
    rows = {row[0]: row[1] for row in _table_rows(NEW_STRINGS)}
    assert f'"{rows["`picker.sign_out_unavailable`"]}"' in sources
