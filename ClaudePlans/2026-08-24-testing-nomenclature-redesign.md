# Testing nomenclature redesign: event-based Minor/Major/External + a cross-platform coverage gate

## Context

Roadmap item #9 (`NEXT_STEPS.md`). Planning item #7's README status
dashboard surfaced that the dashboard's own "minor/major/integration"
framing didn't match this repo's real, established vocabulary: the root
`TESTING.md`'s Minor/Major is a diff-driven *regression-scoping* rule,
completely orthogonal to each platform's own time-cadence-named
Sanity/Daily/Weekly/Release (`scan-proxy`) and Unit/Daily/Weekly
(Android) *network-dependency tiers* — two independent axes, not one
scheme replacing the other, confirmed by a full re-read of
`ARCHIVE_TESTING.md`. The dashboard work was paused specifically to
settle this first, since it would otherwise report against a scheme
about to change.

Decided during that discussion (recorded in `NEXT_STEPS.md` item #9 and
`ARCHIVE_TESTING.md`, 2026-08-24): collapse these two axes into one,
purely event-based scheme — Minor/Major absorbs the offline tiers, a new
5th test category **External** absorbs the real-network tiers, applied
*consistently* across all four platforms (Android, `scan-proxy`, Web,
Python/Streamlit) even though Web and Python never had tier language at
all before. Plus a coverage-gate script run at release time.

This plan formalizes that discussion into concrete file changes, and
resolves the design questions that were still open when work paused, per
this round's clarifying answers:
- **Docs only this pass** — no test file/directory/npm-script renames
  (e.g. `src/weekly/` stays `src/weekly/` for now); only the TESTING.md
  narrative and category names change. Physical renames are a fast,
  low-risk mechanical follow-up once this model is live and stable.
- **Confirmed tier mapping**: Sanity's `[sanity]`-tagged/offline-mocked
  cases and Android's Unit tier → **Minor**. Full `npm test`/
  `connectedDebugAndroidTest` → **Major**. Weekly + Release (scan-proxy)
  and Weekly (Android) → **External**'s two suites (through-our-service
  vs. direct-provider-boundary), both under External's *event-driven*
  trigger. External's *diff-driven* trigger isn't a separate suite to
  run — it's satisfied by running External whenever a Major change
  touches boundary-calling code.
- **Full four-platform coverage scope**: `web/` and `workers/scan-proxy`
  get real coverage tooling wired up in this same pass (they have none
  today), so the gate script is genuinely uniform on day one rather than
  stubbed for two platforms.
- **No-release-event platforms (Web, Streamlit today) run report-only**
  — the gate script prints their real coverage number and always exits
  success for them; only Android and Python (which already have a real
  baseline and, for Python, the existing xfail/strict-failure discipline
  to match) get an enforced pass/fail threshold.

## Goal

