"""The final comparison of the re-skinned Android app with the designer's map (#197).

  uv run scripts/design_compare.py            # print the report; exit 1 if anything is missing, unimplemented, out of
                                              # tolerance or out of order and not an accepted exception
  uv run scripts/design_compare.py --write    # also write docs/android-redesign/comparison-report.md
  uv run scripts/design_compare.py --check    # exit 1 if the committed report is not what this would write, or there is
                                              # a problem, or an accepted exception no longer applies

It reads the "after" half of the layout capture that `scripts/ui_inventory.py --merge-bounds DIR --field after_measured`
merged into docs/android-redesign/ui-inventory.json (`after_measured` per element, `added_after_measured` per element
the designer added) and the map's `new_*` fields (both maps, the follow-up superseding the first), at the reference frame
(412 x 892 dp). For each element the design keeps it lists

  - MISSING: the element was not found in any captured state (a removed element must not be found);
  - UNIMPLEMENTED: its flag in implementation-status.json is false;
  - SIZE: its measured width or height differs from `new_width` / `new_height` by more than the tolerance;
  - ORDER: in an annotated frame of the designer's (annotation-legends.json numbers the elements of each frame in reading
    order), an element numbered earlier starts below the whole of one numbered later, both measured in the capture's
    state of the same name (elements side by side start on the same row and pass).

TOLERANCE. A size the map gives as `56dp` is held to 1.5 dp. A size given with a `~` (the designer's reading of a frame:
`wrap (~44dp)`) is held to 4 dp or 10 percent, whichever is more. `fill` is the full width of the column the element is in,
which the map does not say, so it is held to being wide: at least half the screen and no wider than it (the layout tests
of the screens hold each one to its exact column). `wrap` has no size to check.

An element outside the tolerance, missing, unimplemented or out of order is a problem unless
docs/android-redesign/comparison-exceptions.json names it with a reason and the owner's acceptance; an exception that no
longer applies is reported too, so the list cannot grow stale.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import design_return_check  # noqa: E402  (a sibling script, found through the path line above)
import ui_inventory  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
REDESIGN = REPO_ROOT / "docs" / "android-redesign"
REPORT = REDESIGN / "comparison-report.md"
EXCEPTIONS = REDESIGN / "comparison-exceptions.json"

REFERENCE_FRAME = ui_inventory.REFERENCE_FRAME
FIXED_TOLERANCE_DP = 1.5
APPROX_TOLERANCE_DP = 4.0
APPROX_TOLERANCE_FRACTION = 0.10
FILL_MIN_FRACTION = 0.5
FILL_TOLERANCE_DP = 0.5
ORDER_TOLERANCE_DP = 0.5
KINDS = ("missing", "unimplemented", "size", "order")


@dataclass(frozen=True)
class Dim:
    """What the map says about one size: `fill`, `wrap` (maybe with a ~ estimate), or a fixed number of dp."""

    kind: str  # "fill" | "wrap" | "fixed" | "none"
    dp: float | None = None
    approx: bool = False

    @property
    def tolerance(self) -> float:
        if self.dp is None:
            return 0.0
        if not self.approx:
            return FIXED_TOLERANCE_DP
        return max(APPROX_TOLERANCE_DP, APPROX_TOLERANCE_FRACTION * self.dp)

    def text(self) -> str:
        if self.kind in ("fill", "none"):
            return self.kind
        number = "" if self.dp is None else f"{'~' if self.approx else ''}{self.dp:g}dp"
        return number if self.kind == "fixed" else f"wrap {number}".strip()


def parse_dim(text: str | None) -> Dim:
    """`fill`, `wrap`, `wrap (~44dp)`, `56dp`, `892dp`, or nothing."""
    if not text:
        return Dim("none")
    text = text.strip()
    number = re.search(r"(\d+(?:\.\d+)?)\s*dp", text)
    dp = float(number.group(1)) if number else None
    approx = "~" in text
    if text.startswith("fill"):
        return Dim("fill", dp, approx)
    if text.startswith("wrap"):
        return Dim("wrap", dp, approx)
    return Dim("fixed", dp, approx) if dp is not None else Dim("none")


@dataclass(frozen=True)
class Expected:
    """One element the design keeps, with what the map says about it."""

    id: str
    screen: str
    tag: str | None
    status: str
    width: Dim
    height: Dim
    added: bool


def expected_elements(parts: dict) -> list[Expected]:
    """Every element of both maps (the follow-up superseding the first), the designer's added elements last."""
    result: list[Expected] = []
    by_id = {e["id"]: e for e in parts["inventory"]["elements"]}
    for entry in design_return_check.effective_entries(parts["map"], parts["followup"]):
        redesign = entry["redesign"]
        inventory_element = by_id.get(entry["id"], entry)
        result.append(_expected(entry["id"], inventory_element["screen"], inventory_element.get("test_tag_new"), redesign, False))
    for added in parts["map"].get("added_elements", []) + parts["followup"].get("added_elements", []):
        redesign = added["redesign"]
        result.append(_expected(added["id"], added["screen"], redesign.get("new_test_tag"), redesign, True))
    return result


