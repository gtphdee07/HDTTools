"""Glossary hygiene for web/CONTEXT.md's Pro term (#86).

**Pro** is the Web app's name for the paid plan. RevenueCat's own "entitlement"
object backs it, but the scan-proxy glossary reserves **Entitlement** for a
different question (which system is the source of truth for paid status), so the
Pro entry must not stretch that word, and must say what to call Pro instead.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.minor]

ROOT = Path(__file__).resolve().parent.parent
WEB_CONTEXT = ROOT / "web" / "CONTEXT.md"


def _term_entry(text: str, term: str) -> str:
    """The glossary entry for **term**: from its heading line to the next blank-line-separated term."""
    match = re.search(rf"^\*\*{re.escape(term)}\*\*:\n(.*?)(?=\n\n\*\*|\Z)", text, re.DOTALL | re.MULTILINE)
    assert match, f"no **{term}** entry in {WEB_CONTEXT}"
    return match.group(1)


def test_pro_entry_has_an_avoid_line():
    entry = _term_entry(WEB_CONTEXT.read_text(encoding="utf-8"), "Pro")
    assert re.search(r"^_Avoid_:", entry, re.MULTILINE)


def test_pro_entry_does_not_define_pro_as_an_entitlement():
    entry = _term_entry(WEB_CONTEXT.read_text(encoding="utf-8"), "Pro")
    assert not re.search(r"\ba RevenueCat entitlement\b", entry)

def test_pro_entry_points_at_the_reserved_entitlement_term():
    entry = _term_entry(WEB_CONTEXT.read_text(encoding="utf-8"), "Pro")
    assert "workers/scan-proxy/CONTEXT.md" in entry
    assert "Entitlement" in entry
