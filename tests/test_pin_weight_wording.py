"""No shipped source says "tongue weight" for the fifth-wheel hitch load (#48).

The product is scoped to fifth-wheel and gooseneck trailers, where the hitch
load is Pin Weight (src/hdttools/CONTEXT.md). The breakdown notes are pinned by
the shared golden-vector fixture, but the Android truck-entry hint and every
other string in the three apps are not, so this scans the shipped sources of
each surface. Bumper-pull Tongue Weight (#2) is not built; when it ships, the
hitch-type-specific code can be exempted here by name.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.minor]

ROOT = Path(__file__).resolve().parent.parent

# Shipped source per surface: Core (and so the API), Streamlit, Web, Android.
SHIPPED = (
    (ROOT / "src" / "hdttools", {".py"}),
    (ROOT / "streamlit_app", {".py"}),
    (ROOT / "web" / "src", {".ts", ".tsx"}),
    (ROOT / "android" / "app" / "src" / "main", {".kt", ".xml"}),
)


def _shipped_files():
    for base, suffixes in SHIPPED:
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix in suffixes:
                yield path


def test_the_scan_covers_every_surface():
    seen = {path.relative_to(ROOT).parts[0] for path in _shipped_files()}
    assert seen == {"src", "streamlit_app", "web", "android"}


def test_no_shipped_source_says_tongue_weight():
    hits = [
        f"{path.relative_to(ROOT)}:{number}: {line.strip()}"
        for path in _shipped_files()
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if "tongue" in line.lower()
    ]
    assert hits == []