def _expected(element_id: str, screen: str, tag: str | None, redesign: dict, added: bool) -> Expected:
    return Expected(
        id=element_id,
        screen=redesign.get("new_screen") or screen,
        tag=tag,
        status=redesign["status"],
        width=parse_dim(redesign.get("new_width")),
        height=parse_dim(redesign.get("new_height")),
        added=added,
    )


def measurement(inventory: dict, expected: Expected) -> dict | None:
    """The element's measurement at the reference frame (see ui_inventory.merge_bounds), or None when never found."""
    if expected.added:
        measured = (inventory.get("added_after_measured") or {}).get(expected.id)
    else:
        element = next(e for e in inventory["elements"] if e["id"] == expected.id)
        measured = element.get("after_measured")
    return (measured or {}).get(REFERENCE_FRAME)


@dataclass(frozen=True)
class Problem:
    kind: str
    id: str
    detail: str


def size_problems(expected: Expected, measured: dict, frame_width: float) -> list[Problem]:
    found: list[Problem] = []
    # An element that holds several controls has no box of its own to measure.
    if "width" not in measured:
        return found
    for axis, dim in (("width", expected.width), ("height", expected.height)):
        value = measured[axis]
        if dim.kind == "fixed" or (dim.kind == "wrap" and dim.approx):
            if abs(value - dim.dp) > dim.tolerance:
                found.append(
                    Problem("size", expected.id, f"{axis} is {value:g} dp, the map says {dim.text()} (tolerance {dim.tolerance:g} dp)")
                )
    if expected.width.kind == "fill":
        # Only the width is compared: the capture's x is where an element's content starts (inside any padding the element
        # has), so a margin cannot be read from it. The exact column of each screen is checked on the device by that
        # screen's layout test (`Dim.Fill`).
        if not FILL_MIN_FRACTION * frame_width <= measured["width"] <= frame_width + FILL_TOLERANCE_DP:
            found.append(
                Problem("size", expected.id, f"width is {measured['width']:g} dp, but the map says fill on a {frame_width:g} dp screen")
            )
    return found


def order_problems(measured: dict[str, dict], legends: dict[str, list[dict]]) -> list[Problem]:
    """The designer's reading order, frame by frame. A legend (annotation-legends.json) numbers the elements of one
    annotated frame in reading order. Of the elements a frame numbers that were measured in that same captured state
    (the frame `<screen>__<state>` and the capture's state have the same name), one numbered earlier must not start
    below the whole of one numbered later. Elements side by side start on the same row, so they pass. The map's own
    `new_order` is not used: it is the number an element has in the first frame that shows it, so two elements are only
    comparable in a frame both are in."""
    found: list[Problem] = []
    for frame, legend in sorted(legends.items()):
        members = [
            (item["n"], item["id"], measured[item["id"]])
            for item in sorted(legend, key=lambda i: i["n"])
            if item["id"] in measured and measured[item["id"]].get("state") == frame
            and measured[item["id"]].get("visible") and "y" in measured[item["id"]]
        ]
        for (n_earlier, earlier, a), (n_later, later, b) in zip(members, members[1:]):
            if a["y"] >= b["y"] + b["height"] + ORDER_TOLERANCE_DP and b["height"] > 0:
                found.append(
                    Problem(
                        "order",
                        earlier,
                        f"in {frame}, is {n_earlier} before {later} ({n_later}) in the designer's numbering but starts at "
                        f"{a['y']:g} dp, below the end of it ({b['y'] + b['height']:g} dp)",
                    )
                )
    return found


def compare(parts: dict) -> tuple[list[Problem], dict]:
    """The problems found, and the counts the report states."""
    inventory = parts["inventory"]
    flags = (parts["implemented"] or {}).get("implemented", {})
    frame_width = float(REFERENCE_FRAME.split("x")[0])
    problems: list[Problem] = []
    measured_by_id: dict[str, dict] = {}
    counts = {"compared": 0, "removed": 0, "found": 0}
    for expected in expected_elements(parts):
        found = measurement(inventory, expected)
        if expected.status == "removed":
            counts["removed"] += 1
            if found is not None:
                problems.append(Problem("missing", expected.id, "the design removed this element, but it is still on a captured screen"))
            continue
        counts["compared"] += 1
        if not flags.get(expected.id):
            problems.append(Problem("unimplemented", expected.id, "its flag in implementation-status.json is false"))
        if found is None:
            problems.append(Problem("missing", expected.id, "not found in any captured state at 412x892"))
            continue
        counts["found"] += 1
        problems += size_problems(expected, found, frame_width)
        measured_by_id[expected.id] = found
    problems += order_problems(measured_by_id, parts["legends"])
    counts["elements"] = counts["compared"] + counts["removed"]
    return problems, counts


# ---- exceptions the owner accepted -------------------------------------------------------------------------


