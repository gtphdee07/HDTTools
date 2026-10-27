"""The beta feedback address (#182) is the same in the three places a tester can meet it.

Web's `FEEDBACK_EMAIL` (`web/src/betaKit.ts`), Android's `FEEDBACK_EMAIL`
(`android/.../ui/util/Feedback.kt`) and `docs/BETA_TESTER_GUIDE.md` are plain files read here, so the
check is offline. The Web test (`betaGuide.test.ts`) already checks the guide against Web; this one is
the only place Android is held to the same address.
"""

from __future__ import annotations

import re

import pytest

from tests._test_command_helpers import ANDROID, ROOT, WEB, read

pytestmark = [pytest.mark.core, pytest.mark.minor]

WEB_CONSTANT = WEB / "src" / "betaKit.ts"
ANDROID_CONSTANT = ANDROID / "app/src/main/java/com/rigcheck/app/ui/util/Feedback.kt"
GUIDE = ROOT / "docs" / "BETA_TESTER_GUIDE.md"
ADDRESS = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def web_address() -> str:
    found = re.search(r"export const FEEDBACK_EMAIL = '([^']+)'", read(WEB_CONSTANT))
    assert found, "web/src/betaKit.ts no longer has `export const FEEDBACK_EMAIL = '...'`"
    return found.group(1)


def android_address() -> str:
    found = re.search(r'const val FEEDBACK_EMAIL = "([^"]+)"', read(ANDROID_CONSTANT))
    assert found, "Feedback.kt no longer has `const val FEEDBACK_EMAIL = \"...\"`"
    return found.group(1)


def test_web_android_and_the_guide_carry_the_same_feedback_address():
    web, android = web_address(), android_address()
    assert web == android
    # Every address the guide names is the feedback address: a second one would send a tester elsewhere.
    assert set(ADDRESS.findall(read(GUIDE))) == {web}


def test_android_mailto_uses_the_constant_and_the_subject_web_uses():
    kotlin = read(ANDROID_CONSTANT)
    web = read(WEB_CONSTANT)
    assert re.search(r'const val FEEDBACK_MAILTO = "mailto:\$FEEDBACK_EMAIL\?subject=RigCheck%20feedback"', kotlin)
    assert "subject=${encodeURIComponent('RigCheck feedback')}" in web


def test_no_other_android_source_spells_the_address():
    # One Kotlin constant: any other file that names it would be a second copy to drift.
    address = android_address()
    sources = (ANDROID / "app/src").rglob("*.kt")
    copies = [p.name for p in sources if p != ANDROID_CONSTANT and address in read(p)]
    # The tests may spell it out to check what the app sends.
    assert [name for name in copies if not name.endswith("Test.kt")] == []
