# Phase 2: apply the confirmed detekt/JDK21 fix to the real Android project

## Context

Phase 1 (executed this session, in a disposable scratch project at
`G:\ClaudeScratch\detekt-toolchain\`) confirmed a real fix for the
`detekt`/JDK25 crash documented in `REPORT_KOTLIN_DETEKT_TOOLCHAIN.md`,
via three actual `./gradlew detekt` runs — not by assumption:

- The report's original hypothesis (pin the project's Kotlin toolchain
  via `kotlin { jvmToolchain(21) }`) is **confirmed not to work** — this
  session tested it directly in the scratch project by removing it and
  re-running; identical pass/fail either way. This matches the report's
  earlier finding that the `jdkHome` property on the Detekt task also
  didn't help — both are project/task-level settings, and neither
  redirects what actually crashes.
- **The real fix**: detekt's analysis runs *in-process inside the
  Gradle daemon's own JVM* — not a separately forked process. Only
  pinning that JVM works: `org.gradle.java.home=<path>` in
  `gradle.properties`, pointed at a real JDK 21
  (`G:\GradleUserHome\jdks\eclipse_adoptium-21-amd64-windows.2`, the
  same JDK 21 the report's earlier `jdkHome` attempt had already
  downloaded via the foojay resolver). With that one line set, no
  task-level `jvmTarget`/`jdkHome` override is needed at all — detekt
  correctly infers everything once it's actually running under JDK 21.
- Real positive control: detekt genuinely flagged an
  intentionally-unused private function (`[UnusedPrivateMember]`) in the
  scratch project, confirming the tool actually works, not just "didn't
  crash."

**The real open question Phase 1 surfaced**: `org.gradle.java.home`
takes a literal filesystem path — unlike `jvmToolchain()`, it does not
auto-provision via the foojay resolver. Committing a machine-specific
path (like the one above, unique to this Windows machine) into
HDTTools' shared `android/gradle.properties` would break on any other
machine or CI runner. This plan's first step resolves that before
touching the real repo.

**HDTTools has no CI configured** (`.github/` doesn't exist) — so this
is currently a single-dev-machine problem, not a CI problem. Worth
noting in the docs update for whenever CI does get added (a CI runner
would set its own explicit JDK version directly, sidestepping the
Android-Studio-JBR-drift problem entirely — a different, simpler
situation than a dev machine's ambient JDK).

## Goal

Apply the confirmed fix to the real HDTTools Android project as one
deliberate, fully-regressed change, using a placement for
`org.gradle.java.home` that doesn't hardcode a machine-specific path
into the shared repo. Close out roadmap item #10's Android leg for
real, and update `REPORT_KOTLIN_DETEKT_TOOLCHAIN.md` with the actual
resolution.

## Steps

1. **Prove the portability answer in the scratch project first**, before
   touching the real repo (same "prove it in isolation first" principle
   the original report's test plan called for). Remove
   `org.gradle.java.home` from the scratch project's own
   `gradle.properties`; instead set it in this machine's *global*
   `G:\GradleUserHome\gradle.properties` (confirmed empty of any
   `java.home` setting right now — a clean, unused, legitimate place for
   machine-specific Gradle config, and Gradle's own documented mechanism
   for exactly this). Re-run `./gradlew detekt` in the scratch project
   with **no** project-level `org.gradle.java.home` at all, confirming
   the global setting alone still produces the same real
   pass-then-flags-the-real-issue result as Phase 1.
   - This is the key check: it proves the real repo's own
     `gradle.properties` can stay portable (no hardcoded path committed),
     while each dev machine supplies its own JDK 21 path once, globally,
     outside of git entirely.

2. **Document the one-time per-machine setup step** in
   `DEV_ENVIRONMENT.md`, matching its existing convention for exactly
   this kind of machine-specific, compaction-losable detail (already
   covers SDK/emulator/Tesseract/Node/`uv` paths). Add: the real JDK 21
   path on this machine, the exact `org.gradle.java.home` line to add to
   `GRADLE_USER_HOME/gradle.properties`, and a one-line note on why
   (detekt's in-daemon JDK25 crash) so a future session doesn't have to
   rediscover the reasoning.

3. **Apply `detekt` 1.23.8 to the real `android/` project**, scoped
   narrow — private-visibility rules only
   (`UnusedPrivateMember`/`UnusedImports`), matching item #10's original
   intent for this tool (a dead-code check, not a general lint-style
   adoption, which would be a separate, bigger decision). Add the plugin
   to `android/build.gradle.kts` (`apply false`) and
   `android/app/build.gradle.kts` (applied, with a `detekt.yml` enabling
   just those rules, `buildUponDefaultConfig = true` off scope creep).
   No project-level `jvmToolchain()`/task-level `jdkHome`/`jvmTarget`
   needed — Phase 1 confirmed none of that is necessary once the daemon
   JVM itself is correctly pinned via step 1/2's global config.

4. **Run `./gradlew detekt` for real against the actual app code**,
   review genuine findings before fixing/allowlisting anything — same
   honest-verification pattern already used for `vulture`/`knip` this
   session (spot-check each finding against real code, don't blindly
   suppress).

5. **Full-suite regression sweep** — required even though this change
   shouldn't touch compile/test JVMs (only detekt's own task runs
   in-daemon; step 1 already isolates that this doesn't change
   compilation toolchains), but worth confirming for real rather than
   assuming:
   - `./gradlew test` (Minor)
   - `./gradlew connectedDebugAndroidTest` (Major — needs the emulator;
     see `DEV_ENVIRONMENT.md` for the AVD start command)
   - `./gradlew detekt` (confirm it runs clean after any real fixes)
   - Confirm the dashboard's Android row (`dashboard.svg`, via
     `scripts/generate_dashboard.py`) still regenerates correctly.

6. **Update `REPORT_KOTLIN_DETEKT_TOOLCHAIN.md`** with a dated
   "✅ Resolved" section appended (append, don't rewrite the original
   investigation, per this project's pruning convention): the real fix
   (`org.gradle.java.home` pins the Gradle daemon's own JVM — the
   project-level `jvmToolchain()`/`jdkHome` approaches the report
   originally proposed are now confirmed *not* to work), the portability
   answer (global `GRADLE_USER_HOME/gradle.properties`, documented in
   `DEV_ENVIRONMENT.md`, not a repo-committed path), and a link to the
   `android/` commit that applied it.

7. **Update `NEXT_STEPS.md` item #10's Android bullet** and
   `ARCHIVE_DEAD_CODE.md`'s Android section to ✅ closed, same
   trim-to-pointer convention already used for this topic.

8. **Clean up the scratch project** at `G:\ClaudeScratch\detekt-toolchain\`
   — disposable by design, no longer needed once the real repo change is
   verified.

9. **Commit and push** (confirm first, per this session's standing rule)
   — `android/build.gradle.kts`, `android/app/build.gradle.kts`,
   `android/app/detekt.yml` (new), `DEV_ENVIRONMENT.md`,
   `REPORT_KOTLIN_DETEKT_TOOLCHAIN.md`, `NEXT_STEPS.md`,
   `ARCHIVE_DEAD_CODE.md`, this plan's own
   `ClaudePlans/2026-08-24-detekt-phase2-apply.md` save.

## Files

- `G:\GradleUserHome\gradle.properties` — new, machine-global, **not**
  part of the git repo (outside `HDTTools/` entirely)
- `android/build.gradle.kts`, `android/app/build.gradle.kts`,
  `android/app/detekt.yml` (new) — the real detekt config, scoped narrow
- `DEV_ENVIRONMENT.md` — new entry documenting the per-machine JDK21/
  `org.gradle.java.home` setup step
- `REPORT_KOTLIN_DETEKT_TOOLCHAIN.md` — appended "✅ Resolved" section
- `NEXT_STEPS.md`, `ARCHIVE_DEAD_CODE.md` — item #10's Android status
  closed

## Definition of Done

- The global-config placement (step 1) is verified for real in the
  scratch project before being applied to `android/` — not assumed from
  Phase 1's project-level test alone.
- `detekt` runs clean (or with genuinely reviewed/fixed findings)
  against the real `android/app` source, scoped to private-visibility
  rules.
- Full regression sweep (Minor + Major + detekt) passes clean, verified
  by reading real output.
- `REPORT_KOTLIN_DETEKT_TOOLCHAIN.md`, `NEXT_STEPS.md`,
  `ARCHIVE_DEAD_CODE.md`, and `DEV_ENVIRONMENT.md` all reflect the real,
  current, resolved state — no stale "not yet executed"/"deferred"
  language left behind.
- Scratch project cleaned up.
- Everything committed and pushed.

## Verification

1. Real terminal output from the scratch-project global-config
   re-verification (step 1) and from every real-repo Gradle command in
   steps 4-5 — read line-by-line, not assumed green.
2. `git status` clean after the final commit/push, and confirmation that
   no machine-specific path was committed into any file under
   `android/`.
3. `REPORT_KOTLIN_DETEKT_TOOLCHAIN.md` read back in full to confirm the
   appended "Resolved" section is coherent and dated.
