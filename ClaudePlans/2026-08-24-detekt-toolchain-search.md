# Scratch-repo experiment: find a working detekt/JDK toolchain combination

## Context

`REPORT_KOTLIN_DETEKT_TOOLCHAIN.md` documents a real, reproducible
blocker from the dead-code sweep (roadmap item #10): `detekt` 1.23.8's
bundled Kotlin compiler crashes (`IllegalArgumentException: 25.0.2`)
because it doesn't recognize this machine's ambient JDK (25, from
Android Studio's bundled JBR at `G:\Android\AndroidStudio\jbr`, confirmed
still the active `JAVA_HOME`). A `jdkHome`-toolchain workaround pointed
at a real, Gradle-downloaded JDK 21 did **not** fix it — a genuine gap in
detekt's Gradle plugin, not a config mistake. The report's own "Proposed
test plan" section explicitly deferred running this experiment to a
future session, which is now.

Real evidence already gathered (via live Maven Central queries, not
memory) narrows the search: `detekt` 1.23.8 is genuinely the latest
stable release; the actively-developed successor lives under a new
`dev.detekt` Maven group with only alpha releases (`2.0.0-alpha.0`
through `.6`); `dev.detekt:detekt-parser:2.0.0-alpha.6`'s real module
metadata shows it bundles `kotlin-compiler:2.4.10` — a much newer
compiler than 1.23.8's, and a plausible reason it would recognize JDK 25
even without any toolchain pin.

## Goal

**This plan covers Phase 1 only: find a candidate.** Confirm —
empirically, in a disposable scratch project, not by assumption — at
least one AGP × Kotlin × detekt-version × JDK-toolchain combination that
lets `detekt` actually run and catch a real violation (an
intentionally-unused private member) on this machine. Stop there, report
the real result, and discuss next steps with the user before touching
the real repo.

Applying a confirmed combination to the real HDTTools Android project is
**Phase 2** — deliberately scoped out of this plan's execution. It's
sketched below (steps 4+) so the shape of the follow-on work is visible,
but it is *not* approved for execution here: this is a side
investigation, and the core HDTTools project only needs the final,
reviewed result, not every intermediate step preserved as ceremony.
Phase 2 gets its own review once Phase 1's real finding is in hand — the
right approach may look different depending on what Phase 1 actually
finds (e.g., a clean toolchain pin vs. an alpha-only fix changes the
conversation).

**Search strategy (user-selected): targeted, cheapest-first.** Try the
most likely fix first — pinning a Gradle-managed JDK 21 toolchain
project-wide with the existing `detekt` 1.23.8 — and stop there if it
works. Only fall back to the next candidate if a given trial genuinely
fails. This trades a full comparison matrix for speed; each trial costs
a real Gradle sync/download.

**Scratch location (user-selected):** `G:\ClaudeScratch\detekt-toolchain\`
— a generic, clearly-disposable root, separate from the real Android
SDK/Studio install under `G:\Android\`, so there's no ambiguity about
what's safe to delete afterward.

## Phase 1 — execute now: find a candidate combination

1. **Scaffold a minimal Android module** at
   `G:\ClaudeScratch\detekt-toolchain\`: bare `com.android.application`
   plugin, one trivial Kotlin source file containing an intentionally
   unused private member (so a later "detekt actually caught it" check
   is a real positive, not just "the plugin loaded without crashing").
   No Compose, no RevenueCat, no kotlinx-serialization — keep the
   dependency graph minimal so each trial's Gradle sync stays fast.
   Include the `foojay-resolver-convention` plugin in `settings.gradle.kts`
   (already proven working this session) so toolchain JDKs auto-provision
   without any manual JDK install.

2. **Trial 1 (cheapest-first): pin a Gradle JDK 21 toolchain +
   detekt 1.23.8.** Add `kotlin { jvmToolchain(21) }` (or the
   `java.toolchain` equivalent) to the scratch module, apply
   `io.gitlab.arturbosch.detekt` 1.23.8, and run `./gradlew detekt`.
   - **If it succeeds** (plugin loads, runs under the pinned JDK 21, and
     actually flags the intentionally-unused private member): search
     stops here per the targeted strategy — this is the confirmed
     combination.
   - **If it still crashes**: capture the real error, move to Trial 2.

3. **Trial 2 (only if Trial 1 fails): `dev.detekt` 2.0.0-alpha.6 under
   the ambient JDK 25** (no toolchain pin) — testing whether the newer
   bundled `kotlin-compiler:2.4.10` alone resolves the JDK-recognition
   problem, independent of pinning anything.
   - If this succeeds, that's the confirmed combination (alpha-software
     tradeoff noted, per the report's own risk discussion).
   - If it also fails, capture the error and treat the search as
     inconclusive — stop and report back rather than open-ending into a
     full matrix sweep (that's the explicit tradeoff of "targeted"
     over "exhaustive").

**Stop here.** Report the real trial result(s) — which combination
worked, or that both trials failed — and discuss Phase 2 with the user
before doing anything further. Do not proceed into Phase 2 automatically.

## Phase 2 — sketch only, not approved for execution in this plan

Kept here so the shape of the follow-on work is visible, and so nothing
from the report's original test plan is silently dropped. This phase
needs its own review once Phase 1's real finding is in hand — the right
approach depends on what Phase 1 actually finds (a clean toolchain pin
is a different conversation than an alpha-only fix), and the core
HDTTools project only needs the final, reviewed result preserved, not
every intermediate step.

4. **Apply the confirmed combination to the real HDTTools Android
   project** (`android/`) as one deliberate change — mirroring how
   `vulture`/`knip` were added this session: real config, run against
   real code, review real findings before removing/fixing anything.
   - If Trial 1 won: add `jvmToolchain(21)` project-wide in
     `android/build.gradle.kts` (or wherever Kotlin's toolchain DSL
     applies cleanly — verify against AGP 9.3.1 + Kotlin 2.2.10's actual
     behavior, since the report flagged this interop as a real,
     unverified question), plus the `detekt` 1.23.8 plugin/config,
     scoped to the private-visibility rules originally intended for item
     #10.
   - If Trial 2 won: add the `dev.detekt` alpha plugin/config instead, no
     toolchain pin needed.

5. **Full-suite regression sweep**, not just a detekt-only check —
   required because a project-wide toolchain pin changes which JVM runs
   *every* Gradle task:
   - `./gradlew test` (Minor)
   - `./gradlew connectedDebugAndroidTest` (Major, needs the emulator —
     see `DEV_ENVIRONMENT.md` for the AVD start command)
   - `./gradlew detekt` (confirm it still runs clean/flags real issues)
   - Confirm the dashboard's Android row (`dashboard.svg`,
     `scripts/generate_dashboard.py`) still regenerates correctly.

6. **Update `REPORT_KOTLIN_DETEKT_TOOLCHAIN.md`** with a dated
   "✅ Resolved" section appended (per this project's pruning
   convention — append, don't rewrite the original investigation):
   what combination worked, real trial output, and a link to the
   `android/` commit that applied it. If the search is inconclusive
   instead (both trials fail), append a "🔶 Update" section instead,
   documenting what was tried and that Android's `detekt` step stays
   deferred.

7. **Update `NEXT_STEPS.md` item #10's Android bullet** and
   `ARCHIVE_DEAD_CODE.md`'s Android section to reflect the real outcome
   (closed ✅, or still deferred with the new evidence noted) — same
   trim-to-pointer convention already established for this topic.

8. **Clean up the scratch project** at
   `G:\ClaudeScratch\detekt-toolchain\` once the real repo change is
   verified — it's disposable by design, not meant to persist.

9. **Commit and push** (confirm first, per this session's standing
   rule) — `android/` config changes, `REPORT_KOTLIN_DETEKT_TOOLCHAIN.md`,
   `NEXT_STEPS.md`, `ARCHIVE_DEAD_CODE.md`, this plan's own
   `ClaudePlans/2026-08-24-detekt-toolchain-search.md` save.

## Files

**Phase 1 (this plan):**
- `G:\ClaudeScratch\detekt-toolchain\` — new, disposable, outside the
  repo. Left in place after Phase 1 (not cleaned up until Phase 2 is
  reviewed and executed, in case it's needed for a follow-up trial).

**Phase 2 (sketch only, not executed by this plan):**
- `android/build.gradle.kts` / `android/app/build.gradle.kts` /
  `android/gradle/libs.versions.toml` — the confirmed toolchain +
  detekt config, applied for real
- `REPORT_KOTLIN_DETEKT_TOOLCHAIN.md` — appended "Resolved" (or
  "Update") section
- `NEXT_STEPS.md`, `ARCHIVE_DEAD_CODE.md` — item #10's Android status
  updated to match the real outcome

## Definition of Done

**For this plan (Phase 1 only):**
- At least one real trial ran to completion in the scratch project with
  a genuine pass/fail result (not assumed from the report's evidence
  alone) — either a confirmed working combination, or both targeted
  trials genuinely exhausted and reported as inconclusive.
- The real result reported back to the user, with Phase 2 (applying it
  to `android/`) explicitly left for a separate, later decision — not
  started automatically.

Phase 2's own Definition of Done (regression sweep passing, docs
updated, scratch cleaned up, committed/pushed) applies once Phase 2 is
itself reviewed and approved — not part of this plan's completion
criteria.

## Verification

1. Real terminal output from each Gradle trial (`./gradlew detekt` in
   the scratch project) — pass/fail state confirmed by reading the
   actual output, not inferred.
2. The trial(s) run against the intentionally-unused-private-member
   source file, confirming a real positive (detekt actually flags it)
   rather than just "the plugin loaded without crashing."
