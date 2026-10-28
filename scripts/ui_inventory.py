"""The Android UI inventory (#188): docs/android-redesign/ui-inventory.json is the source of truth.

  uv run scripts/ui_inventory.py                  # rewrite ui-inventory.csv from the JSON
  uv run scripts/ui_inventory.py --check          # exit 1 if the CSV, UiTags.kt or the screens disagree with the JSON
  uv run scripts/ui_inventory.py --refresh-tests  # also recount which test files use each element's tag
  uv run scripts/ui_inventory.py --merge-bounds DIR [--field today_measured|after_measured]
                                                  # write the layout capture's measurements (#189) into the JSON

The check fails when
  - ui-inventory.csv is not byte-identical to what this script writes from the JSON;
  - a `test_tag_new` in the JSON is not a value in the `UiTags` object, or a UiTags value is not in the JSON;
  - a UiTags constant is not used by any file under android/app/src/main outside UiTags.kt (a tag no screen sets);
  - a UiTags constant is not an argument of an assertShown(...) call in UiTagsDisplayedTest.kt, the instrumented
    test that shows every tagged element on a real screen (a tag that is only tapped or typed into does not count).
"""

from __future__ import annotations

import csv
import io
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INVENTORY_JSON = REPO_ROOT / "docs" / "android-redesign" / "ui-inventory.json"
INVENTORY_CSV = REPO_ROOT / "docs" / "android-redesign" / "ui-inventory.csv"
ANDROID_MAIN = REPO_ROOT / "android" / "app" / "src" / "main"
UI_TAGS_KT = ANDROID_MAIN / "java" / "com" / "rigcheck" / "app" / "ui" / "UiTags.kt"
ANDROID_TEST = REPO_ROOT / "android" / "app" / "src" / "androidTest"
DISPLAYED_TEST = (
    REPO_ROOT / "android" / "app" / "src" / "androidTest" / "java" / "com" / "rigcheck" / "app" / "ui"
    / "UiTagsDisplayedTest.kt"
)

# The arguments of one assertShown(...) call in UiTagsDisplayedTest (they hold no parentheses of their own).
ASSERT_SHOWN_CALL = re.compile(r"assertShown\(([^()]*)\)")

FIXED_COLUMNS = [
    "id", "screen", "kind", "name", "function", "text", "visible_when", "navigates_to",
]
TODAY_COLUMNS = ["region", "order", "width", "height", "style"]
# The measured position and size at the reference frame, from the layout capture (today_measured).
MEASURED_COLUMNS = ["x", "y", "width", "height"]
REFERENCE_FRAME = "412x892"
MEASURED_FIELDS = ("today_measured", "after_measured")
MEASURED_NOTES = {
    "today_measured": (
        "Measured on the emulator by the layout capture (LayoutCaptureTest, #189; merged by "
        "`scripts/ui_inventory.py --merge-bounds`), per frame (412x892 is the reference frame, 360x640 the small phone, "
        "-font2.0 the same at font scale 2.0). x and y are the element's top-left corner on the display and width and "
        "height its size as laid out, all in dp, in the first captured state (in the capture's order) where it is on "
        "show; `visible` is whether any of it is on show there (width and height are the laid-out size, so an element "
        "scrolled out of view keeps its size and has visible false); `count` how many elements carry the tag there (a "
        "repeated item); `seen_in_states` in how many captured states it is present. null: never found in any state, "
        "or untagged (the merge names those). "
        "These supersede the estimates in `today`, which stay for the designer's round."
    ),
    "after_measured": "The same measurement of the re-skinned app (#197), merged with `--field after_measured`.",
}
REDESIGN_COLUMNS = [
    "status", "new_screen", "new_region", "new_order", "new_width", "new_height", "new_style", "new_text",
    "new_test_tag", "notes",
]
HEADER = (
    FIXED_COLUMNS
    + [f"today_{c}" for c in TODAY_COLUMNS]
    + [f"today_measured_{c}" for c in MEASURED_COLUMNS]
    + ["test_tag_today", "test_tag_new", "tests_referencing"]
    + [f"REDESIGN_{c}" for c in REDESIGN_COLUMNS]
)

_CONST_VALUE = re.compile(r'const val (\w+)\s*=\s*"([^"]+)"')


def load_inventory() -> dict:
    return json.loads(INVENTORY_JSON.read_text(encoding="utf-8"))


def _cell(value) -> str:
    return "" if value is None else str(value).replace("\n", " / ")


def _tests_cell(tests: dict) -> str:
    return "; ".join(f"{name} x{count}" for name, count in sorted(tests.items()))


