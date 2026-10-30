"""The Android redesign hand-back check (#191): is the designer's return complete and consistent with the inventory?

  uv run scripts/design_return_check.py                       # exit 1 and one line per problem, else exit 0
  uv run scripts/design_return_check.py --set-implemented ID [ID ...]   # a re-skin ticket marks the elements it built
  uv run scripts/design_return_check.py --set-implemented ID --not-implemented   # and takes the mark back

It reads docs/android-redesign/ui-inventory.json (the source of truth) and docs/android-redesign/design-return/:
the redesign map, the follow-up map (which supersedes the first for the ids it revises), tokens.json and the
annotated frames. The check fails when
  - an inventory id has no entry in either map, or its status is not the first word of `meta.status_values`;
  - a map entry is for an id the inventory does not have (a renamed id), or is not the same element (the id, screen,
    kind, name, function, text, visible_when, navigates_to and test tags must equal the inventory's: the measured
    fields `today_measured` / `after_measured` and anything else that is not identity are ignored, because a hand-back
    copy was made before they existed);
  - an id was dropped without status `removed` and a reason in `notes`;
  - an `added_elements` id lacks its screen's prefix, or is not unique;
  - a non-removed element lacks one of the `new_*` fields (`new_text` may stay null: the copy did not change);
  - a screen (or splash / app icon) has no frame named <screen>__<state>.png, a frame is named for no known screen,
    a frame has no legend, or a frame the follow-up map lists is missing;
  - tokens.json lacks a required group;
  - `implementation-status.json` (the `implemented` flag per element, false until a re-skin ticket builds it) does
    not list every inventory and added id exactly once with a true or false.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REDESIGN = REPO_ROOT / "docs" / "android-redesign"
RETURN = REDESIGN / "design-return"
INVENTORY_JSON = REDESIGN / "ui-inventory.json"
MAP_JSON = RETURN / "ui-redesign-map.json"
FOLLOWUP_JSON = RETURN / "ui-redesign-map-followup.json"
TOKENS_JSON = RETURN / "tokens.json"
LEGENDS_JSON = RETURN / "annotation-legends.json"
FRAMES_DIR = RETURN / "annotated"
IMPLEMENTED_JSON = REDESIGN / "implementation-status.json"

# What makes two records the same element. Everything else (sizes, measured fields, tests_referencing, the
# designer's own `redesign` block) is allowed to differ.
IDENTITY_FIELDS = (
    "id", "screen", "kind", "name", "function", "text", "visible_when", "navigates_to",
    "test_tag_today", "test_tag_new", "test_tag_variants",
)
NEW_FIELDS = (
    "status", "new_screen", "new_region", "new_order", "new_width", "new_height", "new_style", "new_test_tag",
    "notes",
)
# Where the first map's copy of an element is allowed to differ from today's inventory, and why. The map was drawn
# from the inventory as it stood on 2026-10-25; these changed afterwards. An entry that stops differing is reported
# (stale), so the list cannot grow quietly.
KNOWN_DRIFT: dict[str, tuple[tuple[str, ...], str]] = {
    "paywall.back": (
        ("kind", "name", "function", "text", "visible_when", "navigates_to", "test_tag_today"),
        "#186 added the Back control after the first map (the follow-up map's drift_notes)",
    ),
    "scan_error.next_step_button": (
        ("test_tag_variants",),
        "#188 tagged each of the five next-step controls after the first map",
    ),
}
# Screens the frames cover that are not screens of the inventory.
EXTRA_FRAME_SCREENS = ("splash", "app_icon")
FRAME_NAME = re.compile(r"^([a-z_]+?)__([a-z0-9_]+)$")
REQUIRED_TOKEN_GROUPS = {
    "colors": ("brand", "deep", "support", "neutral", "proposed"),
    "typography": ("families", "styles"),
    "material3_mapping": ("primary", "shapes", "custom_colors_outside_m3"),
    "sizes_dp": ("touch_target_min", "button", "text_field", "credit_chip"),
    "radii_dp": ("input", "card", "pill"),
    "opacity": ("scrim",),
}
REQUIRED_TOKEN_KEYS = ("gradients", "spacing_dp", "screen_margin_dp", "elevation", "motion")


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_parts() -> dict:
    """Everything the check reads, as plain data, so a test can break one part of a copy."""
    return {
        "inventory": _read(INVENTORY_JSON),
        "map": _read(MAP_JSON),
        "followup": _read(FOLLOWUP_JSON),
        "tokens": _read(TOKENS_JSON),
        "legends": _read(LEGENDS_JSON),
        "frames": sorted(p.stem for p in FRAMES_DIR.glob("*.png")),
        "implemented": _read(IMPLEMENTED_JSON) if IMPLEMENTED_JSON.exists() else None,
    }


def status_words(inventory: dict) -> set[str]:
    """The first word of each `meta.status_values` entry, plus `added` for an element the designer added."""
    return {value.split()[0] for value in inventory["meta"]["status_values"]} | {"added"}


def effective_entries(first: dict, followup: dict) -> list[dict]:
    """The map's records: the first map's, with the follow-up's `revised_elements` replacing the first map's entry
    for the same id (the first map is never edited), then the follow-up's own elements."""
    revised = {e["id"]: e for e in followup.get("revised_elements", [])}
    entries: list[dict] = []
    for element in first["elements"]:
        if element["id"] in revised:
            entries.append({**element, "redesign": revised[element["id"]]["redesign"]})
        else:
            entries.append(element)
    entries.extend(followup["elements"])
    return entries


