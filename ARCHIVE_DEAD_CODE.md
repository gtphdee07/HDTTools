# Archive: dead-code sweep (roadmap item #10)

New archive file, 2026-08-24 — split out from `ARCHIVE_TESTING.md` once
that file crossed the ~1000-line split threshold `Claude.md`'s Archive
discipline rule calls for, right as this new topic of work started
anyway. See `NEXT_STEPS.md` item #10 for current status;
`ClaudePlans/2026-08-24-dead-code-sweep.md` for the approved plan.

## ✅ `parse_label.py` confirmed dead code and removed, 2026-08-24

The one already-known candidate (flagged in `NEXT_STEPS.md` item #8's
Python coverage baseline, 2026-08-23, as 0%-covered and "worth
confirming... not yet checked") — resolved as the plan's fast first step
before any tool was even installed.

**What it actually was**: a stray prototype file under
`src/hdttools/parse_label.py` — module-level code (`results = {...};
print(json.dumps(results, indent=2))`) that ran on import, plus a
leftover comment ("Retry execution of fixed script") signaling it was
scratch work from early truck-tag-OCR-regex experimentation, never wired
into the real `truck_tag_ocr.py`/`trailer_tag_ocr.py` modules those
regexes eventually landed in for real.

**Already excluded from git** via `.gitignore` ("Local scratch notes/
fragments, not part of the application") — so despite living on disk and
showing up in a local coverage report, it was never actually part of the
shipped repository at all. This is why it needed a different close-out
than a normal dead-code removal: no `git rm`, just deleting the local
file and removing the now-pointless `.gitignore` line that excluded it.

**Confirmed unreferenced before deletion** (per this project's TDD/
honest-verification discipline — no deletion without confirming first): a
repo-wide grep for `parse_label`/`parse_volvo_label` (its second,
also-unused function) found zero matches in any real code — only in
`NEXT_STEPS.md`'s own prose and the `.gitignore` pattern that excluded
it, both cleaned up as part of this close-out.

**Net effect**: `src/hdttools/parse_label.py` deleted;
`.gitignore`'s now-pointless exclusion line removed; `NEXT_STEPS.md`
item #8's Python baseline bullet updated to reflect it as closed rather
than "not yet checked."

## ✅ Python: `vulture` stood up, zero genuine dead code found, 2026-08-24

Added as a dev dependency (`uv add --dev vulture`). Real run against
`src/hdttools`/`streamlit_app` found 65 findings at default confidence —
**every one a false positive**, across exactly three categories, each
spot-checked against real code before being whitelisted (not blindly
kept from vulture's own `--make-whitelist` stub):

1. **FastAPI route handlers** (`extract_truck_tag`/`extract_trailer_tag`/
   `extract_scale_ticket`/`create_breakdown` in `api/main.py`) — reachable
   only via `@app.post(...)` decorators; vulture has no framework-routing
   awareness. Confirmed real by reading each decorator directly.
2. **Pydantic/dataclass model field declarations** (`schemas.py`,
   `models.py` — ~55 of the 65 findings) — class-level annotated
   attributes are a well-known vulture false-positive class: "used" by
   the framework reading `__annotations__`, never by a direct AST-visible
   name reference.
3. **This repo's deliberate public library API**
   (`read_scale_ticket`/`read_truck_tag`/`read_trailer_tag`/
   `read_truck_tag_ocr`/`read_trailer_tag_ocr`) — meant for external
   callers per `README.md`'s "Underlying toolkit" section, so "no
   in-repo caller" is correct, not a sign of dead code. The two `_ocr`
   variants aren't literally re-exported from `__init__.py` (unlike the
   other three) but were confirmed real by reading each function
   directly — same file-picker/review-form/save CLI-tool shape as the
   exported ones.

`vulture_whitelist.py` (repo root) documents all three categories with
the reasoning inline. `streamlit_app/` alone (no `src/hdttools`) found
**zero** findings even before any whitelist — genuinely clean. With the
whitelist applied, `uv run vulture src/hdttools streamlit_app
vulture_whitelist.py` exits clean. No genuine dead code found beyond
`parse_label.py` above.

## ✅ Web + `scan-proxy`: `knip` stood up, 4 real fixes, zero genuine dead code, 2026-08-24

Chosen over `ts-prune` (narrower scope, less actively maintained) — knip
checks unused exports/files/dependencies in one pass with built-in
`entry`/`ignore` config. Ran via `npx knip` first in each project to see
real output before deciding to keep it (both proved worth keeping — 100%
real signal, zero false positives — added as a `knip` devDependency +
`npm run check:dead-code` script in both).

**Real findings, both projects — the exact same category every time**:
an exported type/interface/const that *was* genuinely used, just
unnecessarily `export`ed — nothing outside its own file ever imported it
by name, because the type/const that actually gets imported elsewhere
(`ModuleDef`, `WizardState`, `runScan`) already includes it structurally,
and TypeScript's structural typing means a consumer never needs the
inner piece imported separately. Fixed by removing the `export` keyword
only — nothing deleted, since the code itself is real and used:

- Web: `FieldType`/`FieldDef` (`mockData.ts`), `TireSpec`/`WizardSubStep`
  (`types.ts`).
- `scan-proxy`: `DOC_TYPES`/`MEDIA_TYPES` (`request.ts`),
  `defaultScanDeps` (`scan.ts` — backs `runScan`'s default parameter
  value; confirmed via grep that nothing ever calls `runScan` with an
  explicit `deps` argument).

Every fix confirmed via `git grep` for the name across the whole project
(including test files) before touching it, then verified via a clean
typecheck/build and a full test-suite run afterward (Web: `npm run
build` + 71/71 tests; scan-proxy: `npm run typecheck` + 57/57 tests). No
allowlist/ignore config ended up needed for either project — knip's
default entry-point detection (via each `package.json`/`tsconfig.json`)
already correctly recognized `main.tsx` and the Worker's `index.ts` as
real entry points without any manual config. Both `npm run
check:dead-code` commands exit clean (0 findings) as of this writing.

## 🔶 Android: `detekt` deferred - a real plugin/JDK incompatibility, 2026-08-24

Attempted: `detekt` (`io.gitlab.arturbosch.detekt`) 1.23.8 — the latest
stable release — added as a Gradle plugin, scoped deliberately narrow
(`buildUponDefaultConfig = false`, only `UnusedImports`/
`UnusedPrivateMember` active, chosen for low false-positive risk vs.
detekt's full default rule set or whole-program public-symbol
reachability).

**Real, reproducible failure, not a config mistake**: `./gradlew detekt`
crashed with `IllegalArgumentException: 25.0.2` deep in detekt's bundled
Kotlin compiler (`KotlinEnvironmentUtilsKt.createKotlinCoreEnvironment`)
— it doesn't recognize this machine's real JDK (Android Studio's bundled
JBR, JDK 25) when parsing its own runtime `java.version` string,
independent of the `--jvm-target` compile flag (fixed first, separately,
by pinning `jvmTarget = "21"` on the Detekt task — that got past the
*first* error, "Invalid value (25)... must be one of [1.6, 1.8, 9-22]",
before hitting this second, deeper one).

**Worked around the JVM issue, but the plugin itself didn't honor it**:
configured the Detekt task's `jdkHome` to a Gradle-managed JDK 21
toolchain (auto-provisioned for real via the foojay resolver already
configured in `settings.gradle.kts` — confirmed a real
`eclipse_adoptium-21-amd64-windows.2` install landed in
`G:\GradleUserHome\jdks\`, ~2.5 minutes to download). Re-ran — **same
crash**. `jdkHome` on the `Detekt` task type apparently doesn't actually
redirect which JVM process runs the CLI invocation (likely only affects
classpath resolution for type-analysis, not process launch) - a real gap
in detekt 1.23.8's Gradle plugin API, not a config error on this side.

**Checked for a newer fix before giving up**: detekt's Maven Central
metadata confirms 1.23.8 genuinely is the latest release under the
`io.gitlab.arturbosch.detekt` group. The project has migrated to a new
`dev.detekt` group for its actively-developed successor, but that group
only has alpha pre-releases published (`2.0.0-alpha.0` through
`2.0.0-alpha.6` — no stable release yet) — confirmed via that group's own
`maven-metadata.xml`, not guessed from training-data memory (which would
be stale this far past this session's own knowledge cutoff anyway).

**Decided (user's call, presented with the real tradeoffs)**: defer
Android's dead-code tool rather than force a fix. The two remaining
options — force the whole Gradle daemon onto the already-downloaded JDK
21 via `org.gradle.java.home` (works, but changes the JVM for *every*
Gradle invocation on this machine going forward, not just this one dev
tool), or adopt `dev.detekt` 2.0.0-alpha.6 (alpha software risk for a
routine dev-tool addition) — were both judged worse than simply not
having this one tool yet. All detekt-related changes were fully reverted
(`git status` confirmed clean) rather than left half-working in the
build files. Python (`vulture`) and Web/`scan-proxy` (`knip`) are fully
done and clean; picking this back up (either option above, or checking
again later for a stable `dev.detekt` release) is tracked as open in
`NEXT_STEPS.md` item #10.
