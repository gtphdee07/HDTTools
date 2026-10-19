"""Function tests for scripts/coverage_lib.py's coverage-report parsers.

Extracted from tests/test_coverage_gate.py 2026-08-24 (roadmap item #7)
when the parsers themselves moved out of coverage_gate.py into this
shared module - see coverage_lib.py's own docstring for why. Pure
functions taking already-read text/data, no subprocess I/O. The Android
JVM decision-logic tests (#130) read fake report HTML from tmp_path.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import coverage_lib  # noqa: E402
from tests._coverage_fakes import package_page, write_fake_jvm_report  # noqa: E402

pytestmark = [pytest.mark.core, pytest.mark.minor]


def test_parse_android_report_computes_percent_from_missed_and_total():
    html = (
        '<tfoot><tr><td>Total</td><td class="bar">4,259 of 14,731</td>'
        '<td class="ctr2">71%</td></tr></tfoot>'
    )
    percent = coverage_lib.parse_android_report(html)
    assert percent == pytest.approx((14731 - 4259) / 14731 * 100)


def test_parse_android_report_raises_when_total_row_is_missing():
    with pytest.raises(ValueError, match="Total"):
        coverage_lib.parse_android_report("<html>no coverage table here</html>")


# Real per-package row snippet shape (top-level JaCoCo index.html, item #8
# 2026-09-09): a package below the exclusion threshold - e.g. an isolated
# research spike like ui.experiments.cameraoverlay, never reachable from
# production, same spirit as BoundOCR being kept outside Python's
# coverage.py `source` - shouldn't drag down the app-wide real number.
_REPORT_WITH_TWO_PACKAGES = (
    '<table><tbody>'
    '<tr><td id="a0"><a href="com.rigcheck.app.ui.experiments.cameraoverlay/index.html" '
    'class="el_package">com.rigcheck.app.ui.experiments.cameraoverlay</a></td>'
    '<td class="bar" id="b0">'
    '<img src="jacoco-resources/redbar.gif" width="27" height="10" title="1,636" alt="1,636"/>'
    '<img src="jacoco-resources/greenbar.gif" width="2" height="10" title="154" alt="154"/>'
    '</td><td class="ctr2" id="c0">8%</td></tr>'
    '<tr><td id="a1"><a href="com.rigcheck.app.ui.screens/index.html" '
    'class="el_package">com.rigcheck.app.ui.screens</a></td>'
    '<td class="bar" id="b1">'
    '<img src="jacoco-resources/redbar.gif" width="18" height="10" title="1,079" alt="1,079"/>'
    '<img src="jacoco-resources/greenbar.gif" width="101" height="10" title="6,016" alt="6,016"/>'
    '</td><td class="ctr2" id="c1">84%</td></tr>'
    '</tbody></table>'
    '<tfoot><tr><td>Total</td><td class="bar">2,715 of 8,885</td><td class="ctr2">69%</td></tr></tfoot>'
)


def test_parse_android_report_excludes_a_named_package_from_the_total():
    # Excluding cameraoverlay's 1,636 missed/1,790 total should leave
    # exactly screens' own 1,079 missed/7,095 total.
    percent = coverage_lib.parse_android_report(
        _REPORT_WITH_TWO_PACKAGES,
        exclude_packages=("com.rigcheck.app.ui.experiments.cameraoverlay",),
    )
    assert percent == pytest.approx((7095 - 1079) / 7095 * 100)


def test_parse_android_report_with_no_exclusions_matches_the_unmodified_total():
    percent = coverage_lib.parse_android_report(_REPORT_WITH_TWO_PACKAGES)
    assert percent == pytest.approx((8885 - 2715) / 8885 * 100)


def test_parse_android_report_raises_for_an_exclude_package_not_in_the_report():
    with pytest.raises(ValueError, match="not_a_real_package"):
        coverage_lib.parse_android_report(
            _REPORT_WITH_TWO_PACKAGES, exclude_packages=("not_a_real_package",)
        )


def test_parse_python_report_reads_percent_covered():
    data = {"totals": {"percent_covered": 79.4392523364486, "num_statements": 963}}
    assert coverage_lib.parse_python_report(data) == pytest.approx(79.4392523364486)


def test_parse_web_report_reads_statements_pct():
    data = {
        "total": {
            "lines": {"pct": 95.2},
            "statements": {"pct": 91.41},
            "functions": {"pct": 86.84},
            "branches": {"pct": 85.44},
        }
    }
    assert coverage_lib.parse_web_report(data) == pytest.approx(91.41)


def test_parse_scan_proxy_output_reads_all_files_line():
    output = (
        "ℹ file           | line % | branch % | funcs % | uncovered lines\n"
        "ℹ  claude.ts     | 100.00 |   100.00 |  100.00 | \n"
        "ℹ ---------------------------------------------------------------\n"
        "ℹ all files      | 100.00 |   100.00 |  100.00 | \n"
        "ℹ ---------------------------------------------------------------\n"
    )
    assert coverage_lib.parse_scan_proxy_output(output) == pytest.approx(100.0)


def test_parse_scan_proxy_output_reads_a_partial_percentage():
    output = "ℹ all files      | 79.44 |   60.00 |  70.00 | \n"
    assert coverage_lib.parse_scan_proxy_output(output) == pytest.approx(79.44)


def test_parse_scan_proxy_output_raises_when_summary_line_is_missing():
    with pytest.raises(ValueError, match="all files"):
        coverage_lib.parse_scan_proxy_output("no coverage output here")


# --- Android JVM decision-logic coverage (#130) ---------------------------


def test_parse_jacoco_package_classes_reads_missed_and_total_per_class():
    page = package_page(
        [("Mixed", 3, 75), ("AllCovered", 0, 66), ("NeverRun", 27, 0), ("Empty", 0, 0)]
    )
    rows = coverage_lib.parse_jacoco_package_classes("com.x", page)
    assert [(r.fqn, r.missed, r.total) for r in rows] == [
        ("com.x.Mixed", 3, 78),
        ("com.x.AllCovered", 0, 66),
        ("com.x.NeverRun", 27, 27),
        ("com.x.Empty", 0, 0),
    ]


def test_parse_jacoco_package_classes_keeps_lambda_and_inner_class_names_whole():
    page = package_page(
        [
            ("ScanHttp.scan.2.new Callback() {...}", 0, 68),
            ("ScanUiState.Error", 10, 15),
        ]
    )
    names = [r.name for r in coverage_lib.parse_jacoco_package_classes("com.x", page)]
    assert names == ["ScanHttp.scan.2.new Callback() {...}", "ScanUiState.Error"]


def test_parse_jacoco_package_classes_unescapes_html_in_names():
    page = package_page([("Foo.<init>", 1, 1)])
    assert coverage_lib.parse_jacoco_package_classes("com.x", page)[0].name == "Foo.<init>"


def test_read_jvm_report_walks_everypackage_page(tmp_path):
    root = write_fake_jvm_report(
        tmp_path,
        {"com.x.domain": [("Breakdown", 0, 100)], "com.x.data": [("Manager", 5, 45)]},
    )
    rows = coverage_lib.read_jvm_report(root)
    assert sorted((r.fqn, r.missed, r.total) for r in rows) == [
        ("com.x.data.Manager", 5, 50),
        ("com.x.domain.Breakdown", 0, 100),
    ]


def test_read_jvm_report_raises_when_the_index_lists_no_packages(tmp_path):
    (tmp_path / "index.html").write_text("<html>nothing</html>", encoding="utf-8")
    with pytest.raises(ValueError, match="package"):
        coverage_lib.read_jvm_report(tmp_path)


def _scope(**overrides) -> "coverage_lib.AndroidLogicScope":
    base = dict(
        allow=(),
        waived_classes={},
        waived_packages={},
        watched_packages=("com.x.domain", "com.x.data", "com.x.ui"),
    )
    base.update(overrides)
    return coverage_lib.AndroidLogicScope(**base)


def _rows(spec: dict[str, list[tuple[str, int, int]]]):
    out = []
    for pkg, classes in spec.items():
        out += coverage_lib.parse_jacoco_package_classes(pkg, package_page(classes))
    return out


def test_measure_android_logic_aggregates_instructions_over_the_allow_list_only():
    rows = _rows({"com.x.domain": [("A", 10, 90), ("B", 0, 100)], "com.x.ui": [("Huge", 900, 100)]})
    scope = _scope(
        allow=("com.x.domain.A", "com.x.domain.B"),
        waived_classes={"com.x.ui.Huge": "wrapper"},
    )
    result = coverage_lib.measure_android_logic(rows, scope)
    assert (result.missed, result.total) == (10, 200)
    assert result.percent == pytest.approx(95.0)


def test_measure_android_logic_counts_inner_and_lambda_classes_with_their_outer_class():
    rows = _rows(
        {
            "com.x.data": [
                ("ScanHttp", 0, 41),
                ("ScanHttp.scan.2.new Callback() {...}", 11, 68),
                ("ScanHttp.scan.2.new Function1() {...}", 4, 0),
            ]
        }
    )
    result = coverage_lib.measure_android_logic(rows, _scope(allow=("com.x.data.ScanHttp",)))
    assert (result.missed, result.total) == (15, 124)
    assert result.unclassified == []


def test_measure_android_logic_does_not_confuse_a_class_with_one_that_shares_its_prefix():
    rows = _rows({"com.x.data": [("ScanApiClient", 46, 0), ("ScanApiClientKt", 0, 199)]})
    result = coverage_lib.measure_android_logic(rows, _scope(allow=("com.x.data.ScanApiClientKt",)))
    assert (result.missed, result.total) == (0, 199)
    assert result.unclassified == ["com.x.data.ScanApiClient"]


def test_measure_android_logic_lists_a_watched_class_on_neither_list_without_counting_it():
    rows = _rows(
        {
            "com.x.domain": [("A", 0, 100)],
            "com.x.data": [("NewThing", 50, 0)],
            "com.x": [("MainActivity", 55, 0)],
        }
    )
    result = coverage_lib.measure_android_logic(rows, _scope(allow=("com.x.domain.A",)))
    assert result.unclassified == ["com.x.data.NewThing"]  # the root package is not watched
    assert result.percent == pytest.approx(100.0)


def test_measure_android_logic_ignores_waived_classes_and_packages_whatever_their_coverage():
    rows = _rows(
        {
            "com.x.domain": [("A", 0, 100)],
            "com.x.ui.screens": [("Screen", 800, 0)],
            "com.x.ui.experiments.cameraoverlay": [("Spike", 900, 0)],
            "com.x.data": [("Backend", 226, 0), ("Backend.Companion", 88, 0)],
        }
    )
    scope = _scope(
        allow=("com.x.domain.A",),
        waived_packages={"com.x.ui.screens": "compose", "com.x.ui.experiments": "spikes"},
        waived_classes={"com.x.data.Backend": "provider wrapper"},
    )
    result = coverage_lib.measure_android_logic(rows, scope)
    assert (result.missed, result.total) == (0, 100)
    assert result.unclassified == []


def test_measure_android_logic_reports_an_allow_listed_class_missing_from_the_report():
    rows = _rows({"com.x.domain": [("A", 0, 100)]})
    scope = _scope(allow=("com.x.domain.A", "com.x.domain.Gone"))
    result = coverage_lib.measure_android_logic(rows, scope)
    assert result.stale == ["com.x.domain.Gone"]


def test_measure_android_logic_raises_when_nothing_on_the_allow_list_is_measured():
    rows = _rows({"com.x.domain": [("A", 0, 100)]})
    with pytest.raises(ValueError, match="allow"):
        coverage_lib.measure_android_logic(rows, _scope(allow=("com.x.domain.Gone",)))


def test_load_android_logic_scope_reads_the_toml_file(tmp_path):
    path = tmp_path / "scope.toml"
    path.write_text(
        'watched_packages = ["com.x.domain"]\n'
        'allow = ["com.x.domain.A"]\n'
        '[waive_classes]\n"com.x.data.B" = "wrapper"\n'
        '[waive_packages]\n"com.x.ui.screens" = "compose"\n',
        encoding="utf-8",
    )
    scope = coverage_lib.load_android_logic_scope(path)
    assert scope.allow == ("com.x.domain.A",)
    assert scope.waived_classes == {"com.x.data.B": "wrapper"}
    assert scope.waived_packages == {"com.x.ui.screens": "compose"}
    assert scope.watched_packages == ("com.x.domain",)


def test_load_android_logic_scope_rejects_a_class_that_is_both_allowed_and_waived(tmp_path):
    path = tmp_path / "scope.toml"
    path.write_text(
        'allow = ["com.x.A"]\nwatched_packages = []\n[waive_classes]\n"com.x.A" = "why"\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="com.x.A"):
        coverage_lib.load_android_logic_scope(path)


def test_load_android_logic_scope_rejects_a_waiver_with_no_reason(tmp_path):
    path = tmp_path / "scope.toml"
    path.write_text(
        'allow = []\nwatched_packages = []\n[waive_classes]\n"com.x.B" = ""\n', encoding="utf-8"
    )
    with pytest.raises(ValueError, match="com.x.B"):
        coverage_lib.load_android_logic_scope(path)
