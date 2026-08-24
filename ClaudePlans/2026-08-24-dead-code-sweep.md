# Dead-code sweep: tool selection per platform + the allowlist problem

## Context

Raised while discussing what's next after the dashboard work (roadmap
item #7): the user wants a dead-code check across every product line,
noting at least one already-known candidate. Discussed counter-arguments
first — different tools are needed per platform (no single sweep), and
the real risk is false positives from framework-wired code (Compose
composables, pytest fixtures, FastAPI route handlers) and this repo's
deliberate public library API (`hdttools`'s `read_scale_ticket`/
`read_truck_tag`/`read_trailer_tag`, exported specifically for external
callers per `README.md`'s "Underlying toolkit" section) — a naive tool
flags all of that as "unused." Agreed approach: scope tool selection +
an explicit allowlist/ignore mechanism per platform, resolve the one
named candidate first as a fast, low-risk win, then decide separately
whether to expand.

**The known candidate, investigated during this planning session**:
`src/hdttools/parse_label.py` (flagged in `NEXT_STEPS.md` item #8 as
0%-covered, "worth confirming that and removing it rather than writing
tests for it, not yet checked"). Confirmed: it's a stray prototype file
(module-level `print(json.dumps(...))` runs on import, comment "Retry
execution of fixed script" — leftover scratch work, not a real module),
**already excluded from git** via `.gitignore` line 27
("Local scratch notes/fragments, not part of the application") — so it
was never actually shipped. A repo-wide grep confirms zero references to
`parse_label`/`parse_volvo_label` anywhere in real code. This isn't a
"find it" problem, it's a "close it out" problem — the file just needs
deleting locally and the two stale references (the `.gitignore` line and
`NEXT_STEPS.md`'s bullet) cleaned up.

## Goal

Close the known candidate for real. Stand up one real, low-false-positive
dead-code tool per platform (Python, Web, `scan-proxy`, Android), each
with an explicit allowlist/ignore mechanism covering this repo's known
framework-wired and intentionally-public code, verified against real
output (not speculative). Explicitly *not* a commit to deleting
everything each tool flags — every real finding gets a human review pass
before anything is removed. Whether to expand beyond this baseline
(especially Android's public-symbol reachability, deliberately scoped out
below) is a separate decision for afterward, not part of this plan.

## Steps

1. **Close `parse_label.py`**: delete the local file (confirmed
   unreferenced, confirmed already git-excluded — nothing to `git rm`).
   Remove the now-pointless `.gitignore` line 27. Update `NEXT_STEPS.md`
   item #8's bullet (currently lists `parse_label.py` as a coverage gap)
   to instead note it was confirmed dead and removed, not "not yet
   checked."

2. **Python: `vulture`**. Add as a dev dependency (`uv add --dev
   vulture`, matching this project's package-manager convention). Run it
   for real against `src/hdttools/` and `streamlit_app/` first (not
   `tests/` — test files legitimately have functions vulture can't prove
   are called, e.g. fixtures). Build `vulture_whitelist.py` (vulture's
   own supported mechanism, generated via `vulture --make-whitelist`
   then hand-pruned) from *real* flagged output, not written
   speculatively — expected real entries once output is seen: the
   `__init__.py` public API surface (`read_scale_ticket`/`read_truck_tag`/
   `read_trailer_tag`/`save_*`), dataclass fields in `models.py` (a
   known common vulture false-positive class), and FastAPI route
   handlers in `api/main.py` (referenced only via `@app.post(...)`
   decorators). Document the command + whitelist rationale in
   `tests/TESTING.md`.

3. **Web + `scan-proxy` (TypeScript): `knip`**. Chosen over `ts-prune`
   (narrower scope, less actively maintained) — knip checks unused
   exports, unused files, *and* unused dependencies in one pass, and has
   built-in `entry`/`ignore` config rather than needing a hand-rolled
   allowlist file. Run via `npx knip` first (no permanent dependency)
   against each project separately to see real output before deciding
   whether to add it as a devDependency. Expected real `entry`/`ignore`
   config once output is seen: Web's `main.tsx` and test setup files as
   entry points; `scan-proxy`'s `index.ts` (the Worker's `fetch` handler
   — invoked by the Cloudflare runtime, not by any in-repo caller) as an
   entry point. Cross-check against `web/TESTING.md`'s existing
   "Deliberately not tested" list (`ProcessingStep.tsx`, `StepPills.tsx`,
   `PredictiveEstimateNotice.tsx`, design-system primitives) — those are
   a *test-coverage* gap, not a dead-code one (they're genuinely
   imported/rendered), so knip shouldn't flag them; if it does, that's
   itself worth investigating, not silently allowlisting.

4. **Android: `detekt`, scoped to private-visibility rules only**.
   Chosen over firing up Android Studio's headless inspection CLI
   (`inspect.bat`, confirmed present at `G:\Android\AndroidStudio\bin\`)
   for this baseline pass — detekt is a lightweight Gradle plugin with
   fast, low-false-positive rules (`UnusedPrivateMember`,
   `UnusedPrivateClass`, `UnusedImports`), whereas whole-program
   *public*-symbol reachability for an app module runs straight into the
   framework-wiring false-positive risk (Compose composables, manifest-
   referenced classes, navigation routes referenced by string) without a
   much heavier setup (an inspection profile, real risk of false
   positives on `@Composable`/`@Preview` functions). Add the detekt
   Gradle plugin + a `detekt.yml` enabling just those three rules; run
   `./gradlew detekt`; review real output.

5. **Review and remove**: for every real finding across all three tools,
   confirm it via a manual grep/read (same standard used to close
   `parse_label.py` above) before deleting anything — no tool output gets
   deleted on its own say-so. Re-run each platform's full test suite
   after any deletion to confirm zero regressions (matching this
   session's established verification pattern).

6. **Document and close out**: add each tool's command to its platform's
   `TESTING.md` (a short new section per file, mirroring how "Coverage"
   sections were added this session). Update `NEXT_STEPS.md`: close the
   dead-code item with a compact summary once verified; explicitly note
   Android's public-symbol reachability (the `inspect.bat` route) as a
   deliberately-deferred expansion decision, not forgotten scope.

## Files

- `src/hdttools/parse_label.py` (deleted), `.gitignore` (remove the
  now-pointless line), `NEXT_STEPS.md` (item #8 bullet + close-out)
- `pyproject.toml` (`vulture` dev dependency), `vulture_whitelist.py`
  (new), `tests/TESTING.md` (new section)
- `web/package.json`, `web/knip.json` (if adopted), `web/TESTING.md`
- `workers/scan-proxy/package.json`, `workers/scan-proxy/knip.json` (if
  adopted), `workers/scan-proxy/TESTING.md`
- `android/build.gradle.kts` / `android/app/build.gradle.kts` (detekt
  plugin), `android/detekt.yml` (new), `android/TESTING.md`
- Any files confirmed dead and actually removed (unknown count until
  real tool output is reviewed — not enumerated here)

## Definition of Done

- `parse_label.py` is gone from disk; `.gitignore` and `NEXT_STEPS.md`
  no longer reference it.
- All three tools (`vulture`, `knip` ×2, `detekt`) run successfully and
  produce real output with a documented, real-output-derived allowlist/
  ignore config — not a speculative one.
- Every actual deletion (beyond `parse_label.py`) was individually
  confirmed unreferenced before removal, and the full test suite for
  that platform passes afterward with zero regressions.
- Each platform's `TESTING.md` documents its new tool's command.
- `NEXT_STEPS.md` reflects the closed baseline sweep and explicitly
  parks the Android public-symbol-reachability expansion as a separate,
  not-yet-decided next step.

## Verification

1. `git status`/`grep -r parse_label` — confirm the file and every
   reference to it are gone.
2. Run `uv run vulture src/hdttools streamlit_app`, `npx knip` (Web and
   `scan-proxy` separately), `./gradlew detekt` (Android) — confirm each
   runs clean (no unreviewed findings left outstanding) against the
   final state.
3. Full regression sweep on every platform touched by an actual deletion
   (`uv run pytest -q`, `npm test` in `web/`/`scan-proxy`, `./gradlew
   test connectedDebugAndroidTest`) — zero regressions.
4. Spot-check at least one real allowlisted/ignored entry per tool by
   hand (e.g. confirm `read_truck_tag` really is vulture-flagged without
   the whitelist, and really is genuinely used externally per
   `README.md`) to prove the allowlist reflects real tool behavior, not
   a guess.
