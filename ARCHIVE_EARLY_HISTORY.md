# Archive: early cross-platform fixes (pre-Android)

Detailed narrative for the earliest breakdown-logic fixes, from before the
Android app existed, moved out of `NEXT_STEPS.md` 2026-08-23 to keep that
file's current-status section cheap to read. Current status/roadmap lives
in `NEXT_STEPS.md` — this file is history, not a place to look for
"what's next."

**Entry-tag convention** (for `Grep`-based lookup instead of reading this
whole file): entries lead with `**Fix implemented`, `**Explicitly
deferred`, `**Superseded`, or similar bold tags — grep for those to filter
by type.

---

## ✅ Done: tongue-weight fallback fix (implemented 2026-08-15)

Discovered while reviewing the Android design handoff (`android/design/`,
not version-controlled — see its `README.md` for the full screen list):
the Android design's blank-field fallback for stand-alone weight assumes
`trailer_axle_lb` is **80% of the trailer's actual total weight** (a
standard fifth-wheel/gooseneck pin-weight rule of thumb — pin weight is
commonly cited as 15–25% of trailer weight). The web/Streamlit apps'
then-current fallback — when stand-alone weight is blank, just skip the
tongue-weight adjustment entirely — wasn't merely less accurate, **it was
wrong in the unsafe direction**: it implicitly assumed tongue weight is
0%, which could make an overweight trailer look compliant on the "Trailer
Total (GVWR)" check. Tongue weight physically transfers onto the truck's
axles when hitched and never appears in `trailer_axle_lb` — so comparing
`trailer_axle_lb` alone against the trailer's GVWR (a *total*-weight
rating) understates the real number whenever tongue/pin weight isn't
separately supplied.

**Fix implemented**: adopted the Android design's 80% assumption as the
correct default everywhere, per the plan above. (Later superseded — see
`ARCHIVE_WEB_STREAMLIT.md`'s skip-image/predictive-weight entry, which
replaced this fixed 80% with an adjustable `pin_weight_pct` parameter.)

- `src/hdttools/api/breakdown.py`: added `DEFAULT_AXLE_TO_TOTAL_RATIO = 0.8`
  as a named constant; when `standalone_weight_lb` is blank,
  `compute_breakdown()` set
  `trailer_total_actual = trailer_axle_lb / DEFAULT_AXLE_TO_TOTAL_RATIO`
  with the note text specified above. The exact-figure path
  (`standalone_weight_lb` provided) was unchanged.
- `tests/test_breakdown.py`'s omitted-stand-alone-weight test now asserts
  the `/0.8` estimate (renamed
  `test_trailer_total_estimates_from_axle_reading_when_standalone_weight_omitted`).
  No new test was needed for the provided-path regression — the existing
  provided/clamp-at-zero tests exercise the untouched `if` branch
  directly, so they already prove it. 54 backend tests pass.
- Streamlit imports `compute_breakdown` directly, so this one fix covered
  both frontends — verified live via Streamlit `AppTest`: a trailer that
  previously showed "1,120 lb to spare" (falsely safe, unadjusted axle
  reading vs. GVWR) now correctly showed "1,725 lb over" in red.
- Android's design already baked in this behavior as the intended
  default — nothing to change there once built.
- Not verified against the real `ExampleDocs/` photos specifically at the
  time (the fix was verified with synthetic numbers matching the existing
  test fixtures, not a fresh photo run) — low-risk since the math is a
  single division; this was never revisited but the fix has since been
  further validated indirectly by the real-photo tests added 2026-08-20.

## ✅ Done: portability pass (implemented 2026-08-13)

Goal: make RigCheck portable beyond the original web+DB setup (decided:
**no shared hosted backend**, each platform self-contained). Web app
(`web/` + `src/hdttools/api/`) became database-free — stateless
`POST /api/breakdown`, recent rigs are a client-side `localStorage` list
(`web/src/recentRigs.ts`). New self-contained Streamlit app
(`streamlit_app/`) reuses the same OCR/breakdown logic directly, no HTTP
hop, recent rigs persist to `~/.rigcheck/recent_rigs.json`. See
`streamlit_app/README.md`. `hdttools/__init__.py` tolerates a missing
`tkinter`; `ocr_common.py`'s Tesseract path detection also checks macOS/
Linux locations. Android: high-level roadmap only at this point (later
superseded by the monetization work — see `ARCHIVE_MONETIZATION.md`), no
OCR, needed its own Android Studio/Gradle project (later built — see
`ARCHIVE_ANDROID.md`).

54 backend tests passed; frontend typechecked/built clean; Streamlit
smoke-tested end-to-end against the real `ExampleDocs/` photos.

**Note found during this pass, not fixed:** `ExampleDocs/GooseTag.jpg`
and `ExampleDocs/AddieTag.jpg` are swapped relative to what their names
suggest — `GooseTag.jpg` is actually the Brinkley RV **trailer** tag and
`AddieTag.jpg` is the Ford **truck** tag (opposite of the CAT ticket's
"TRACTOR # GOOSE TRAILER # ADDIE"). Never renamed since that wasn't part
of the ask — any test/demo code should use them this way around; this is
still true as of 2026-08-23.

## ✅ Done: axle-count / tongue-weight plan (implemented 2026-08-13)

Two logic faults were fixed: `compute_breakdown()` hardcoded a 2-axle
trailer regardless of actual axle count, and "Trailer Total (GVWR)"
always excluded tongue weight. Fix: both `axle_count` (trailer) and
`standalone_weight_lb` (truck) became optional user-typed fields with
graceful fallback to the old behavior when left blank; the tongue-weight
estimate folded into the existing "Trailer Total (GVWR)" card rather than
a new one. See `tests/test_breakdown.py` for the five tests covering all
four scenarios (default axle count, custom axle count, tongue weight
omitted/provided, clamp-at-0). All 55 backend tests passed; frontend
typechecked/built clean.

**Explicitly deferred** (agreed as a good eventual direction, never
built): reading a *second* CAT scale ticket (unhitched) so
`standalone_weight_lb` comes from an actual measurement instead of a
typed number — `compute_breakdown`'s math wouldn't need to change again
for this, only where the value comes from. Still unbuilt as of
2026-08-23, not on the current roadmap.

**Superseded by the tongue-weight fallback fix above**: the omitted-
stand-alone-weight fallback described here ("skip the tongue-weight
adjustment entirely") turned out to be unsafe — see that section above
for the fix, itself later superseded by the adjustable `pin_weight_pct`
work in `ARCHIVE_WEB_STREAMLIT.md`.
