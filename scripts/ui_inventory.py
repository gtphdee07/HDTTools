"""The Android UI inventory (#188): docs/android-redesign/ui-inventory.json is the source of truth.

  uv run scripts/ui_inventory.py                  # rewrite ui-inventory.csv from the JSON
  uv run scripts/ui_inventory.py --check          # exit 1 if the CSV, UiTags.kt or the screens disagree with the JSON
  uv run scripts/ui_inventory.py --refresh-tests  # also recount which test files use each element's tag

The check fails when
  - ui-inventory.csv is not byte-identical to what this script writes from the JSON;
  - a `test_tag_new` in the JSON is not a value in the `UiTags` object, or a UiTags value is not in the JSON;
  - a UiTags constant is not used by any file under android/app/src/main outside UiTags.kt (a tag no screen sets);
  - a UiTags constant is not named in UiTagsDisplayedTest.kt, the instrumented test that shows every tagged
    element on a real screen (the elements that cannot be shown are listed in NOT_SHOWN_BY_THE_TEST).
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

# Elements that a screen test cannot show on a real screen, with the reason. They are still tagged.
NOT_SHOWN_BY_THE_TEST: dict[str, str] = {}

FIXED_COLUMNS = [
    "id", "screen", "kind", "name", "function", "text", "visible_when", "navigates_to",
]
TODAY_COLUMNS = ["region", "order", "width", "height", "style"]
REDESIGN_COLUMNS = [
    "status", "new_screen", "new_region", "new_order", "new_width", "new_height", "new_style", "new_text",
    "new_test_tag", "notes",
]
HEADER = (
    FIXED_COLUMNS
    + [f"today_{c}" for c in TODAY_COLUMNS]
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
    for name, tag in sorted(constants.items()):
        if not re.search(rf"\bUiTags\.{name}\b", used_in):
            found.append(f"UiTags.{name} ({tag!r}) is set by no screen or component under android/app/src/main")
        if tag not in NOT_SHOWN_BY_THE_TEST and not re.search(rf"\bUiTags\.{name}\b", test_text):
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


def main(argv: list[str]) -> int:
    if "--check" in argv:
        found = problems()
        for line in found:
            print(line)
        return 1 if found else 0
    if "--refresh-tests" in argv:
        inventory = refresh_tests_referencing(load_inventory())
        INVENTORY_JSON.write_text(json.dumps(inventory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"updated tests_referencing in {INVENTORY_JSON.relative_to(REPO_ROOT).as_posix()}")
    INVENTORY_CSV.write_bytes(csv_bytes(load_inventory()))
    print(f"wrote {INVENTORY_CSV.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
