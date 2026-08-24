# vulture whitelist (roadmap item #10) - hand-reviewed from real
# `uv run vulture src/hdttools streamlit_app` output, 2026-08-24.
#
# Every entry below was individually confirmed to be a genuine false
# positive, not blindly kept from vulture's own --make-whitelist stub -
# see ARCHIVE_DEAD_CODE.md for how each category was verified. Grouped
# by *why* vulture can't see the real usage, not by file, so a future
# addition to any of these categories has an obvious place to go.
#
# Run: uv run vulture src/hdttools streamlit_app vulture_whitelist.py

# --- FastAPI route handlers: reachable only via @app.post(...)
# decorators (src/hdttools/api/main.py) - vulture has no framework-
# routing awareness, so a handler with no direct in-repo caller looks
# identical to a genuinely dead function. Confirmed real: each name
# below is the function immediately under a real @app.post(...) line.
extract_truck_tag
extract_trailer_tag
extract_scale_ticket
create_breakdown

# --- Pydantic/dataclass model fields (src/hdttools/api/schemas.py,
# src/hdttools/models.py) - class-level annotated attributes are a
# well-known vulture false-positive class: they're "used" by the
# framework (Pydantic's validation/serialization, dataclasses' __init__)
# reading the class's __annotations__, never by a direct name reference
# vulture's AST walk can see. Listed once each (vulture whitelist
# entries aren't file-scoped, so a name shared across schemas.py and
# models.py - e.g. vin, cold_pressure_kpa - only needs one entry here).
cold_pressure_kpa
cold_pressure_psi
vin
vehicle_type
standalone_weight_lb
gawr_per_axle_kg
gawr_per_axle_lb
ticket_number
weigh_number
time
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
badgeLabel
barColor
actualLabel
limitLabel
status
headline
subline
bandBg
breakdownItems
verdictInfo

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
