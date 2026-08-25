# Interface-contract suite: document the combined manual command

## Context

Item #13's design (`FUTURE_CONSTRAINED_RANDOM_OCR_TESTING.md`) names the
interface-contract suite as the last piece that "runs both pools
together," triggered manually whenever Tesseract, Claude, or an
OCR-adjacent library version changes. Both pools now exist for real:
`tests/test_pass_pool_regression.py` and
`tests/test_fail_pool_regression.py` (both built earlier this session),
each resolving one random image per doc_type and asserting real
extraction still matches documented golden state.

The FUTURE doc's own scoping decision (2026-08-25, direct quote from the
project owner: *"I don't expect to develop the hooks to auto recognize a
dependency change and autorun the regression script. I just need a set
of script commands that I can manually run"*) already says what this
piece needs to be: **a documented command, not new automation or new
test code.** Confirmed with the project owner again just now — the
minimal documentation-only approach is the right scope here, not a new
exhaustive-sweep script (that would be more machinery than the scoping
decision called for, and wouldn't run as part of the default `pytest -q`
without new collection-exclusion config that doesn't exist yet).

## Goal

A single documented, copy-pasteable command (matching
`DEV_ENVIRONMENT.md`'s existing style) that runs both pools together —
the real "dependency changed, check the OCR extraction path" command —
with a note on why re-running it matters given each run only samples one
random image per pool/doc_type.

## Steps

1. **`DEV_ENVIRONMENT.md`**, under "Python / backend / Streamlit": add a
   short new subsection "OCR extraction interface-contract check" with:
   ```bash
   uv run pytest -q tests/test_pass_pool_regression.py tests/test_fail_pool_regression.py -v
   ```
   plus a one-line note: run whenever Tesseract/Claude/an OCR-adjacent
   library version changes; each run samples one random image per
   doc_type per pool, so re-run it a few times on a real dependency bump
   for broader coverage (the fail-pool's `truck_tag` vehicle alone has
   10 images to cycle through today).

2. **`NEXT_STEPS.md` item #13**: mark the interface-contract suite done,
   describing it as the documented command above (not new code),
   pointing at `DEV_ENVIRONMENT.md`.

3. **`FUTURE_CONSTRAINED_RANDOM_OCR_TESTING.md`**'s step-5 list: mark
   the interface-contract suite bullet done the same way, leaving
   manufacturer-diversity growth and the Android inherit-vs-duplicate
   decision as the only remaining open items under item #13.

## Definition of Done

- `DEV_ENVIRONMENT.md` has the new documented command, verified by
  actually running it once for real (not just written and assumed
  correct).
- `NEXT_STEPS.md` / `FUTURE_CONSTRAINED_RANDOM_OCR_TESTING.md` reflect
  that all three pieces of item #13's core design (pass-pool, fail-pool,
  interface-contract suite) are now done; only diversity-growth and the
  Android decision remain open.

## Verification

1. Run the exact documented command for real:
   `uv run pytest -q tests/test_pass_pool_regression.py tests/test_fail_pool_regression.py -v`
   — confirm both pools' tests pass together in one invocation.
