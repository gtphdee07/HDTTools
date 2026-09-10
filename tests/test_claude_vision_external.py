"""External-tier test (first for this Python platform, roadmap item #16):
real Claude vision API calls, one per doc type, against an existing
pass-pool image (scripts/vehicle_discovery.py's registered vehicles via
scripts/pass_pool.py - no new fixtures needed). Skipped entirely when no
real `ANTHROPIC_API_KEY` is set, mirroring
`workers/scan-proxy/src/release/scan.release.test.ts`'s skip-if-
missing-key pattern - that platform's only existing precedent for this
class of test; Python has none before this file
(`tests/TESTING.md`'s "No External suite exists here today" line, now
stale, is corrected alongside this file per roadmap item #16 step 7).

Real cost: each parametrized case is one real, billed Claude vision API
call (this project's own precedent: ~$0.01-0.03 per call, see roadmap
items #13/#15). Per this project's standing "don't re-run a real-money
test casually while iterating" convention, this file should be run
deliberately and sparingly - not as part of a routine `uv run pytest -q`
pass (nothing marks it xdist/skip-by-default at collection beyond the
real env var check below, matching how the Minor/Major/External model
already scopes which suites a session actually needs, per the root
`TESTING.md`).

Tolerance note - a deliberate difference from
`tests/test_pass_pool_regression.py`: that suite asserts strict
`mismatched == known_ocr_limitations` because it runs routinely and
wants an *improvement* (a previously-limited field suddenly matching)
surfaced just as loudly as a regression. This file only asserts no *new*
mismatch beyond what's already documented - a documented
known_ocr_limitations entry (every one on record today is a Tesseract-
only regex/OCR quirk: a digit-drop, a two-column layout jumble) actually
reading correctly under Claude vision is an expected, welcome outcome
given roadmap item #17's real finding (100% correct on every real photo
tested), not a surprise worth flagging as a failure on a test this
expensive to re-run.
"""

from __future__ import annotations

import mimetypes
import os
import random
import sys
from pathlib import Path

import pytest

from hdttools import scale_ticket, trailer_tag, truck_tag

_EXAMPLE_DOCS = Path(__file__).resolve().parent.parent / "ExampleDocs"

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))  # pass_pool.py is a standalone module, like coverage_lib.py

import pass_pool  # noqa: E402

_EXTRACTORS = {
    "truck_tag": truck_tag.extract_truck_tag_fields,
    "trailer_tag": trailer_tag.extract_trailer_tag_fields,
    "scale_ticket": scale_ticket.extract_scale_ticket_fields,
}

pytestmark = pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="requires a real ANTHROPIC_API_KEY",
)


@pytest.mark.parametrize("doc_type", sorted(_EXTRACTORS))
def test_claude_vision_extraction_matches_documented_pass_pool_state(doc_type):
    filename, photo = pass_pool.resolve_pass_pool_image(doc_type, rng=random.Random())
    image_path = _EXAMPLE_DOCS / filename
    media_type = mimetypes.guess_type(image_path.name)[0] or "image/jpeg"

    extracted = _EXTRACTORS[doc_type](image_path.read_bytes(), media_type)

    known_limitations = set(photo.get("known_ocr_limitations", {}))
    mismatched = {
        field: (extracted.get(field), expected)
        for field, expected in photo["fields"].items()
        if extracted.get(field) != expected
    }
    new_mismatches = set(mismatched) - known_limitations

    assert not new_mismatches, (
        f"{filename} ({doc_type}): real Claude vision extraction produced a mismatch "
        f"not covered by documented known_ocr_limitations - "
        f"{ {field: mismatched[field] for field in new_mismatches} } "
        f"(got, expected). This is a real regression in the Claude-vision extraction "
        f"path itself (vision_client.extract_via_claude or the matching "
        f"extract_*_fields function), not an accuracy-tuning signal."
    )