def load_exceptions() -> list[dict]:
    if not EXCEPTIONS.exists():
        return []
    exceptions = json.loads(EXCEPTIONS.read_text(encoding="utf-8"))["exceptions"]
    for exception in exceptions:
        if exception["kind"] not in KINDS:
            raise ValueError(f"{exception['id']}: the kind {exception['kind']!r} is not one of {KINDS}")
    return exceptions


def apply_exceptions(problems: list[Problem], exceptions: list[dict]) -> tuple[list[Problem], list[tuple[Problem, dict]], list[str]]:
    """(problems nobody accepted, problems with the exception that accepts them, exceptions that accept nothing).

    An exception matches a problem by its element id and kind; one without `accepted_by` is a proposal and accepts nothing."""
    accepted: list[tuple[Problem, dict]] = []
    open_problems: list[Problem] = []
    used: set[int] = set()
    for problem in problems:
        match = next(
            (
                (i, e)
                for i, e in enumerate(exceptions)
                if e["id"] == problem.id and e["kind"] == problem.kind and e.get("accepted_by")
            ),
            None,
        )
        if match is None:
            open_problems.append(problem)
        else:
            used.add(match[0])
            accepted.append((problem, match[1]))
    stale = [
        f"{e['kind']} exception for {e['id']} accepts nothing"
        for i, e in enumerate(exceptions)
        if e.get("accepted_by") and i not in used
    ]
    return open_problems, accepted, stale


# ---- the report --------------------------------------------------------------------------------------------


def report_text(parts: dict, problems: list[Problem], counts: dict, exceptions: list[dict]) -> str:
    open_problems, accepted, stale = apply_exceptions(problems, exceptions)
    lines = [
        "# Android redesign: the finished app against the map (#197)",
        "",
        "Generated by `uv run scripts/design_compare.py --write` from the layout capture merged into `ui-inventory.json` "
        "(`after_measured`, `added_after_measured`; `uv run scripts/ui_inventory.py --merge-bounds DIR --field after_measured`) "
        "and the designer's maps (`design-return/ui-redesign-map.json`, the follow-up map superseding it). "
        f"Reference frame {REFERENCE_FRAME} dp. Do not edit by hand.",
        "",
        "## Result",
        "",
        f"- {counts['elements']} elements in the maps ({counts['compared']} the design keeps, {counts['removed']} it removed).",
        f"- Found in a captured state: {counts['found']} of {counts['compared']}.",
        f"- Problems: **{len(open_problems)}** open, {len(accepted)} accepted by the owner.",
        "",
        "Tolerance: a size the map gives as `56dp` is held to ±1.5 dp; one given with a `~` (the designer's reading of a "
        "frame) to ±4 dp or 10 percent, whichever is more; `fill` to at least half the screen and no more than "
        "all of it; `wrap` has no size to check. Order: in each annotated frame of the designer's, of the elements it "
        "numbers that were measured in the capture's state of the same name, one numbered earlier never starts below the "
        "end of one numbered later.",
        "",
    ]
    for kind, title in (
        ("missing", "Not found in any captured state"),
        ("unimplemented", "Flag `implemented` is false"),
        ("size", "Outside the size tolerance"),
        ("order", "Out of order"),
    ):
        opens = [p for p in open_problems if p.kind == kind]
        accepts = [(p, e) for p, e in accepted if p.kind == kind]
        lines += [f"## {title}", ""]
        if not opens and not accepts:
            lines += ["None.", ""]
            continue
        for p in opens:
            lines.append(f"- `{p.id}`: {p.detail}. **Not accepted.**")
        for p, e in accepts:
            lines.append(f"- `{p.id}`: {p.detail}. Accepted by {e['accepted_by']} ({e.get('date', 'no date')}): {e['reason']}")
        lines.append("")
    if stale:
        lines += ["## Exceptions that no longer apply", ""] + [f"- {s}" for s in stale] + [""]
    return "\n".join(lines).rstrip() + "\n"


def run(write: bool, check: bool) -> int:
    parts = design_return_check.load_parts()
    problems, counts = compare(parts)
    exceptions = load_exceptions()
    open_problems, _accepted, stale = apply_exceptions(problems, exceptions)
    text = report_text(parts, problems, counts, exceptions)
    if write:
        REPORT.write_text(text, encoding="utf-8")
        print(f"wrote {REPORT.relative_to(REPO_ROOT).as_posix()}")
    status = 0
    if check and (not REPORT.exists() or REPORT.read_text(encoding="utf-8") != text):
        print("comparison-report.md is not what scripts/design_compare.py writes (run it with --write)")
        status = 1
    for problem in open_problems:
        print(f"{problem.kind.upper()} {problem.id}: {problem.detail}")
    for line in stale:
        print(line)
    if open_problems or stale:
        status = 1
    print(
        f"{counts['compared']} elements compared, {counts['found']} found, {len(open_problems)} open problems, "
        f"{len(problems) - len(open_problems)} accepted"
    )
    return status


def main(argv: list[str]) -> int:
    return run(write="--write" in argv, check="--check" in argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
