"""Function tests for scripts/pass_pool.py's pass-pool resolver -- the
schema + minimal random-selection mechanism from
FUTURE_CONSTRAINED_RANDOM_OCR_TESTING.md's "pass-pool" design (roadmap
item #13, NEXT_STEPS.md).

Proves a doc_type resolves to one of its registered real images, with
that image's exact golden_fields.json "photos" entry (fields + any
known_ocr_limitations) attached -- the pass-pool schema is a membership
index over "photos", not a second, drift-prone copy of the same field
data. A future pass-pool regression test (not written yet) will call
this resolver with an unseeded Random() to get "different answers back
... versus the same ones, all the time" (the project owner's own framing
for why this needs to be random at execution time); these tests pass an
explicit seed so the assertions stay deterministic.
"""

import random
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))  # pass_pool.py is a standalone module, like coverage_lib.py

import pass_pool  # noqa: E402


def test_resolve_pass_pool_image_returns_a_registered_truck_photo():
    filename, photo = pass_pool.resolve_pass_pool_image("truck_tag", rng=random.Random(0))
    assert filename == "AddieTag.jpg"
    assert photo["doc_type"] == "truck_tag"
    assert photo["fields"]["gvwr_lb"] == 14000.0


def test_resolve_pass_pool_image_returns_a_registered_trailer_photo():
    filename, photo = pass_pool.resolve_pass_pool_image("trailer_tag", rng=random.Random(0))
    assert filename == "GooseTag.jpg"
    assert photo["doc_type"] == "trailer_tag"
    # A pass-pool image doesn't have to be perfect on every field, only
    # already-understood -- the resolver must carry a known limitation
    # through, not silently strip it, so a future pass-pool test can
    # still xfail that one field the same way test_real_photo_ocr_accuracy.py does.
    assert "gawr_per_axle_lb" in photo["known_ocr_limitations"]


def test_resolve_pass_pool_image_raises_for_a_doc_type_with_no_pool_yet():
    with pytest.raises(ValueError, match="scale_ticket"):
        pass_pool.resolve_pass_pool_image("scale_ticket", rng=random.Random(0))


def test_resolve_pass_pool_image_is_reproducible_for_a_given_seed():
    first = pass_pool.resolve_pass_pool_image("truck_tag", rng=random.Random(42))
    second = pass_pool.resolve_pass_pool_image("truck_tag", rng=random.Random(42))
    assert first == second