One consistent, event-driven testing vocabulary — Function/Interaction/
Module/Interface/**External**, scoped per-change by Minor/Major — used
identically in every platform's `TESTING.md`, with the old time-cadence
names (Sanity/Daily/Weekly/Release, Unit/Daily/Weekly) fully retired, and
a real, working coverage-gate script that reports (and, where a real
baseline exists, enforces) coverage for all four platforms.

## Steps

1. **Root `TESTING.md`** — the framework definition all platform files
   point back to:
   - Add a `### 5. External tests` section (peer to Function/Interaction/
     Module/Interface) defining the category and its two triggers: (a)
     diff-driven — a Major change touching code that calls a real 3rd-
     party boundary also runs External; (b) event-driven — release-
     gated, a 3rd-party SDK/API version bump, or explicit suspicion of
     drift, independent of any diff.
   - Replace the "Reconciling with per-platform network/cadence tiers"
     section (currently describes two *separate, coexisting* axes) with
     the new single-axis model: Minor (offline function+interaction),
     Major (offline full module+interface suite, cascades to other
     modules sharing a changed interface), External (real-network, two
     triggers as above). State explicitly that Sanity/Daily/Weekly/
     Release and Unit/Daily/Weekly are retired, not kept in parallel.
   - Update the "Regression scoping: Minor vs. Major" section's Major
     bullet to mention the External cascade.
   - Add a new `## Coverage gate` section: what the gate script does,
     where it lives, its per-platform enforced-vs-report-only behavior,
     and the baseline-floor threshold policy (below).
   - Update "Status of this repo against the framework" to reflect the
     redesign date/state.

2. **`android/TESTING.md`** — replace the Unit/Daily/Weekly tier table
   and its surrounding prose with Minor (`./gradlew test`)/Major
   (`./gradlew connectedDebugAndroidTest`)/External
   (`.\test-weekly.ps1`, unrenamed this pass) framing; keep all real
   narrative (the `CustomTestRunner` marker-file mechanism, the
   RevenueCat balance-cache bug, etc.) intact, just relabeled. Update the
   Coverage section to note these numbers now feed the gate script.

3. **`workers/scan-proxy/TESTING.md`** — replace the Sanity/Daily/
   Weekly/Release table with Minor (`npm run test:sanity`)/Major (`npm
   test`)/External (`npm run test:weekly` + `.\test-release.ps1`, both
   unrenamed this pass, described as External's two suites — through-
   our-service vs. direct-provider-boundary) framing. Keep all real
   narrative intact.

4. **`tests/TESTING.md`** (Python/Streamlit) and **`web/TESTING.md`** —
   neither ever had tier language; add a short new section applying the
   same Minor/Major framing for consistency (today's whole suite is
   Minor+Major undifferentiated, since nothing tags a fast subset yet —
   document that honestly rather than inventing a split that doesn't
   exist). Note plainly that neither platform has an External suite yet
   (no real 3rd-party boundary called directly by either), so that
   category is N/A there today, not a gap.

5. **Web coverage tooling** (new): add `@vitest/coverage-v8` as a dev
   dependency, add a `test:coverage` script (`vitest run --coverage`),
   run it for a real baseline number, document in `web/TESTING.md`'s new
   Coverage section (mirroring `tests/TESTING.md`'s existing Coverage
   section's format).

6. **`scan-proxy` coverage tooling** (new): wire up coverage for the
   `node --test`-based suite — Node's built-in
   `--experimental-test-coverage` flag on the existing `test`/
   `test:sanity` scripts is the first thing to try (no new dependency);
   fall back to `c8` only if that proves inadequate in practice. Run for
   a real baseline number, document in `workers/scan-proxy/TESTING.md`'s
   new Coverage section.

7. **Coverage-gate script** — new `scripts/coverage_gate.py` (a Python
   orchestrator, consistent with this project's `uv run` convention,
   even though it shells out across all four platforms). For each
   platform: run (or read already-generated) coverage output and parse
   its real overall percentage out of that platform's own report format
   — JaCoCo's XML report for Android, `coverage.py`'s `coverage json`
   output for Python, Vitest's `coverage-summary.json` (v8 provider) for
   Web, Node's own `--experimental-test-coverage` summary output for
   scan-proxy. Threshold policy: **baseline-floor, not an arbitrary
   target** — Android and Python are enforced against *today's real
   baseline number* (already documented in `NEXT_STEPS.md` item #8: 71%
   Android Daily-tier, 79% Python total), failing only on regression
   below that floor, consistent with item #8's own "no target percentage
   decided yet" stance. Web and scan-proxy (no release event yet) print
   their real number and always exit 0 for that platform. Overall script
   exit code reflects only the platforms actually gated.

8. **Close out item #9**: once the above is real and verified, flip
   `NEXT_STEPS.md` item #9 to ✅ with a compact summary (per `Claude.md`'s
   Core file discipline), move the full narrative into
   `ARCHIVE_TESTING.md`. Update item #7's now-stale dashboard-blocked-on-
   #9 bullet and item #8's coverage-tooling-gap bullet, since both
   preconditions this closes.

## Files

- `TESTING.md` (root) — framework rewrite (External category, retired
  reconciling section, new Coverage gate section).
- `android/TESTING.md`, `workers/scan-proxy/TESTING.md`,
  `tests/TESTING.md`, `web/TESTING.md` — each relabeled to the new model,
  narrative content otherwise preserved.
- `web/package.json`, `web/vite.config.ts` (or a new `vitest.config.ts`
  section) — `@vitest/coverage-v8` + `test:coverage` script.
- `workers/scan-proxy/package.json` — new coverage script.
- `scripts/coverage_gate.py` (new) — the orchestrator.
- `NEXT_STEPS.md`, `ARCHIVE_TESTING.md` — close-out updates once verified.

No production application code changes anywhere in this plan — testing
infrastructure and documentation only.

## Definition of Done

- `Sanity`/`Daily`/`Weekly`/`Release` and `Unit`/`Daily`/`Weekly` tier
  language is gone from every `TESTING.md` (root, android, scan-proxy,
  web, tests) — a repo-wide search confirms it only remains inside
  `ARCHIVE_*.md` narrative history, never in current-state docs.
  `git mv`/renames of test files themselves are explicitly out of scope.
- Root `TESTING.md` defines External as a 5th category with both
  triggers spelled out, and a Coverage gate section describing the real
  script.
- `web/` and `workers/scan-proxy` both produce real, non-zero coverage
  numbers via a documented command.
- `scripts/coverage_gate.py` runs successfully end-to-end and produces
  correct enforced/report-only output for all four platforms.
- `NEXT_STEPS.md` item #9 is ✅ with a compact summary; full narrative
  lives in `ARCHIVE_TESTING.md`; items #7/#8 updated to reflect this
  closing their respective blocked-on/gap bullets.

## Verification

1. Repo-wide search for `Sanity`, `Daily`, `Weekly`, `Release` (case-
   sensitive, as tier names) across every `TESTING.md` — confirm zero
   remaining hits outside `ARCHIVE_*.md`.
2. Run each platform's existing test commands unchanged and confirm the
   same pass counts as before this work (no test code moves, so no
   regression is possible, but confirm anyway): `./gradlew test`,
   `./gradlew connectedDebugAndroidTest`, `npm test` (scan-proxy), `npm
   test` (web), `uv run pytest -q`.
3. Run the two new coverage commands (`web/`, `scan-proxy`) and confirm
   real, non-zero, sane-looking percentages.
4. Run `uv run scripts/coverage_gate.py` directly: confirm Android/
   Python report enforced pass/fail against their real documented
   baseline, and Web/scan-proxy report their number with an explicit
   "not gated — no release event yet" note, exiting 0 regardless of
   their number.
5. Read all five updated `TESTING.md` files back end-to-end, confirming
   internal consistency (no file still cross-references another file's
   now-retired tier names).