def csv_text(inventory: dict) -> str:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\r\n")
    writer.writerow(HEADER)
    for element in inventory["elements"]:
        today = element["today"]
        redesign = element["redesign"]
        writer.writerow(
            [_cell(element[c]) for c in FIXED_COLUMNS]
            + [_cell(today[c]) for c in TODAY_COLUMNS]
            + [_cell(((element.get("today_measured") or {}).get(REFERENCE_FRAME) or {}).get(c)) for c in MEASURED_COLUMNS]
            + [
                _cell(element["test_tag_today"]),
                "; ".join(element_tags(element)),
                _tests_cell(element["tests_referencing"]),
            ]
            + [_cell(redesign[c]) for c in REDESIGN_COLUMNS]
        )
    return out.getvalue()


def csv_bytes(inventory: dict) -> bytes:
    """UTF-8 with a BOM, so Excel opens it as UTF-8."""
    return b"\xef\xbb\xbf" + csv_text(inventory).encode("utf-8")


def element_tags(element: dict) -> list[str]:
    """The tags an element carries: test_tag_new, then any test_tag_variants (one per control it holds)."""
    return ([element["test_tag_new"]] if element["test_tag_new"] else []) + element.get("test_tag_variants", [])


def inventory_tags(inventory: dict) -> set[str]:
    return {tag for e in inventory["elements"] for tag in element_tags(e)}


def ui_tags_constants() -> dict[str, str]:
    """UiTags.kt's constants, name -> tag value."""
    return dict(_CONST_VALUE.findall(UI_TAGS_KT.read_text(encoding="utf-8")))


def main_sources_outside_ui_tags() -> str:
    return "\n".join(
        p.read_text(encoding="utf-8") for p in sorted(ANDROID_MAIN.rglob("*.kt")) if p != UI_TAGS_KT
    )


def problems(inventory: dict | None = None) -> list[str]:
    inventory = inventory or load_inventory()
    found: list[str] = []

    if not INVENTORY_CSV.exists() or INVENTORY_CSV.read_bytes() != csv_bytes(inventory):
        found.append(
            "ui-inventory.csv is not what scripts/ui_inventory.py writes from ui-inventory.json "
            "(run: uv run scripts/ui_inventory.py)"
        )

    wanted = inventory_tags(inventory)
    constants = ui_tags_constants()
    have = set(constants.values())
    for tag in sorted(wanted - have):
        found.append(f"test_tag_new {tag!r} is in ui-inventory.json but not in UiTags")
    for tag in sorted(have - wanted):
        found.append(f"UiTags has {tag!r}, which is in no test_tag_new of ui-inventory.json")
    values = list(constants.values())
    for tag in sorted({v for v in values if values.count(v) > 1}):
        found.append(f"UiTags has the value {tag!r} more than once")

    used_in = main_sources_outside_ui_tags()
    test_text = DISPLAYED_TEST.read_text(encoding="utf-8") if DISPLAYED_TEST.exists() else ""
    shown_text = "\n".join(ASSERT_SHOWN_CALL.findall(test_text))
    for name, tag in sorted(constants.items()):
        if not re.search(rf"\bUiTags\.{name}\b", used_in):
            found.append(f"UiTags.{name} ({tag!r}) is set by no screen or component under android/app/src/main")
        if not re.search(rf"\bUiTags\.{name}\b", shown_text):
            found.append(f"UiTags.{name} ({tag!r}) is not shown by UiTagsDisplayedTest")
    return found


def refresh_tests_referencing(inventory: dict) -> dict:
    """Sets each element's tests_referencing to the instrumented test files that use its tag(s), and how often.

    A file that only lists every tag (UiTagsDisplayedTest) counts too, so an element's row says where it is shown.
    """
    constants = ui_tags_constants()
    by_tag = {tag: name for name, tag in constants.items()}
    tests = {p.name: p.read_text(encoding="utf-8") for p in sorted(ANDROID_TEST.rglob("*Test.kt"))}
    for element in inventory["elements"]:
        counts: dict[str, int] = {}
        for tag in element_tags(element):
            pattern = re.compile(rf"\bUiTags\.{by_tag[tag]}\b")
            for name, text in tests.items():
                found = len(pattern.findall(text))
                if found:
                    counts[name] = counts.get(name, 0) + found
        element["tests_referencing"] = counts
    return inventory


def read_bounds(directory: Path) -> dict[str, list[dict]]:
    """The layout capture's bounds files: frame name -> its files, in the order the capture lists the states.

    The capture writes <directory>/<frame>/<screen>__<state>.json (and a PNG next to each, which is not read).
    """
    if not directory.is_dir():
        raise FileNotFoundError(f"no such directory: {directory}")
    frames: dict[str, list[dict]] = {}
    for frame_dir in sorted(p for p in directory.iterdir() if p.is_dir()):
        files = [json.loads(f.read_text(encoding="utf-8")) for f in sorted(frame_dir.glob("*.json"))]
        if files:
            frames[frame_dir.name] = sorted(files, key=lambda f: f["order"])
    if not frames:
        raise FileNotFoundError(f"no bounds files under {directory} (expected <frame>/<screen>__<state>.json)")
    return frames


