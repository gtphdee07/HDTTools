"""Pure coverage-report parsers shared by coverage_gate.py and the
dashboard (generate_dashboard.py, roadmap item #7).

Extracted from coverage_gate.py 2026-08-24 (roadmap item #7's dashboard
plan) so the release gate and the dashboard both parse each platform's
coverage report the same way, from one place, instead of duplicating
(and risking drifting) the same regex/JSON-key logic in two scripts.
Each platform's number is its own tool's native metric (Android:
instruction coverage from JaCoCo; Python: statement coverage from
coverage.py; Web: statement coverage from Vitest's v8 provider;
scan-proxy: line coverage from Node's --experimental-test-coverage) -
these are genuinely different metrics, not normalized to one, since each
is what that platform's own TESTING.md already documents and no single
metric is available across all four tools.
"""

from __future__ import annotations

import html
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path


def parse_android_report(html: str, exclude_packages: tuple[str, ...] = ()) -> float:
    """Instruction coverage from the JaCoCo HTML report's Total row, minus
    any package named in exclude_packages.

    Exclusion exists for isolated research spikes that live inside the
    app module's main/ source set but are never reachable from production
    (e.g. ui.experiments.cameraoverlay, item #18) - same spirit as
    an experiment being kept outside Python's coverage.py `source`
    config so an intentionally-unwired experiment doesn't drag
    down the real, shippable-code number (item #8, found 2026-09-09: the
    camera-overlay spike alone dropped Android's measured coverage from
    71% to 64.28%).
    """
    match = re.search(
        r'<tfoot><tr><td>Total</td><td class="bar">([\d,]+) of ([\d,]+)</td>',
        html,
    )
    if not match:
        raise ValueError("No 'Total' row found in the JaCoCo HTML report")
    missed = int(match.group(1).replace(",", ""))
    total = int(match.group(2).replace(",", ""))
    if total == 0:
        raise ValueError("JaCoCo report's Total row reports zero instructions")

    for package in exclude_packages:
        pkg_missed, pkg_total = _android_package_instruction_counts(html, package)
        missed -= pkg_missed
        total -= pkg_total

    if total == 0:
        raise ValueError("Excluding all requested packages leaves zero instructions")
    return (total - missed) / total * 100


def _android_package_instruction_counts(html: str, package: str) -> tuple[int, int]:
    """Missed and total instructions for one package row in the top-level
    JaCoCo index.html. Matched by CSS class (redbar.gif = missed,
    greenbar.gif = covered) rather than image position, since a
    0%- or 100%-covered package's row only has one of the two <img> tags."""
    row_match = re.search(
        r'<a href="[^"]*index\.html" class="el_package">'
        + re.escape(package)
        + r'</a></td><td class="bar"[^>]*>(.*?)</td>',
        html,
        re.DOTALL,
    )
    if not row_match:
        raise ValueError(f"Package {package!r} not found in the JaCoCo HTML report")
    missed, covered = _jacoco_bar_counts(row_match.group(1))
    return missed, missed + covered


def _jacoco_bar_counts(bar_html: str) -> tuple[int, int]:
    """(missed, covered) instructions from a JaCoCo bar cell: redbar.gif is
    missed, greenbar.gif is covered, and a fully covered, fully missed or
    empty row has only one or neither of the two <img> tags."""
    missed_match = re.search(r'redbar\.gif"[^>]*title="([\d,]+)"', bar_html)
    covered_match = re.search(r'greenbar\.gif"[^>]*title="([\d,]+)"', bar_html)
    missed = int(missed_match.group(1).replace(",", "")) if missed_match else 0
    covered = int(covered_match.group(1).replace(",", "")) if covered_match else 0
    return missed, covered


# --- Android JVM decision-logic coverage (#130) ---------------------------
#
# The Android gate measures JaCoCo's JVM unit-test report over an allow-list
# of decision-logic classes only (android/coverage-logic.toml). Compose
# screens, navigation, view-model wiring and provider wrappers carry no
# number: device and External tests verify them.


@dataclass(frozen=True)
class ClassCoverage:
    package: str
    name: str  # simple name within the package; inner and lambda classes keep their dotted suffix
    missed: int
    total: int

    @property
    def fqn(self) -> str:
        return f"{self.package}.{self.name}"


@dataclass(frozen=True)
class AndroidLogicScope:
    allow: tuple[str, ...]
    waived_classes: dict[str, str]  # fully qualified class -> reason
    waived_packages: dict[str, str]  # package (and its subpackages) -> reason
    watched_packages: tuple[str, ...]  # a class here on neither list is reported as unclassified


