# Report: detekt vs. JDK 25 — a real Gradle-plugin/JDK incompatibility

Written 2026-08-24, during roadmap item #10's dead-code sweep (see
`NEXT_STEPS.md` item #10 for current status, `ARCHIVE_DEAD_CODE.md` for
the sweep's other, unaffected platforms). This is a standalone report,
not part of the main `ARCHIVE_*.md` chain, because it turned into a
side investigation with its own proposed fix and its own not-yet-executed
test plan — a reader doesn't need any other file's context to follow this
one.

## Summary

Adding `detekt` (Kotlin's standard static-analysis tool) to the Android
project's dead-code sweep failed with a real, reproducible crash: the
latest stable `detekt` release doesn't recognize this machine's JDK
(version 25) at all, and a Gradle-toolchain workaround that should have
fixed it didn't, exposing a real gap in detekt's own Gradle plugin. No
stable fix exists yet upstream. The proposed direction is to pin the
whole Android build to a specific, Gradle-managed JDK version instead of
relying on whatever JDK happens to be ambient on a given machine — which
would fix this specific problem and prevent the same failure class from
recurring silently in the future. That fix needs to be proven in an
isolated scratch project first, before being applied to this real repo;
that experiment has not been run yet.

## Background

Item #10's dead-code sweep picked one real, low-false-positive tool per
platform: `vulture` for Python, `knip` for Web and `scan-proxy` — both
stood up cleanly, both found real, fixable issues, both fully documented
in `ARCHIVE_DEAD_CODE.md`. Android's equivalent tool for "is this
private/unused code actually dead" is `detekt`, the standard Kotlin
static-analysis tool with a rule for exactly this
(`UnusedPrivateMember`/`UnusedImports`). Adding it should have been the
same shape of work as the other two platforms. It wasn't — it uncovered
a real environment problem instead.

Why this matters beyond just "detekt didn't work": this machine's ambient
JDK (`JAVA_HOME`, pointing at Android Studio's bundled JBR) is currently
JDK 25 — a very recent release. That's not a deliberate choice anyone on
this project made; it's just whatever Android Studio's install happened
to bundle, and it can change again silently on the next Studio update
with zero code change on this project's side. The class of failure this
report documents — a tool that bundles its own analysis compiler
crashing because that compiler doesn't recognize a new JDK major version
— isn't specific to detekt. Any similarly-built tool could hit the same
thing. That's the real reason the proposed fix (below) is about the
build's JDK story generally, not just "get detekt working."

## The finding

`./gradlew detekt` (Android's Gradle build, `android/` directory) fails
with:

```
Caused by: org.gradle.api.GradleException: 25.0.2
Caused by: java.lang.reflect.InvocationTargetException
Caused by: java.lang.IllegalArgumentException: 25.0.2
	at io.github.detekt.parser.KotlinEnvironmentUtilsKt.createKotlinCoreEnvironment(KotlinEnvironmentUtils.kt:61)
	at io.gitlab.arturbosch.detekt.core.settings.EnvironmentFacade.environment_delegate$lambda$0(EnvironmentAware.kt:45)
	...
```

`25.0.2` is this machine's real JDK version string (Android Studio's
bundled JetBrains Runtime). `detekt` 1.23.8's bundled Kotlin compiler
tries to parse its own host JVM's version internally, as part of setting
up its analysis environment, and throws because it doesn't recognize
major version 25 as valid — this happens independent of whatever
bytecode target the *project itself* compiles to (this app already
targets Java 11 bytecode; the crash is about the JVM *running* the
analysis, not what it produces).

## Investigation, in order

1. **First error, fixed**: before the above, the very first attempt
   failed with `Invalid value (25) passed to --jvm-target, must be one
   of [1.6, 1.8, 9, 10, ..., 22]` — detekt's own `--jvm-target` compiler
   flag rejecting 25 outright. Fixed by explicitly pinning
   `jvmTarget = "21"` on the Detekt Gradle task (detekt's own analysis
   doesn't need to match the app's real compile target exactly). This
   got past the *first* error and exposed the second, deeper one above.

2. **Toolchain workaround attempted, didn't actually work**: configured
   the Detekt task's `jdkHome` property to a Gradle-managed JDK 21
   toolchain, using the `JavaToolchainService` already available via the
   foojay resolver plugin this project's `settings.gradle.kts` already
   configures (`org.gradle.toolchains.foojay-resolver-convention`).
   Gradle genuinely downloaded a real JDK 21
   (`eclipse_adoptium-21-amd64-windows.2`, ~2.5 minutes, confirmed on
   disk at `G:\GradleUserHome\jdks\`) — the toolchain mechanism itself
   worked correctly. Re-ran `./gradlew detekt` anyway: **identical
   crash**. `jdkHome` on detekt's `Detekt` Gradle task type does not
   actually redirect which JVM process runs the CLI analysis (it likely
   only affects classpath resolution for type-checking, not process
   launch) — a real gap in detekt 1.23.8's Gradle plugin, not a
   configuration mistake on this project's side.

3. **Confirmed there's no newer stable fix**: queried Maven Central's
   real metadata directly (not relying on training-data memory, which
   would be stale for a project this far past any model's knowledge
   cutoff) —

   ```bash
   curl -s "https://repo1.maven.org/maven2/io/gitlab/arturbosch/detekt/detekt-gradle-plugin/maven-metadata.xml"
   ```

   confirms `1.23.8` genuinely is the latest release under the classic
   `io.gitlab.arturbosch.detekt` group — nothing newer exists there to
   upgrade to.

4. **Found the successor, found it's alpha-only**: detekt has migrated
   to a new Maven group, `dev.detekt`, for its actively-developed
   successor. That group's real metadata:

   ```bash
   curl -s "https://repo1.maven.org/maven2/dev/detekt/detekt-gradle-plugin/maven-metadata.xml"
   ```

   lists only `2.0.0-alpha.0` through `2.0.0-alpha.6` — no stable
   release yet.

5. **Found real evidence the successor likely does fix this**: inspected
   `dev.detekt:detekt-parser:2.0.0-alpha.6`'s real Gradle module
   metadata (the `.module` file, which lists resolved dependency
   versions precisely):

   ```bash
   curl -s ".../detekt-parser-2.0.0-alpha.6.module" | grep -A3 '"group": "org.jetbrains.kotlin"'
   ```

   shows it depends on `kotlin-compiler` **2.4.10** — a substantially
   newer bundled compiler than whatever 1.23.8 uses internally, and a
   plausible real reason the JDK-version-parsing bug is fixed there:
   Kotlin's own compiler-embeddable JDK-detection logic has needed
   updates before to recognize each new JDK major version as it's
   released, and 2.4.10 postdates JDK 25's release far more comfortably
   than whatever compiler 1.23.8 bundles.

   Note: this is about the Kotlin compiler *detekt bundles internally*
   for its own analysis, not this project's own Kotlin version (this
   project is on Kotlin 2.2.10, confirmed in
   `android/gradle/libs.versions.toml`) — those are independent. Bumping
   this project's own Kotlin version would not, by itself, fix detekt's
   bundled-compiler crash.

## Options considered, with real tradeoffs

**Downgrade Android Studio to a release bundling an older JBR.**
Rejected. Android Studio's *IDE* version is actually decoupled from what
matters for automated builds — every test script this session used
(`gradlew.bat`, `adb`, `test-weekly.ps1`) invokes the SDK/Gradle
directly, never through Studio's IDE process, and the Android SDK/
emulator/AVDs are separately-versioned components, not bundled inside
Studio's own install. So downgrading Studio is *low risk* to the
emulator-based test scripts specifically — but it's still the wrong
fix: it doesn't address the actual root cause (this machine's JDK being
*ambient*, i.e. determined by whatever happens to be installed, not by
anything the project declares), it costs more (a real system-wide
reinstall, needing explicit permission per this project's own
System Tool Installs rule, plus research to find a specific older Studio
release bundling JDK ≤22), and it's less durable — the *next* Studio
update could silently re-drift the bundled JBR forward and reproduce
this exact failure again, with zero warning, exactly like happened this
time.

**Adopt `dev.detekt` 2.0.0-alpha.6.** A real option — the evidence above
suggests it would likely just work. The cost is adopting alpha software
(API/config still subject to change) for what should be a routine,
low-stakes dev-tool addition — not necessarily wrong, but worth entering
deliberately rather than as the path of least resistance.

**Pin a Gradle toolchain project-wide (recommended direction).** Declare
the JDK version the whole Android build should run under, in the project
files themselves, instead of inheriting whatever's ambient. Gradle then
either finds a matching local JDK or downloads one (the same
foojay-resolver mechanism already proven working this session — no new
system-wide install).

- **Reward**: fixes detekt (or any future tool with the same class of
  JDK-version sensitivity) by making sure the pinned version is what
  everything runs under. Reproducible across every machine/CI runner.
  Immune to the exact failure that caused this investigation — a future
  Studio update literally cannot change what JDK the build uses once
  it's pinned in the project's own files.
- **Risk**: broader blast radius — this changes which JVM runs *every*
  Gradle task, not just detekt, so it needs a full-suite regression pass
  (Minor + Major + a real detekt run) before being trusted, not just a
  detekt-specific check. There's a real, not-yet-verified question about
  whether AGP 9.3.1 and Kotlin 2.2.10 (this project's current versions)
  cleanly respect Kotlin's `jvmToolchain()` DSL — AGP/Kotlin toolchain
  interop has had rough edges historically, and this needs an empirical
  test, not an assumption. There's also a real but subtle distinction to
  get right during implementation: `jvmToolchain()` picks the JDK
  *executable* that runs the build; it's independent of
  `sourceCompatibility`/`targetCompatibility` (already `VERSION_11` in
  `app/build.gradle.kts`), which controls the bytecode *target* the app
  compiles to — pinning the toolchain to a newer-than-11 JDK doesn't
  change what bytecode the app produces, but the two settings are easy
  to conflate.

## Proposed solution

Pin the Android build to a specific Gradle-managed JDK toolchain (JDK
21 is the leading candidate — it's what detekt 1.23.8 already proved it
can parse, and it's an LTS release), rather than relying on whatever
JDK happens to be ambient (`JAVA_HOME`) on a given machine. This fixes
the immediate detekt problem and removes the underlying fragility (silent
JDK drift from IDE updates) that caused it, for this and any future tool.

## Proposed test plan — not yet executed

Deliberately deferred as a side effort, separate from the main HDTTools
project, to be picked up in a future session:

1. **Build a small, disposable scratch Android module outside this
   repo** — on `G:`, not `C:` (matching this machine's space-constrained
   boot drive), location to be confirmed with the user before creating
   it (a fresh system-tool-adjacent action, worth a quick check-in even
   though it's not literally a system install). Minimal dependencies —
   no Compose, no RevenueCat, nothing beyond what's needed to apply
   detekt — so each trial iterates fast (small Gradle sync, no unrelated
   version constraints from a heavier dependency graph).
2. **Search the real combination space**: AGP version × Kotlin version ×
   detekt version (both `io.gitlab.arturbosch.detekt` and `dev.detekt`
   alpha releases are fair game) × Gradle-toolchain JDK version. Confirm
   which combination actually resolves *and* runs `detekt` successfully
   against a trivial source file with an intentionally-unused private
   member, proving the rule genuinely fires, not just that the plugin
   loads without crashing.
3. **Do not trust the minimal repro's result alone.** A working
   combination in the scratch project is evidence, not proof, for this
   real repo — real interop issues (the AGP/Kotlin toolchain question
   above) sometimes only surface with the full real dependency graph
   (Compose BOM, RevenueCat SDK, kotlinx-serialization, etc.).
4. **Apply the confirmed-working combination to this repo as one
   deliberate change** — the same pattern already used successfully for
   `vulture`/`knip` this session: add the plugin/config for real, run it
   against real code, review real findings before removing anything, and
   run the *full* regression sweep (`./gradlew test`,
   `./gradlew connectedDebugAndroidTest`, a real `./gradlew detekt`) to
   confirm zero regressions before treating this as done.
5. **Update this report and `NEXT_STEPS.md` item #10** once resolved —
   this file should get a dated "✅ Resolved" section added (per this
   project's own pruning convention: append, don't silently delete the
   original investigation), not be rewritten from scratch.

## ✅ Resolved, 2026-08-24

The test plan above ran in a scratch Android module at
`G:\ClaudeScratch\detekt-toolchain\` (targeted, cheapest-first: try the
most likely fix and stop on success, rather than a full matrix sweep).
The proposed solution's *direction* (pin the build to a specific JDK)
was right, but its proposed *mechanism* — `kotlin { jvmToolchain(21) }`
— turned out to be wrong, and the real, simpler fix was found instead.

**What the scratch trials actually showed**: `kotlin { jvmToolchain(21) }`
does **not** fix the crash — confirmed by adding it, then removing it
again, with identical pass/fail either way. This makes sense in
hindsight and matches the earlier `jdkHome`-on-the-Detekt-task finding
above: `detekt`'s analysis runs **in-process inside the Gradle daemon's
own JVM**, not a separately forked process. Nothing that only configures
a project/task-level toolchain can redirect that — only pinning the JVM
that runs Gradle itself works. Confirmed with a real positive control:
detekt correctly flagged an intentionally-unused private function
(`[UnusedPrivateMember]`) once the daemon's own JVM was JDK 21, using
`detekt` 1.23.8 — the existing latest-stable version, no alpha software
needed.

**The real fix**: this project's Android build already used Gradle's
"Daemon JVM criteria" feature — a git-committed
`android/gradle/gradle-daemon-jvm.properties` file (present since the
project's very first Android commit, `149d7a0`), which pins exactly
which JVM the daemon runs under and auto-provisions it via the same
foojay resolver already proven working in this investigation. It was
simply pinned to JDK 25 (whatever was ambient when the file was first
generated). Re-running:

```
./gradlew updateDaemonJvm --jvm-version=21
```

regenerated that file pinned to JDK 21 instead, with real per-platform
foojay download URLs baked in. This is fully portable — no manual
per-machine setup, unlike an earlier intermediate step in this
investigation that used `org.gradle.java.home` in a machine-specific,
uncommitted `gradle.properties` (superseded once this mechanism was
found; not part of the final fix). No project-level `jvmToolchain()`,
no task-level `jdkHome`/`jvmTarget` override — none of that was needed
once the daemon's own JVM was correctly pinned via the committed file.

**Applied to the real repo**: `detekt` 1.23.8 added to `android/app`,
scoped narrow to the two rules the dead-code sweep actually needs
(`UnusedPrivateMember`, `UnusedImports`) via `buildUponDefaultConfig =
false` plus a minimal `android/app/detekt.yml` — confirmed empirically
in the scratch project that this combination fires *only* those two
rule types, not the ~40 other rules active by default in detekt's
`style` ruleset alone (an early scratch trial with
`buildUponDefaultConfig = true` had also flagged `FunctionOnlyReturningConstant`,
real evidence of exactly the scope creep this sweep was meant to avoid).

Ran for real against all 45 Kotlin files in `android/app`: 3 genuine
unused imports found (`ScanOrManualChooser.kt`, `DisclaimerScreen.kt`,
`TruckTagEntryScreen.kt`), each spot-checked via `grep` before removal
to confirm no other reference existed in its file, then removed.
`./gradlew detekt` now runs clean. Full regression sweep passed for
real: `./gradlew test` (Minor, 31/31), `./gradlew connectedDebugAndroidTest`
(Major, 39/39 on the `medium_phone` emulator), `dashboard.svg`
regenerated correctly.

Roadmap item #10's Android leg is closed. See `DEV_ENVIRONMENT.md`'s
detekt gotcha for the mechanism summary kept alongside the other
machine/build notes.
