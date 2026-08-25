# Dev environment reference (this machine)

Local tool paths, install locations, and run commands for this specific
Windows dev machine — written 2026-08-24 because the Android SDK/emulator
setup kept getting rediscovered from scratch after every context
compaction. **This file is machine-specific, not portable** — a second
machine (see `NEXT_STEPS.md`'s "Fresh-machine setup checklist") will have
different paths; update this file, don't assume it, if you set up on a
new machine. Every path/command below is copy-pasteable as written — grep
this file for a product line name or tool name rather than re-discovering
via `Get-Command`/`where`.

## Android

- SDK root: `G:\Android\Sdk` (env var `ANDROID_SDK_ROOT` — `ANDROID_HOME`
  is *not* set, only `ANDROID_SDK_ROOT`; `android/local.properties`
  (gitignored, Android-Studio-generated) also points `sdk.dir` here).
- Android Studio: `G:\Android\AndroidStudio` — its bundled JDK is
  `G:\Android\AndroidStudio\jbr`, already set as the machine's
  `JAVA_HOME` env var, so `gradlew` just works with no extra setup.
- The Gradle *daemon's own* JVM is separately pinned to JDK 21 via
  `android/gradle/gradle-daemon-jvm.properties` (git-committed, real
  per-platform foojay download URLs baked in by
  `./gradlew updateDaemonJvm --jvm-version=21`) — auto-provisions on any
  machine, no manual setup needed. See the detekt gotcha below for why
  this exists; it's separate from the `JAVA_HOME` env var above, which
  only affects the wrapper's own bootstrap launcher.
- `adb`: `G:\Android\Sdk\platform-tools\adb.exe`
- `emulator`: `G:\Android\Sdk\emulator\emulator.exe`
- The one configured AVD: **`medium_phone`**

```powershell
# List AVDs (confirms the SDK path and the AVD name above are still real)
& "G:\Android\Sdk\emulator\emulator.exe" -list-avds

# Start the emulator (headless-friendly; runs in the background)
Start-Process -FilePath "G:\Android\Sdk\emulator\emulator.exe" `
  -ArgumentList "-avd","medium_phone","-no-snapshot-save" -WindowStyle Hidden

# Confirm it's attached
& "G:\Android\Sdk\platform-tools\adb.exe" devices

# Wait for a real boot (not just "device" showing in `adb devices` -
# that can appear before the OS is actually ready)
$adb = "G:\Android\Sdk\platform-tools\adb.exe"
for ($i=0; $i -lt 40; $i++) {
  $val = & $adb -s emulator-5554 shell getprop sys.boot_completed 2>$null
  if ($val -match "1") { break }
  Start-Sleep -Seconds 5
}
```

Test/coverage commands — see `android/TESTING.md` for the full
Minor/Major/External breakdown; the raw commands (run from `android/`):

```powershell
.\gradlew.bat test                                                      # Minor (Unit, JVM) - no device needed
.\gradlew.bat connectedDebugAndroidTest                                 # Major (instrumented) - needs a booted device
.\gradlew.bat connectedDebugAndroidTest createDebugAndroidTestCoverageReport  # Major + real coverage report
.\test-weekly.ps1                                                       # External (real RevenueCat) - needs a booted device
```

Real JaCoCo coverage report lands at
`android/app/build/reports/coverage/androidTest/debug/connected/index.html`
(Major suite) or `.../coverage/test/debug/index.html` (Minor/Unit suite)
— both HTML only, no XML report configured. `scripts/coverage_gate.py`
parses the HTML `Total` row directly (see that script's own docstring).

## Python / backend / Streamlit

- `uv`: `C:\Users\Angela\.local\bin\uv.exe` (also just `uv` if it's on
  PATH in the current shell — it usually is).
- Project virtual environment: `.venv` at the repo root, created/synced
  via `uv sync` — never activate/use a global Python.
- Tesseract OCR engine (real, installed on this machine):
  `C:\Program Files\Tesseract-OCR\tesseract.exe`. Auto-detected by
  `src/hdttools/ocr_common.py::ensure_tesseract_configured()` from a
  fixed candidate-paths list — this exact path is already in that list,
  so no env var or config is needed on this machine specifically.

```bash
uv sync                                              # install/sync deps into .venv
uv run pytest -q                                     # full suite
uv run pytest --cov --cov-report=term-missing        # with coverage
uv run uvicorn hdttools.api.main:app --reload --port 8000   # backend API, localhost:8000
uv run streamlit run streamlit_app/app.py            # Streamlit wizard (self-contained, no backend needed)
uv run scripts/coverage_gate.py                      # cross-platform coverage gate
```

Streamlit one-time setup (already done on this machine, only needed
again on a fresh one — see `NEXT_STEPS.md`'s fresh-machine checklist for
why): `~/.streamlit/credentials.toml` (`email = ""`) and
`~/.streamlit/config.toml` (`gatherUsageStats = false`,
`server.headless = true`).

## Web (`web/`)

- Node: `C:\Program Files\nodejs\node.exe` (v24.19.0 as of 2026-08-24)
- npm: `C:\Program Files\nodejs\npm.ps1`

```bash
cd web
npm install
npm run dev            # localhost:5173
npm test                # vitest run - 71 tests
npm run test:coverage   # vitest run --coverage, report at web/coverage/coverage-summary.json
npm run build           # tsc -b && vite build
```

## `workers/scan-proxy`

Same Node/npm as Web, run from `workers/scan-proxy/`:

```bash
npm test                 # Major suite (node --test src/*.test.ts)
npm run test:sanity      # Minor suite ([sanity]-tagged subset)
npm run test:coverage    # Major suite + node --experimental-test-coverage
npm run test:weekly      # External (through-our-service) - real, bounded, needs a deployed Worker
.\test-release.ps1       # External (direct-provider-boundary) - needs ANTHROPIC_API_KEY/REVENUECAT_SECRET_KEY in the shell
npm run dev               # wrangler dev
npm run deploy             # wrangler deploy
```

## Gotchas specific to this machine

- `adb` is **not** on PATH in a fresh shell — always use the full path
  above, or `& "G:\Android\Sdk\platform-tools\adb.exe" start-server`
  first if you want bare `adb` to resolve afterward (it won't; PATH
  isn't modified by that, this is just a reminder it needs the full path
  every time in a new shell).
- An idle/sleeping emulator screen makes instrumented Compose tests fail
  with a misleading "No compose hierarchies found in the app" error —
  `android/app/build.gradle.kts`'s `wakeEmulatorForInstrumentedTests`
  task already handles this automatically for
  `connectedDebugAndroidTest`, but if you're driving `adb`/the emulator
  directly for something else, wake it first.
- **Why `android/gradle/gradle-daemon-jvm.properties` is pinned to JDK
  21, not left on this machine's ambient JDK 25**: `detekt` 1.23.8's
  analysis runs in-process inside the Gradle daemon's own JVM, and that
  JVM doesn't recognize JDK 25 (`IllegalArgumentException: 25.0.2`, real
  trace in `REPORT_KOTLIN_DETEKT_TOOLCHAIN.md`). Neither a project-level
  Kotlin toolchain pin (`jvmToolchain()`) nor the Detekt task's own
  `jdkHome` property fixes this — both were tried and confirmed not to
  work, since neither actually redirects the daemon's own JVM; only
  Gradle's own "Daemon JVM criteria" file does. This is portable and
  needs no per-machine setup — `./gradlew` reads the committed
  `gradle-daemon-jvm.properties` and auto-downloads a matching JDK 21 via
  foojay on first use, same as it did on this machine.
