# Wrap up HDTTools docs, then write + publish the detekt/JDK25 report

## Context

This session's dead-code sweep (roadmap item #10) hit a real, substantive
finding while standing up Android's tool: `detekt` 1.23.8 (latest stable)
crashes on this machine's JDK 25, even after a working JDK 21 toolchain
was proven reachable via Gradle's foojay resolver — the plugin's own
`jdkHome` setting doesn't actually redirect the CLI process, a real gap
in detekt's Gradle plugin, not a config mistake. Follow-up discussion
covered real alternatives (downgrading Android Studio, pinning a Gradle
toolchain project-wide, adopting the alpha `dev.detekt` successor) with
their genuine risk/reward tradeoffs, and landed on wanting a scratch-repo
experiment (outside this repo) to find a working AGP × Kotlin × detekt ×
JDK-toolchain combination before applying anything here for real.

The user wants this captured properly before compacting: a standalone,
publishable report (`REPORT_KOTLIN_DETEKT_TOOLCHAIN.md` + an Artifact web
page) covering what was found, how, and the proposed solution — with the
actual scratch-repo experiment explicitly deferred to a future session
("you'll have to execute the test plan after the compression"). This is
a side effort to the main HDTTools project, so HDTTools' own doc chain
(`NEXT_STEPS.md`, `ARCHIVE_DEAD_CODE.md`) should only carry a short
pointer to the report, not duplicate the full narrative already written
there this session.

## Goal

1. HDTTools' own docs trimmed to short summaries pointing at the report
   (no duplicated detail).
2. A complete, self-contained `REPORT_KOTLIN_DETEKT_TOOLCHAIN.md` — a
   reader with zero conversation context should be able to understand
   the finding, the investigation, the proposed solution, and the
   concrete next-steps test plan from the file alone.
3. That report also published as an Artifact web page.
4. Everything committed/pushed, then ready to compact.

## Steps

1. **Trim `NEXT_STEPS.md` item #10's Android bullet** (currently ~11
   lines of real detail) down to 2-3 lines: still blocked/deferred,
   still real, but pointing at `REPORT_KOTLIN_DETEKT_TOOLCHAIN.md` for
   the full investigation instead of carrying it inline.

2. **Trim `ARCHIVE_DEAD_CODE.md`'s "🔶 Android: `detekt` deferred"
   section** (currently ~50 lines) the same way — collapse to a short
   pointer at the new report. The Python/`vulture` and Web+scan-proxy/
   `knip` sections stay exactly as they are (already appropriately
   scoped, not part of this side effort).

3. **Write `REPORT_KOTLIN_DETEKT_TOOLCHAIN.md`** (repo root, matching
   `FUTURE_API_SCHEMA_VALIDATION.md`'s precedent as a standalone,
   self-contained topic doc outside the main Archive chain). Sections:
   - **Summary** — one paragraph, the finding and proposed direction.
   - **Background** — what task surfaced this (item #10's Android
     `detekt` step) and why it matters (this class of failure — a
     bundled analysis tool's compiler not recognizing a new JDK major
     version — isn't detekt-specific, and this machine's ambient JDK
     already drifted once silently via an Android Studio update).
   - **The finding** — real error text, real stack trace excerpt
     (`KotlinEnvironmentUtilsKt.createKotlinCoreEnvironment`,
     `IllegalArgumentException: 25.0.2`), what it means.
   - **Investigation, in order** — the `jvmTarget` fix that got past the
     first error, the `jdkHome`-toolchain workaround that didn't
     actually redirect the CLI process (real JDK 21 downloaded via
     foojay, confirmed on disk, still crashed), the Maven Central checks
     confirming 1.23.8 is genuinely latest stable and `dev.detekt` has
     no stable release yet, and the `kotlin-compiler:2.4.10` dependency
     found in the `dev.detekt` alpha's module metadata (real evidence
     the successor's newer bundled compiler is why it plausibly fixes
     this).
   - **Options considered, with real tradeoffs** — downgrading Android
     Studio (rejected: doesn't fix the root ambient-JDK fragility, costs
     more, is a system-tool change), adopting `dev.detekt` alpha (real
     option, alpha-software risk), pinning a Gradle toolchain project-
     wide (recommended direction — full risk/reward as already
     discussed: reproducibility and immunity to future Studio-update
     drift, versus broader blast radius and an unverified AGP/Kotlin
     toolchain-interop question).
   - **Proposed solution** — pin a Gradle toolchain (JDK 21, or whatever
     the experiment confirms), verified first in an isolated scratch
     project before touching this repo.
   - **Proposed test plan (for a future session)** — a small, disposable
     Android module outside this repo (on `G:`, not `C:`, matching this
     machine's space-constraint convention; location confirmed with the
     user before creating it), minimal dependencies (no Compose/
     RevenueCat/etc.) so trials iterate fast, searching AGP × Kotlin ×
     detekt-version × JDK-toolchain combinations; once a working
     combination is found, apply it to this real repo as one deliberate
     change, verified via the same full-suite regression sweep this
     session used for every other change (Minor + Major + a real
     detekt run). Explicitly note this step is *not* done yet.

4. **Cross-link**: `NEXT_STEPS.md`/`ARCHIVE_DEAD_CODE.md` point to the
   report; the report's own header points back to `NEXT_STEPS.md` item
   #10 for current status, matching this repo's existing lookup
   convention (`ARCHIVE_DEAD_CODE.md`'s own opening does exactly this
   for `ARCHIVE_TESTING.md`).

5. **Publish as an Artifact** — load the `artifact-design` skill first
   (required before any Artifact publish), build the web version from
   the same real content (not a different, re-summarized version), and
   deliver the URL.

6. **Commit and push** (ask first, per this session's standing rule) —
   `NEXT_STEPS.md`, `ARCHIVE_DEAD_CODE.md`,
   `REPORT_KOTLIN_DETEKT_TOOLCHAIN.md`, this plan's own
   `ClaudePlans/2026-08-24-...md` save.

## Files

- `NEXT_STEPS.md` — item #10's Android bullet, trimmed
- `ARCHIVE_DEAD_CODE.md` — Android section, trimmed
- `REPORT_KOTLIN_DETEKT_TOOLCHAIN.md` (new, repo root)
- An Artifact (published web page, not a repo file)

## Definition of Done

- No duplicated technical detail between `NEXT_STEPS.md`/
  `ARCHIVE_DEAD_CODE.md` and the new report — the HDTTools docs carry
  only a pointer.
- The report is complete and self-contained on its own, including a
  concrete, actionable test plan for the deferred scratch-repo
  experiment.
- The report is published as an Artifact with a real URL delivered.
- Everything is committed and pushed.

## Verification

1. Read `NEXT_STEPS.md` item #10 and `ARCHIVE_DEAD_CODE.md`'s Android
   section back — confirm they're short and the cross-reference to the
   report resolves to a real file.
2. Read `REPORT_KOTLIN_DETEKT_TOOLCHAIN.md` back in full — confirm it
   reads coherently with zero assumed conversation context.
3. Confirm the Artifact publish call returns a real URL.
4. `git status` clean after the commit/push.