def _identity(element: dict) -> dict:
    return {field: element.get(field) for field in IDENTITY_FIELDS}


def _screen_prefixes(inventory: dict) -> dict[str, set[str]]:
    """Id prefix (`picker` in `picker.logo`) -> the screens that prefix is used for in the inventory."""
    prefixes: dict[str, set[str]] = {}
    for element in inventory["elements"]:
        prefixes.setdefault(element["id"].split(".")[0], set()).add(element["screen"])
    return prefixes


def _missing_new_fields(redesign: dict) -> list[str]:
    return [f for f in NEW_FIELDS if redesign.get(f) in (None, "")]


def element_problems(parts: dict) -> list[str]:
    inventory = parts["inventory"]
    allowed = status_words(inventory)
    by_id = {e["id"]: e for e in inventory["elements"]}
    entries = effective_entries(parts["map"], parts["followup"])
    found: list[str] = []

    seen: dict[str, int] = {}
    for entry in entries:
        seen[entry["id"]] = seen.get(entry["id"], 0) + 1
    for element_id, count in sorted(seen.items()):
        if count > 1:
            found.append(f"{element_id} has {count} entries across the two maps")

    entry_by_id = {e["id"]: e for e in entries}
    for element_id in sorted(by_id):
        if element_id not in entry_by_id:
            found.append(f"{element_id} is in the inventory but has no entry in either map (dropped without status removed)")

    for entry in entries:
        element_id = entry["id"]
        redesign = entry.get("redesign") or {}
        status = redesign.get("status")
        if element_id not in by_id:
            found.append(f"{element_id} is in a map but not in the inventory (renamed or invented id)")
            continue
        if status not in allowed:
            found.append(f"{element_id} has status {status!r}, which is not one of {sorted(allowed)}")
        if status == "added":
            found.append(f"{element_id} is an inventory element but has status 'added'")
        allowed_drift, _reason = KNOWN_DRIFT.get(element_id, ((), ""))
        differs = [f for f, v in _identity(by_id[element_id]).items() if _identity(entry).get(f) != v]
        changed = [f for f in differs if f not in allowed_drift]
        if changed:
            found.append(f"{element_id} is not the same element as the inventory's (differs in {', '.join(changed)})")
        stale = [f for f in allowed_drift if f not in differs]
        if stale:
            found.append(f"KNOWN_DRIFT for {element_id} lists {', '.join(stale)}, which no longer differ (remove them)")
        if status == "removed":
            if not (redesign.get("notes") or "").strip():
                found.append(f"{element_id} is removed with no reason in notes")
            continue
        missing = _missing_new_fields(redesign)
        if missing:
            found.append(f"{element_id} lacks {', '.join(missing)}")
        inventory_tag = by_id[element_id].get("test_tag_new")
        if inventory_tag and redesign.get("new_test_tag") not in (None, inventory_tag):
            found.append(
                f"{element_id} has new_test_tag {redesign.get('new_test_tag')!r} but the inventory's test_tag_new is "
                f"{inventory_tag!r}"
            )
    return found


def added_problems(parts: dict) -> list[str]:
    inventory = parts["inventory"]
    prefixes = _screen_prefixes(inventory)
    taken = {e["id"] for e in inventory["elements"]}
    found: list[str] = []
    for added in parts["map"].get("added_elements", []) + parts["followup"].get("added_elements", []):
        element_id = added["id"]
        redesign = added.get("redesign") or {}
        prefix = element_id.split(".")[0]
        if element_id in taken:
            found.append(f"{element_id} is an added element but the id is already used")
        taken.add(element_id)
        if "." not in element_id:
            found.append(f"{element_id} is an added element with no screen prefix")
        elif prefix in prefixes and added.get("screen") not in prefixes[prefix]:
            found.append(f"{element_id} has the prefix of {sorted(prefixes[prefix])} but is on {added.get('screen')!r}")
        elif prefix not in prefixes and prefix != added.get("screen"):
            found.append(f"{element_id} has a prefix that is no screen's and is not its own screen {added.get('screen')!r}")
        if redesign.get("status") != "added":
            found.append(f"{element_id} is an added element but its status is {redesign.get('status')!r}, not 'added'")
        missing = _missing_new_fields(redesign)
        if missing:
            found.append(f"{element_id} lacks {', '.join(missing)}")
    return found


