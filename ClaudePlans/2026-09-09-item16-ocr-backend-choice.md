# Item #16: build-time OCR-backend choice for Streamlit/web

## Context

`src/hdttools/truck_tag.py`/`trailer_tag.py`/`scale_ticket.py` already
contain a complete, working Claude-vision implementation
(`vision_client.extract_via_claude`), but nothing in the shipped app
(Streamlit or the FastAPI backend) ever calls it — both call only the
Tesseract-based `*_ocr.py` modules. This gap was recorded 2026-08-25
(`NEXT_STEPS.md` item #16) as a dropped original intent, never
implemented. Item #17's closure (2026-08-29) gives this a real basis for
a decision: Claude vision scored 100% correct on every real photo
tested, vs. Tesseract's confirmed, unresolved real-photo accuracy limits
(item #11) — so this is worth building now as an opt-in backend, not
deferred further.

Goal: a single build/env-level flag both `src/hdttools/api/main.py` and
`streamlit_app/app.py` read to choose Tesseract-style vs
Claude-vision-style extraction per doc_type, default unchanged
(Tesseract) so no existing deployment starts requiring
`ANTHROPIC_API_KEY` without opting in.

## Real constraints found (exploration, 2026-09-09)

- **No existing config/flag pattern in Python** (`src/hdttools/`,
  `streamlit_app/`) — zero hits for `os.environ`/`os.getenv`/dotenv/
  `pydantic-settings`. This is the first one; don't build more
  infrastructure than that implies.
- **Claude-vision side has no headless, pure function today** — only
  full interactive flows (`truck_tag.read_truck_tag()` etc., `truck_tag.py:62-95`)
  that drive a **tkinter** file dialog (`file_picker.select_image_file`)
  and a blocking `input()` (`prompt_vehicle_name`), then tkinter's
  `review_and_edit` and a SQLite save. None of that is usable from a web
  request handler or a Streamlit rerun.
- **`vision_client.extract_via_claude`** (`src/hdttools/vision_client.py:24-74`)
  takes `image_path: Path` and reads bytes off disk
  (`image_path.read_bytes()`, line 34) — both real callers
  (`main.py`'s `UploadFile`, Streamlit's `UploadedFile`) already have
  the image as in-memory bytes, so this needs to accept bytes directly
  rather than gaining a new temp-file-write indirection.
- **Return shape differs from the Tesseract side.** `*_ocr.py`'s
  `_parse_fields(text) -> dict` embeds an already-built `TireSpec`
  object per tire; `extract_via_claude`'s raw tool-input dict has each
  tire as a nested raw dict — the `TireSpec(**fields.pop("front_tire"))`
  unpacking that reconciles this currently lives inline inside
  `read_truck_tag()` (`truck_tag.py:78-79`), not in any reusable helper.
- **`main.py`** has three independent route functions (`main.py:60-75`),
  each hardcoded to one doc type — no existing per-doc-type dispatch
  table (unlike Streamlit's `_PARSERS` dict, `app.py:76-80`).
- **`app.py`**'s `_extract_fields` (`app.py:124-131`) returns
  `(fields, raw_text)`; `raw_text` feeds a "Raw OCR text (for debugging)"
  expander and — real edge found — an `elif not raw_text.strip():
  st.warning("Tesseract returned no text at all...")` at `app.py:169`
  that would misfire on every successful Claude-vision extraction
  (which has no raw OCR text at all) unless it's made backend-aware.
- **Python has no External test tier today** — `tests/TESTING.md:28-31`
  states this is N/A since nothing calls a real 3rd-party boundary. This
  work is the first thing that could, so that line goes stale and a new
  External suite is a genuine first for this platform (mirroring
  scan-proxy's real precedent: `workers/scan-proxy/src/release/scan.release.test.ts:37-63`'s
  skip-if-missing-key pattern, which has no Python equivalent yet).
- **`tests/test_ocr_output_key_contracts.py`** already guards exactly
  this class of risk (an OCR key mismatch silently dropping a field) for
  the Tesseract side — the new Claude-vision extractor functions need
  the same contract coverage, not a separate, weaker check.

## Steps

1. **`ocr_common.py`**: add `get_ocr_backend() -> str`, reading
   `os.getenv("HDTTOOLS_OCR_BACKEND", "tesseract")`, raising `ValueError`
   on anything other than `"tesseract"`/`"claude"` (fail loud, not a
   silent fallback — matches this project's established default). TDD:
   new test in `tests/test_ocr_common.py` (new file) for default,
   explicit valid values, and the invalid-value error.
2. **`vision_client.py`**: change `extract_via_claude`'s signature to
   accept `image_bytes: bytes, media_type: str` instead of `image_path:
   Path`, dropping the disk read. Update `tests/test_vision_client.py`
   first (TDD — call the new signature, watch it fail), then refactor.
   Update the three existing callers (`truck_tag.py`/`trailer_tag.py`/
   `scale_ticket.py`) to compute `image_path.read_bytes()` and
   `mimetypes.guess_type(image_path.name)[0] or "image/jpeg"` at the call
   site (a small local helper is fine if it avoids repeating the
   mimetypes line three times).
3. **New headless extractor functions**, one per doc type
   (`truck_tag.extract_truck_tag_fields(image_bytes, media_type) -> dict`,
   and matching `trailer_tag.extract_trailer_tag_fields`/
   `scale_ticket.extract_scale_ticket_fields`): pure functions wrapping
   `extract_via_claude` with that module's existing `_SYSTEM_PROMPT`/
   `_SCHEMA`, doing the same `TireSpec(**fields.pop(...))` unpacking
   `read_truck_tag()` does inline today — refactor `read_truck_tag()` to
   call the new function too, removing the duplication. TDD: new tests
   mocking `extract_via_claude` the same way `tests/test_vision_client.py`
   already does; add these functions' key sets to
   `tests/test_ocr_output_key_contracts.py`'s existing coverage.
4. **`main.py`**: replace the three near-duplicate route bodies with one
   small dispatch keyed by doc type (mirroring `app.py`'s `_PARSERS`
   shape) that branches on `get_ocr_backend()` — `"tesseract"` keeps
   today's exact behavior via `_ocr_upload`; `"claude"` reads the raw
   bytes, validates content-type the same way, calls the matching new
   extractor function, and normalizes any exception into
   `HTTPException(502, ...)` (an upstream-API failure, distinct from the
   existing 400 "not a valid image" case at `main.py:55-56`). TDD: extend
   `tests/test_api.py` with `HDTTOOLS_OCR_BACKEND=claude` cases per route
   (monkeypatch the env var + the new extractor function, matching the
   existing `monkeypatch.setattr(main.truck_tag_ocr, "_parse_fields",
   ...)` pattern at `test_api.py:87` etc.).
5. **`app.py`**: `_extract_fields` branches the same way — `"claude"`
   calls the matching extractor with `uploaded_file.getvalue()`/
   `.type`, returns `(fields, "")` for the raw-text slot. Fix the
   raw-text warning at `app.py:169` to only fire when
   `get_ocr_backend() == "tesseract"`, so a successful Claude-vision
   extraction never shows the (false) "Tesseract returned no text"
   message. TDD: extend `tests/test_streamlit_app.py` (existing
   `AppTest`-based file) with a Claude-backend case per module, plus a
   case proving the raw-text warning is suppressed under Claude.
6. **New External test tier (first for this platform)**: new
   `tests/test_claude_vision_external.py`, `@pytest.mark.skipif(not
   os.getenv("ANTHROPIC_API_KEY"), reason="requires a real
   ANTHROPIC_API_KEY")`, running one real extractor call per doc type
   against an existing pass-pool image (reuse
   `scripts/vehicle_discovery.py`'s registered vehicles, item #13's
   existing infra — no new fixtures needed) and asserting the result
   against golden fields, same tolerance-for-`known_ocr_limitations`
   pattern the existing pass-pool regression tests already use.
7. **Docs**: correct `tests/TESTING.md:28-31`'s now-stale "no External
   suite exists / N/A" claim; document the new flag, the refactored
   `extract_via_claude` signature, and the new extractor functions in
   `tests/TESTING.md`'s Coverage/test-list section. Collapse
   `NEXT_STEPS.md` item #16 to a terse ✅ line pointing at
   `ARCHIVE_WEB_STREAMLIT.md`, with the real before/after moved there in
   full (per `Claude.md`'s "Core file discipline").

## Definition of Done

- `HDTTOOLS_OCR_BACKEND=claude` makes both `main.py`'s three endpoints
  and `app.py`'s three module steps genuinely call Claude vision
  end-to-end, with the default (`tesseract`, or the var unset) producing
  byte-for-byte the same behavior as today.
- `vision_client.extract_via_claude` takes bytes, not a path; all three
  existing interactive callers still work (verified via
  `tests/test_readers_integration.py`, updated as needed).
- New Function-tier tests for `get_ocr_backend()` and the three new
  extractor functions; new/extended Module-tier tests for `main.py` and
  `app.py`'s claude-branch dispatch; a new, real, skip-if-no-key
  External-tier test — all passing for real.
- `tests/test_ocr_output_key_contracts.py` covers the new extractor
  functions' key sets, not just `_parse_fields`'s.
- The `app.py:169` raw-text warning never fires under the Claude
  backend.
- `tests/TESTING.md` and `NEXT_STEPS.md` reflect what was actually built
  and measured, not the pre-2026-09-09 "not started" state.

## Verification

- Run the full existing suite (`uv run pytest -q`) after each step —
  must stay green throughout, matching this project's TDD discipline
  (watch each new test fail for real before implementing, then pass).
- Manually run both apps with `HDTTOOLS_OCR_BACKEND=claude` set and a
  real `ANTHROPIC_API_KEY` against one real pass-pool photo per doc
  type, confirming the review form fills in correctly and the "Raw OCR
  text" expander/warning behave sensibly (no false "Tesseract returned
  no text" message).
- Run the new External-tier test for real (not just under mock) at least
  once before calling this done, per this project's standing preference
  for real network verification over trusting mocks alone.
