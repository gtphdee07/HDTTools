# vulture whitelist (roadmap item #10) - hand-reviewed from real
# `uv run vulture src/hdttools streamlit_app` output, 2026-08-24 (the run now also scans scripts/, #150:
# `uv run vulture src/hdttools streamlit_app scripts vulture_whitelist.py`).
#
# Every entry below was individually confirmed to be a genuine false
# positive, not blindly kept from vulture's own --make-whitelist stub -
# see ARCHIVE_DEAD_CODE.md for how each category was verified. Grouped
# by *why* vulture can't see the real usage, not by file, so a future
# addition to any of these categories has an obvious place to go.
#
# Run: uv run vulture src/hdttools streamlit_app scripts vulture_whitelist.py

# --- Dataclass model fields (src/hdttools/models.py) - class-level
# annotated attributes are a well-known vulture false-positive class:
# they're "used" by dataclasses' __init__/asdict reading the class's
# __annotations__, never by a direct name reference vulture's AST walk
# can see.
cold_pressure_kpa
cold_pressure_psi
vin
vehicle_type
standalone_weight_lb
gawr_per_axle_kg
gawr_per_axle_lb
ticket_number
weigh_number
scale_number
location_address
city
steer_axle_lb
drive_axle_lb
trailer_axle_lb
gross_weight_lb
company
commodity
tractor_number
trailer_number
source_image

# --- Public library API: this repo's `hdttools` package is meant to be
# used directly as a library (see README.md's "Underlying toolkit"
# section), not just internally - "no in-repo caller" is expected and
# correct here, not a sign of dead code.
#
# read_scale_ticket/read_trailer_tag/read_truck_tag are re-exported from
# __init__.py's own conditional export block, confirmed real there.
read_scale_ticket
read_trailer_tag
read_truck_tag
#
# read_trailer_tag_ocr/read_truck_tag_ocr aren't re-exported from
# __init__.py (only scale_ticket_ocr.read_scale_ticket - same name as
# the vision version - gets that treatment, per README.md's "Tesseract"
# section), but confirmed real by reading each function directly: same
# file-picker + review-form + save CLI-tool shape as the vision
# versions above, just reached via `from hdttools.truck_tag_ocr import
# read_truck_tag_ocr` instead of the package root.
read_trailer_tag_ocr
read_truck_tag_ocr

# --- scripts/ (#150): dev tooling is scanned too. Each name below is called
# only from tests/ or by pytest itself, and each is a real definition, not
# dead code.
#
# pytest calls a plugin hook by its name.
pytest_collection_modifyitems
# Test-support helpers the regression and External tests import
# (tests/test_pass_pool_regression.py, test_fail_pool_regression.py,
# test_claude_vision_external.py).
registered_doc_types
resolve_pass_pool_image
resolve_fail_pool_image
load_cases
new_mismatches
# The ledger's query function, named in verification_ledger.py's docstring as
# the way a caller asks "is this context verified"; tests/test_verification_ledger.py
# exercises it, no script calls it today.
is_verified