@dataclass(frozen=True)
class LogicCoverage:
    missed: int
    total: int
    stale: list[str]  # allow-listed entries with no class in the report
    unclassified: list[str]  # classes in a watched package on neither list

    @property
    def percent(self) -> float:
        return (self.total - self.missed) / self.total * 100


_PACKAGE_LINK = re.compile(r'<a href="[^"]*index\.html" class="el_package">([^<]+)</a>')
_CLASS_ROW = re.compile(
    r'<a href="[^"]*" class="el_class">([^<]+)</a></td>'
    r'<td class="bar" id="b\d+"(?:/>|>(.*?)</td>)',
    re.DOTALL,
)


def parse_jacoco_package_classes(package: str, html_text: str) -> list[ClassCoverage]:
    """One ClassCoverage per el_class row of a JaCoCo package page."""
    rows = []
    for name, bar in _CLASS_ROW.findall(html_text):
        missed, covered = _jacoco_bar_counts(bar)
        rows.append(ClassCoverage(package, html.unescape(name), missed, missed + covered))
    return rows


def read_jvm_report(report_dir: Path) -> list[ClassCoverage]:
    """Every class row of a JaCoCo HTML report directory (the index.html
    lists the packages, each package has its own <package>/index.html)."""
    index = (report_dir / "index.html").read_text(encoding="utf-8")
    packages = _PACKAGE_LINK.findall(index)
    if not packages:
        raise ValueError(f"No package rows found in the JaCoCo report at {report_dir}")
    rows: list[ClassCoverage] = []
    for package in packages:
        page = (report_dir / package / "index.html").read_text(encoding="utf-8")
        rows += parse_jacoco_package_classes(package, page)
    return rows


def load_android_logic_scope(path: Path) -> AndroidLogicScope:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    scope = AndroidLogicScope(
        allow=tuple(data.get("allow", ())),
        waived_classes=dict(data.get("waive_classes", {})),
        waived_packages=dict(data.get("waive_packages", {})),
        watched_packages=tuple(data.get("watched_packages", ())),
    )
    for name in scope.allow:
        if name in scope.waived_classes:
            raise ValueError(f"{name} is on both the allow list and the waiver list")
    for name, reason in {**scope.waived_classes, **scope.waived_packages}.items():
        if not reason.strip():
            raise ValueError(f"The waiver for {name} has no reason")
    return scope


def _is_or_nests_under(fqn: str, entry: str) -> bool:
    """True for the class itself and its inner and lambda classes, not for a
    class that merely shares a name prefix (ScanApiClient vs ScanApiClientKt)."""
    return fqn == entry or fqn.startswith(entry + ".")


def measure_android_logic(
    rows: list[ClassCoverage], scope: AndroidLogicScope
) -> LogicCoverage:
    """Aggregate instruction coverage over the allow-listed classes. A class
    is decided by its most specific entry: allow-listed, waived by name, then
    waived by package; otherwise it is unclassified when it sits in a watched
    package."""
    missed = total = 0
    matched: set[str] = set()
    unclassified: list[str] = []
    for row in rows:
        allowed = [e for e in scope.allow if _is_or_nests_under(row.fqn, e)]
        waived = [e for e in scope.waived_classes if _is_or_nests_under(row.fqn, e)]
        if allowed and (not waived or max(map(len, allowed)) > max(map(len, waived))):
            missed += row.missed
            total += row.total
            matched.update(allowed)
        elif waived:
            continue
        elif any(_is_or_nests_under(row.package, p) for p in scope.waived_packages):
            continue
        elif any(_is_or_nests_under(row.package, p) for p in scope.watched_packages):
            unclassified.append(row.fqn)
    if total == 0:
        raise ValueError("No allow-listed class has any instructions in the JaCoCo report")
    stale = [entry for entry in scope.allow if entry not in matched]
    return LogicCoverage(missed, total, stale, unclassified)


def parse_python_report(data: dict) -> float:
    """Statement coverage from pytest-cov's --cov-report=json output."""
    return data["totals"]["percent_covered"]


def parse_web_report(data: dict) -> float:
    """Statement coverage from Vitest's v8-provider coverage-summary.json."""
    return data["total"]["statements"]["pct"]


def parse_scan_proxy_output(text: str) -> float:
    """Line coverage from Node's --experimental-test-coverage summary."""
    match = re.search(r"all files\s*\|\s*([\d.]+)\s*\|", text)
    if not match:
        raise ValueError(
            "No 'all files' coverage summary line found in scan-proxy's test output"
        )
    return float(match.group(1))
