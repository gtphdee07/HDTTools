# Drop Tesseract for the Web API only (item #22, narrowed scope)

## Context

`NEXT_STEPS.md` item #22 tracks making Claude-vision the sole OCR
backend, replacing today's `HDTTOOLS_OCR_BACKEND` env-flag toggle
(default `"tesseract"`, opt-in `"claude"`) that `src/hdttools/ocr_common.py`
reads. It was decided (item #20) after item #11's 2026-08-24 finding:
Tesseract returns `None` for every field on realistic, un-cropped phone
photos — `preprocess_image()` never crops, so `--psm 6` can't isolate a
tag's text from surrounding clutter — while Claude vision reads the
same photos correctly with no preprocessing. This was freshly
reproduced live 2026-09-21: a real truck-tag scan through the actual Web
wizard came back completely blank, traced to exactly this failure mode
(`ExampleDocs/scans/truck/f150_blue_goose_uncropped/20260824_141527.jpg`
→ all-null via Tesseract, fully correct via Claude vision).

Item #22 was originally scoped as "Python/Streamlit/Web" together and
noted as blocked on item #20's shared scan-gating decision — dropping
the free Tesseract fallback turns every scan into a real, unbounded-cost
paid Anthropic API call, and **Streamlit is live and public today with
zero cost gating anywhere in Python/Streamlit/Web**. The user first
narrowed scope to "Web only, for now," then confirmed (same day) this
is **permanent, not deferred**: Streamlit was always meant to be a free,
public-service calculator demo, not a lower tier of the Android/Web paid
product — it will never need accounts, credits, or Claude-vision
scanning, so there is nothing for it to eventually migrate to. Web's
FastAPI backend (`src/hdttools/api/main.py`) isn't deployed anywhere
public yet (local dev only), so removing its Tesseract fallback carries
no live cost-exposure risk. Streamlit stays exactly as-is forever —
defaulting to Tesseract, toggleable to Claude via the env var only for
manual dev-time comparison, not as a migration path.

## Goal

Make Claude vision the Web API's only OCR backend: remove
`main.py`'s Tesseract dispatch branch and its dependency on
`get_ocr_backend()` entirely, so every Web scan (truck tag, trailer tag,
scale ticket) always goes through Claude, regardless of
`HDTTOOLS_OCR_BACKEND`. Streamlit, `ocr_common.py`, and every Tesseract
parsing module are untouched.

## Scope boundary

**In scope**: `src/hdttools/api/main.py`; `tests/test_api.py`;
`tests/test_scale_ticket_real_photo.py`; `tests/TESTING.md`'s
`test_api.py` row; `NEXT_STEPS.md` item #22 and its two
"superseded"/"update" cross-references; `ARCHIVE_WEB_STREAMLIT.md`.

**Explicitly out of scope, permanently**: `streamlit_app/app.py`,
`src/hdttools/ocr_common.py`, `truck_tag_ocr.py`/`trailer_tag_ocr.py`/
`scale_ticket_ocr.py` — all byte-for-byte unchanged; Streamlit keeps
defaulting to Tesseract forever, not until some future migration. The
"Fresh-machine setup checklist"'s `tesseract` install step stays
permanently (Streamlit always needs it). Free-tier/credit messaging —
Web has no real accounts/tiers yet (tied to item #20), so there's no
existing "free Tesseract scan" copy to change; Streamlit's free-forever
framing needs no messaging change either, since it was never going to
say otherwise. Cost-gating for Claude-vision calls on Web — deferred;
judged acceptable only because Web isn't publicly deployed. **Must be
revisited before any public Web deployment** — flag this explicitly in
`NEXT_STEPS.md` so it isn't silently forgotten once Web beta work
resumes. (Streamlit never needs this — it stays on the free, ungated
Tesseract path, which is exactly why this permanent-scope decision
carries no cost-gating implication for it at all.)

One real side effect: `ANTHROPIC_API_KEY` becomes a hard runtime
requirement for Web's three extract endpoints (today it's optional,
since Tesseract is the default). Streamlit is unaffected — its own
default stays Tesseract, no new key requirement introduced there.

## Steps

1. **`src/hdttools/api/main.py`**: remove `_ocr_upload`,
   `_TESSERACT_PARSERS`, the `get_ocr_backend`/`ensure_tesseract_configured`/
   `ocr_text`/`preprocess_image` imports, and the now-unused `from PIL
   import Image` / `import io`. Rewrite `_extract_fields` to
   unconditionally dispatch through `_CLAUDE_EXTRACTORS` (drop the
   `if get_ocr_backend() == "tesseract":` branch and its docstring's
   backend-selection framing).
2. Give a missing/invalid `ANTHROPIC_API_KEY` a clear, distinguishable
   error instead of letting it fall through to the generic 502 "Claude
   vision extraction failed." — e.g. a narrow `except` for the SDK's own
   auth error (or a startup-time presence check) that raises a distinct
   message naming the missing env var, so a misconfigured dev machine
   doesn't read as "Claude is down."
3. **`tests/test_api.py`**: remove the three Tesseract-branch tests
   (`test_extract_{truck_tag,trailer_tag,scale_ticket}_returns_parsed_fields`)
   and the `client` fixture's now-dead Tesseract monkeypatches; remove
   `test_extract_claude_backend_invalid_env_value_raises` (no more
   env-var-driven dispatch at this layer to validate — Streamlit's own
   `test_ocr_common.py`/`test_streamlit_app.py` coverage of that flag is
   untouched and still valid there). Drop the now-redundant
   `monkeypatch.setenv("HDTTOOLS_OCR_BACKEND", "claude")` line from each
   remaining `test_extract_*_claude_backend_*` test (Claude is Web's only
   path now) and rename them to drop "claude_backend" framing since
   there's no longer a second backend to contrast against. Collapse the
   duplicate non-image-upload tests to one. Add a test for step 2's
   fail-fast missing-key behavior.
4. **`tests/test_scale_ticket_real_photo.py`**: remove
   `test_real_photo_upload_through_the_actual_api_endpoint` — it
   specifically proves the endpoint's real Tesseract path, which no
   longer exists in `main.py`. Keep
   `test_real_ocr_on_the_tow_vehicle_only_photo_extracts_the_weights_correctly`
   unchanged (tests the raw Tesseract pipeline directly via
   `ocr_common`/`scale_ticket_ocr`, still valid, still what Streamlit
   uses). Update the file's module docstring to explain the removal.
5. **`tests/TESTING.md`**: update the `test_api.py` row to describe the
   simpler, single-path dispatch (no more env-var toggle at this layer);
   note where the removed real-endpoint-Tesseract coverage still
   effectively lives (`test_scale_ticket_real_photo.py`'s remaining test
   plus `test_streamlit_app.py`).
6. ✅ **Done ahead of the code change, 2026-09-21.** `NEXT_STEPS.md`:
   item #22's scope rewritten to Web-only, with Streamlit's Tesseract
   retention stated as permanent and decided (not blocked on item #20).
   The "✅ Superseded 2026-09-21" / "✅ Update 2026-09-21" notes under
   "Tests still outstanding" and "Known limitations" rewritten to say
   explicitly: resolved for Web once item #22 ships, permanent and
   accepted for Streamlit. Item #20's own text corrected to stop implying
   Streamlit might eventually join the shared accounts/paywall system.
   The "revisit cost-gating before public Web deployment" flag is in
   place. (The code change itself — steps 1-5 above — is still not
   started; only the roadmap framing is done.)
7. ✅ **Done ahead of the code change, 2026-09-21.**
   `ARCHIVE_WEB_STREAMLIT.md`: full narrative entry recording the
   Streamlit-stays-on-Tesseract-forever decision and why, and what it
   corrects in the item #20/#22 framing. The Web-side implementation
   detail (exact files/tests changed, the new hard `ANTHROPIC_API_KEY`
   requirement) still belongs in a follow-up archive entry once steps
   1-5 actually ship.

## Definition of Done

- `src/hdttools/api/main.py` has zero remaining references to
  `get_ocr_backend`, `ensure_tesseract_configured`, `ocr_text`,
  `preprocess_image`, or the Tesseract parser modules.
- All three Web extract endpoints always call the matching Claude
  extractor — true with `HDTTOOLS_OCR_BACKEND` unset *and* set to any
  value (the env var no longer affects Web's behavior at all).
- A missing `ANTHROPIC_API_KEY` produces a clear, distinct error,
  covered by a dedicated test — not the generic 502.
- `streamlit_app/app.py` and every Tesseract parsing module are
  byte-for-byte unchanged; `test_streamlit_app.py` passes unmodified.
- Full `uv run pytest -q` passes with no new External-tier dependency
  introduced into the default run (no Minor/Major-tier test makes a real
  Claude API call).
- `NEXT_STEPS.md`/`ARCHIVE_WEB_STREAMLIT.md`/`tests/TESTING.md` reflect
  the actual narrower shipped scope — no stale "fully superseded" claim
  left standing about Streamlit.

## Verification

- Re-run the exact live reproduction case: POST the same real,
  uncropped photo (`ExampleDocs/scans/truck/f150_blue_goose_uncropped/
  20260824_141527.jpg`) to the running Web API with `HDTTOOLS_OCR_BACKEND`
  **unset** — confirm full, correct fields (proving Claude is now the
  true default, not opt-in).
- Re-run the same request with `HDTTOOLS_OCR_BACKEND=tesseract`
  explicitly set — confirm identical (still-correct) output, proving Web
  now genuinely ignores the flag.
- Launch Streamlit (`uv run streamlit run streamlit_app/app.py`) and
  confirm it's completely unaffected — still Tesseract-default, same
  behavior as before this change.
- `uv run pytest -q` — full suite green, count matches expectations
  (net test count down slightly: 4 removed, ~1 added).
- Temporarily unset `ANTHROPIC_API_KEY` and hit `/api/extract/truck-tag`
  — confirm the new clear error, not a silent/generic 502.