def _pick(files: list[dict], screen: str, tag: str) -> dict | None:
    """Where `tag` sits on `screen`: in the first captured state where it is on show, else the first where it is
    present at all. None when no state of the screen has it."""
    present = [(f, f["elements"][tag]) for f in files if f["screen"] == screen and tag in f["elements"]]
    if not present:
        return None
    state, box = next(((f, b) for f, b in present if b["visible"]), present[0])
    return {
        "state": f"{state['screen']}__{state['state']}",
        **{k: box[k] for k in ("x", "y", "width", "height", "visible", "count")},
        "seen_in_states": len(present),
    }


def _measure(element: dict, frames: dict[str, list[dict]]) -> dict | None:
    """The element's measurement per frame, or None when no frame has it. An element that holds several controls
    (test_tag_variants) is measured by its own tag, and each control it holds is listed under `variants`."""
    measured: dict[str, dict] = {}
    for frame, files in frames.items():
        own = _pick(files, element["screen"], element["test_tag_new"]) if element["test_tag_new"] else None
        variants = {t: m for t in element.get("test_tag_variants", []) if (m := _pick(files, element["screen"], t))}
        if own is None and not variants:
            continue
        measured[frame] = {**(own or {}), **({"variants": variants} if variants else {})}
    return measured or None


def _set_field(element: dict, field: str, value: dict | None) -> None:
    """Sets element[field]; a new today_measured goes right after `today`, so the file reads in order."""
    if field in element or field != "today_measured":
        element[field] = value
        return
    items = list(element.items())
    element.clear()
    for key, existing in items:
        element[key] = existing
        if key == "today":
            element[field] = value


def merge_bounds(inventory: dict, frames: dict[str, list[dict]], field: str = "today_measured") -> list[str]:
    """Writes each element's measurement into element[field] and returns the problems found, one line each: every
    element with a tag that no captured state of its screen has, and every bounds file for a screen the inventory
    does not have."""
    if field not in MEASURED_FIELDS:
        raise ValueError(f"field must be one of {MEASURED_FIELDS}, not {field!r}")
    found: list[str] = []
    screens = {s["id"] for s in inventory["screens"]}
    for frame, files in frames.items():
        for f in files:
            if f["screen"] not in screens:
                found.append(f"{frame}/{f['screen']}__{f['state']} is for a screen that is not in the inventory")
    for element in inventory["elements"]:
        if not element_tags(element):
            _set_field(element, field, None)
            found.append(f"{element['id']} on {element['screen']} has no test tag, so it cannot be measured")
            continue
        measured = _measure(element, frames)
        _set_field(element, field, measured)
        if measured is None:
            found.append(
                f"{element['id']} ({', '.join(element_tags(element))}) on {element['screen']} was never found in any "
                "captured state"
            )
    inventory["meta"][field] = MEASURED_NOTES[field]
    return found


def merge_command(argv: list[str]) -> int:
    try:
        directory = Path(argv[argv.index("--merge-bounds") + 1])
        field = argv[argv.index("--field") + 1] if "--field" in argv else "today_measured"
        frames = read_bounds(directory)
        inventory = load_inventory()
        found = merge_bounds(inventory, frames, field)
    except IndexError:
        print("usage: ui_inventory.py --merge-bounds DIR [--field today_measured|after_measured]")
        return 2
    except (FileNotFoundError, ValueError) as error:
        print(error)
        return 2
    INVENTORY_JSON.write_text(json.dumps(inventory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    INVENTORY_CSV.write_bytes(csv_bytes(inventory))
    measured = sum(1 for e in inventory["elements"] if e.get(field))
    print(f"wrote {field} for {measured} of {len(inventory['elements'])} elements from {', '.join(frames)}")
    for line in found:
        print(line)
    return 0


def main(argv: list[str]) -> int:
    if "--check" in argv:
        found = problems()
        for line in found:
            print(line)
        return 1 if found else 0
    if "--merge-bounds" in argv:
        return merge_command(argv)
    if "--refresh-tests" in argv:
        inventory = refresh_tests_referencing(load_inventory())
        INVENTORY_JSON.write_text(json.dumps(inventory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"updated tests_referencing in {INVENTORY_JSON.relative_to(REPO_ROOT).as_posix()}")
    INVENTORY_CSV.write_bytes(csv_bytes(load_inventory()))
    print(f"wrote {INVENTORY_CSV.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