def frame_problems(parts: dict) -> list[str]:
    inventory = parts["inventory"]
    screens = {s["id"] for s in inventory["screens"]} | set(EXTRA_FRAME_SCREENS)
    frames = set(parts["frames"])
    found: list[str] = []
    drawn: set[str] = set()
    for name in sorted(frames):
        match = FRAME_NAME.match(name)
        if not match or match.group(1) not in screens:
            found.append(f"frame {name}.png is not named <screen>__<state>.png for a known screen")
        else:
            drawn.add(match.group(1))
    for screen in sorted(screens - drawn):
        found.append(f"screen {screen} has no frame named {screen}__<state>.png")
    for name in sorted(frames - set(parts["legends"])):
        found.append(f"frame {name}.png has no entry in annotation-legends.json")
    for name in sorted(set(parts["legends"]) - frames):
        found.append(f"annotation-legends.json names {name}, which has no frame")
    listed = parts["followup"].get("frames", {})
    for name in sorted(set(listed.get("new", [])) | set(listed.get("reissued", []))):
        if name not in frames:
            found.append(f"the follow-up map lists frame {name}.png, which is missing")
    return found


def token_problems(parts: dict) -> list[str]:
    tokens = parts["tokens"]
    found: list[str] = []
    for group, keys in REQUIRED_TOKEN_GROUPS.items():
        if not isinstance(tokens.get(group), dict):
            found.append(f"tokens.json lacks the group {group}")
            continue
        for key in keys:
            if key not in tokens[group]:
                found.append(f"tokens.json lacks {group}.{key}")
    for key in REQUIRED_TOKEN_KEYS:
        if key not in tokens:
            found.append(f"tokens.json lacks {key}")
    return found


def implemented_problems(parts: dict) -> list[str]:
    status = parts.get("implemented")
    if status is None:
        return [f"{IMPLEMENTED_JSON.name} is missing (the implemented flag per element)"]
    flags = status.get("implemented")
    if not isinstance(flags, dict):
        return [f"{IMPLEMENTED_JSON.name} has no `implemented` map of id -> true or false"]
    wanted = {e["id"] for e in parts["inventory"]["elements"]}
    wanted |= {a["id"] for a in parts["map"].get("added_elements", []) + parts["followup"].get("added_elements", [])}
    found = [f"{i} has no implemented flag" for i in sorted(wanted - set(flags))]
    found += [f"implemented has {i}, which is no inventory or added id" for i in sorted(set(flags) - wanted)]
    found += [f"{i} has implemented {v!r}, not true or false" for i, v in sorted(flags.items()) if not isinstance(v, bool)]
    return found


def problems(parts: dict | None = None) -> list[str]:
    parts = parts or load_parts()
    return (
        element_problems(parts) + added_problems(parts) + frame_problems(parts) + token_problems(parts)
        + implemented_problems(parts)
    )


def set_implemented(ids: list[str], value: bool) -> list[str]:
    """Writes the flag for each id; returns the ids that are not known (nothing is written when any is unknown)."""
    status = _read(IMPLEMENTED_JSON)
    unknown = [i for i in ids if i not in status["implemented"]]
    if unknown:
        return unknown
    for element_id in ids:
        status["implemented"][element_id] = value
    IMPLEMENTED_JSON.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return []


def main(argv: list[str]) -> int:
    if "--set-implemented" in argv:
        ids = [a for a in argv[argv.index("--set-implemented") + 1:] if not a.startswith("--")]
        if not ids:
            print("usage: design_return_check.py --set-implemented ID [ID ...] [--not-implemented]")
            return 2
        unknown = set_implemented(ids, "--not-implemented" not in argv)
        for element_id in unknown:
            print(f"{element_id} is not an element id in {IMPLEMENTED_JSON.name}")
        return 2 if unknown else 0
    found = problems()
    for line in found:
        print(line)
    if found:
        return 1
    parts = load_parts()
    flags = parts["implemented"]["implemented"]
    print(
        f"ok: {len(parts['inventory']['elements'])} inventory ids, {len(parts['map']['added_elements'])} added, "
        f"{len(parts['frames'])} frames; {sum(flags.values())} of {len(flags)} elements implemented"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
