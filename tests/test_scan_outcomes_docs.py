"""The written Scan outcomes (#115) stay in step with their fixture and their readers.

The glossary entry in workers/scan-proxy/CONTEXT.md and test-vectors/scan_outcomes.json say the same
thing in two places on purpose: the entry is what people read, the fixture is what both clients are
tested against (web/src/scanOutcomes.test.ts, android .../ScanOutcomesFixtureTest.kt). Nothing else
fails if one is edited and the other is not, so this does. It also pins the README's account of the
two Worker answers that were wrong or missing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.minor]

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = json.loads((ROOT / "test-vectors" / "scan_outcomes.json").read_text(encoding="utf-8"))
WORKER_CONTEXT = (ROOT / "workers" / "scan-proxy" / "CONTEXT.md").read_text(encoding="utf-8")


def _outcomes_table() -> dict[str, list[str]]:
    """The glossary entry's table, by case number: the cells after the case name."""
    entry = WORKER_CONTEXT.split("**Scan outcomes**:", 1)[1].split("**Time limits**:", 1)[0]
    rows = {}
    for line in entry.splitlines():
        if not line.startswith("| ") or line.startswith("| ---") or line.startswith("| # "):
            continue
        cells = [cell.strip().replace("*", "") for cell in line.strip().strip("|").split("|")]
        rows[cells[0]] = cells[2:]
    return rows


TABLE = _outcomes_table()
YES_NO = {True: "yes", False: "no"}
REFUNDED = {"yes": "yes", "no": "no", "not_applicable": "n/a"}


def test_the_glossary_table_has_a_row_for_every_fixture_case_and_no_other():
    assert sorted(TABLE) == sorted(row["case"] for row in FIXTURE["cases"])


@pytest.mark.parametrize("row", FIXTURE["cases"], ids=lambda row: row["id"])
def test_a_glossary_row_agrees_with_its_fixture_row(row):
    spent, refunded, keeps_id, try_again, _next_step = TABLE[row["case"]]
    assert spent == row["spent"]
    assert refunded.split(" ")[0] == REFUNDED[row["refunded"]]
    assert keeps_id == YES_NO[row["retryKeepsRequestId"]]
    assert try_again == YES_NO[row["offersTryAgain"]]


@pytest.mark.parametrize("path", ["web/CONTEXT.md", "android/CONTEXT.md", "CONTEXT-MAP.md"])
def test_the_clients_and_the_context_map_point_at_the_scan_outcomes(path):
    text = (ROOT / path).read_text(encoding="utf-8")
    assert "Scan outcomes" in text
    assert "scan_outcomes.json" in text


def _readme_error(code: str) -> str:
    """The README's bullet for one Worker error code (a bullet runs until the next one)."""
    readme = (ROOT / "workers" / "scan-proxy" / "README.md").read_text(encoding="utf-8")
    bullets = readme.split("**Errors:**", 1)[1].split("**CORS.**", 1)[0].split("\n- ")
    (bullet,) = [b for b in bullets if f"`{code}`" in b]
    return " ".join(bullet.split())


def test_the_readme_says_billing_error_may_or_may_not_have_charged():
    bullet = _readme_error("billing_error")
    assert "may or may not have been charged" in bullet
    assert "spending never happened" not in bullet


def test_the_readme_lists_extraction_failed_no_refund_with_its_meaning():
    bullet = _readme_error("extraction_failed_no_refund")
    assert "502" in bullet
    assert "not given back" in bullet  # charged, and the refund failed too
