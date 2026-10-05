"""External-tier test for the "anthropic" surface (ADR-0008; originally
added for roadmap item #16, now also this surface's per-surface suite for
issue #37). Real Claude vision API calls against
`src/hdttools/vision_client.py` - the Python consumer of the Anthropic
API (the other is `workers/scan-proxy/src/claude.ts`, covered by its own
`[anthropic]`-tagged suite at
`workers/scan-proxy/src/external/anthropic.external.test.ts`). Fails the
run entirely when no real `ANTHROPIC_API_KEY` is set (the autouse
`_require_api_key` fixture below) - per ADR-0008, a missing key is a
failure, not a silent skip, so the wrapper never records a false pass for
a surface it never actually exercised.

Depth coverage (ADR-0008's four depths), per surface:
- reachable and authenticated: test_a_bad_key_is_rejected_with_a_real_auth_error
  below (free - a bad key is rejected before any billed call).
- error contract (malformed image):
  test_a_corrupted_image_is_rejected_before_any_billed_model_call below
  (free - same reasoning as scan.weekly.test.ts's equivalent case: an
  undecodable image is rejected at the request layer before any model
  call happens).
- response shape + full journey: the parametrized
  test_claude_vision_extraction_matches_documented_pass_pool_state below,
  one real doc_type per pass-pool entry (3 total, matching
  scripts/external_manifest/surfaces/anthropic.json's max_paid_calls).
  This is the only billed case in this file.

Real cost: exactly one real, billed Claude vision API call per doc type
(this project's own precedent: ~$0.01-0.03 per call, see roadmap items
#13/#15). Per this project's standing "don't re-run a real-money test
casually while iterating" convention, this file should be run
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

import anthropic
import pytest

from hdttools import scale_ticket, trailer_tag, truck_tag
from hdttools.vision_client import extract_via_claude, image_bytes_and_media_type

_EXAMPLE_DOCS = Path(__file__).resolve().parent.parent / "ExampleDocs"
_REPO_ROOT = _EXAMPLE_DOCS.parent

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))  # pass_pool.py is a standalone module, like coverage_lib.py

import pass_pool  # noqa: E402

_EXTRACTORS = {
    "truck_tag": truck_tag.extract_truck_tag_fields,
    "trailer_tag": trailer_tag.extract_trailer_tag_fields,
    "scale_ticket": scale_ticket.extract_scale_ticket_fields,
}

# "anthropic" is this surface's own pytest marker (ADR-0008: "marker for
# pytest" is the surface tag) - scripts/run_external_pytest.py's
# EXTERNAL_SURFACES filtering matches on it via a plain "mark.anthropic"
# text search (scripts/external_wrapper.py's tagged_in, --tag-style marker).
pytestmark = [pytest.mark.external, pytest.mark.anthropic]


@pytest.fixture(autouse=True)
def _require_api_key():
    """A missing key fails the run (ADR-0008), not a silent/soft skip - a
    plain `pytest.mark.skipif` would let a key-less invocation exit 0 ("no
    tests failed"), which the wrapper would record as a false `pass` for a
    surface never actually exercised (ADR-0008 explicitly rejects this: "the
    dashboard would show green for surfaces never exercised"). Collection
    still succeeds either way - this only runs at test setup, same timing a
    `skipif` would use, so a key-less *default* run (which deselects
    `external` entirely) never reaches this fixture. The wrapper's own
    `-Skip` records `skipped` without ever invoking pytest, so it never hits
    this path either."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.fail(
            "External test credentials missing: ANTHROPIC_API_KEY is not set in the "
            "environment. Export it before running, or pass -Skip to the repo-root "
            "test-external.ps1 (records `skipped` instead of failing, and leaves the "
            "surface stale).",
            pytrace=False,
        )

# Trivial, schema-shape-agnostic tool config - the two cases below exercise
# extract_via_claude's own request/auth/decoding behavior, not any specific
# doc type's schema, so there is no need to reuse a real one.
_PROBE_TOOL = {
    "system_prompt": "You are reading a vehicle document.",
    "tool_name": "record_probe",
    "tool_description": "Record a probe field.",
    "schema": {"type": "object", "properties": {"value": {"type": ["string", "null"]}}, "required": ["value"]},
}


def test_a_bad_key_is_rejected_with_a_real_auth_error(monkeypatch):
    """[anthropic] reachable and authenticated: a wrong ANTHROPIC_API_KEY
    gets the real 401 from the Anthropic API. Free to run - rejected before
    any billed model call happens."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-api03-invalid-external-test-key")
    image_bytes, media_type = image_bytes_and_media_type(_EXAMPLE_DOCS / "AddieTag.jpg")

    with pytest.raises(anthropic.AuthenticationError):
        extract_via_claude(image_bytes=image_bytes, media_type=media_type, **_PROBE_TOOL)


def test_a_corrupted_image_is_rejected_before_any_billed_model_call():
    """[anthropic] error contract: a truncated/undecodable image is
    rejected by the real API before any model call. Free to run - same
    reasoning as workers/scan-proxy/src/weekly/scan.weekly.test.ts's
    equivalent through-the-Worker case."""
    full_bytes = (_REPO_ROOT / "streamlit_app" / "assets" / "wtwt_logo.png").read_bytes()
    truncated = full_bytes[:200]

    with pytest.raises(anthropic.BadRequestError):
        extract_via_claude(image_bytes=truncated, media_type="image/png", **_PROBE_TOOL)


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
