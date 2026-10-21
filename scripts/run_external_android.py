"""Runs the Android External suite on the attached device or emulator, narrowed to the surfaces
the wrapper passes in EXTERNAL_SURFACES (comma-separated), and writes JUnit XML to
EXTERNAL_RESULTS_FILE with each test's surface as a `surface` property, so
scripts/external_wrapper.py can record every surface from its own tests (ADR-0008, #39).

This is the Android counterpart of run_external_pytest.py and src/external/run.ts: android/
test-external.ps1 starts it through the wrapper. A test belongs to a surface through a class-level
`@ExternalSurface("<surface>")` annotation, and the class lives in a file named `*ExternalTest.kt`
directly in TESTS_DIR (the wrapper's `--tests-dir` and `--test-glob` are the same two values, so
the guard that refuses a stale surface with no tests looks where this script does).

The run FAILS, and records the surface failed, when:
  - no device or emulator is attached, or more than one is;
  - the device has no Google Play Services (the emulator image must be a "Google Play" one);
  - the funded Supabase test account cannot be signed in (the helper names the variable that is
    missing or rejected; nothing is built or installed before that);
  - a stale surface has no tagged class, the build or install fails, or the instrumentation run
    crashes, reports a failure, or runs no test at all.
Nothing here skips: the explicit skip is the wrapper's `-Skip`, which never runs this script.

Identity is the funded account the Worker's live suites use (see android/TESTING.md): its id is
written into the device marker file that makes CustomTestRunner configure the real RevenueCat SDK
for it, exactly as android/test-weekly.ps1 does. The access token the sign-in helper also prints is
never read, stored or echoed: these tests spend nothing and call no Worker.

Usage (through the wrapper): android\\test-external.ps1
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import android_release  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
ANDROID_DIR = REPO_ROOT / "android"
TESTS_DIR = ANDROID_DIR / "app" / "src" / "androidTest" / "java" / "com" / "rigcheck" / "app"
TEST_GLOB = "*ExternalTest.kt"
LIVE_TOKEN_CLI = REPO_ROOT / "workers" / "scan-proxy" / "src" / "liveTokenCli.ts"
DEBUG_APK = ANDROID_DIR / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
TEST_APK = ANDROID_DIR / "app" / "build" / "outputs" / "apk" / "androidTest" / "debug" / "app-debug-androidTest.apk"
INSTRUMENTATION = "com.rigcheck.app.test/com.rigcheck.app.CustomTestRunner"
# Must equal WEEKLY_MARKER_PATH in CustomTestRunner.kt: its presence (and text) is how the test app
# learns to configure the real SDK for the funded account.
MARKER_PATH = "/data/local/tmp/rigcheck_weekly_mode"
PLAY_SERVICES = "com.google.android.gms"

_CLASS_PATTERN = re.compile(
    r'@ExternalSurface\("(?P<surface>[^"]+)"\)\s*(?:@\w+(?:\([^)]*\))?\s*)*class\s+(?P<name>\w+)'
)
_PACKAGE_PATTERN = re.compile(r"^package\s+([\w.]+)", re.MULTILINE)
_ACCOUNT_ID = re.compile(r"^[\w-]+$")

# `am instrument -r` status codes of a finished test; 1 is a start.
_PASSED, _SKIPPED, _FAILED = {0}, {-3, -4}, {-1, -2}


class ExternalRunError(Exception):
    """A reason the run cannot go on; main() prints it and fails the run."""


@dataclass(frozen=True)
class CaseResult:

    class_name: str
    name: str
    outcome: str  # "passed" | "failed" | "skipped"
    detail: str = ""


def surface_classes(tests_dir: Path = TESTS_DIR, glob: str = TEST_GLOB) -> dict[str, list[str]]:
    """Surface name -> the fully-qualified names of its tagged test classes."""
    found: dict[str, list[str]] = {}
    for path in sorted(tests_dir.glob(glob)):
        text = path.read_text(encoding="utf-8")
        package = _PACKAGE_PATTERN.search(text)
        prefix = f"{package.group(1)}." if package else ""
        for match in _CLASS_PATTERN.finditer(text):
            found.setdefault(match["surface"], []).append(prefix + match["name"])
    return found


def parse_instrumentation(output: str) -> tuple[list[CaseResult], str | None]:
    """The per-test results of `am instrument -w -r`, and why the run itself broke, if it did.

    A test that started but never reported (the process died) counts as failed."""
    results: list[CaseResult] = []
    started: dict[tuple[str, str], bool] = {}
    block: dict[str, str] = {}
    last_key: str | None = None
    problem: str | None = None
    for raw in output.splitlines():
        line = raw.rstrip("\r")
        if line.startswith("INSTRUMENTATION_STATUS_CODE:"):
            code = int(line.split(":", 1)[1])
            key = (block.get("class", ""), block.get("test", ""))
            if code == 1:
                started[key] = True
            elif key[1]:
                started.pop(key, None)
                outcome = "passed" if code in _PASSED else "skipped" if code in _SKIPPED else "failed"
                results.append(CaseResult(key[0], key[1], outcome, block.get("stack", "") if outcome == "failed" else ""))
            block, last_key = {}, None
        elif line.startswith("INSTRUMENTATION_STATUS:"):
            last_key, _, value = line.split(":", 1)[1].strip().partition("=")
            block[last_key] = value
        elif line.startswith("INSTRUMENTATION_FAILED:") or line.startswith("INSTRUMENTATION_RESULT: shortMsg="):
            problem = line.split(":", 1)[1].strip()
            last_key = None
        elif line.startswith("INSTRUMENTATION_"):
            last_key = None
        elif last_key is not None:  # a multi-line value, e.g. a stack trace
            block[last_key] += "\n" + line
    for class_name, name in started:
        results.append(CaseResult(class_name, name, "failed", "the test started but never reported a result"))
    return results, problem


def junit_xml(results: list[CaseResult], surface_of: dict[str, str]) -> str:
    """JUnit XML with each test's surface as a property (what the wrapper reads)."""
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite", name="android-external", tests=str(len(results)))
    for result in results:
        case = ET.SubElement(suite, "testcase", classname=result.class_name, name=result.name)
        surface = surface_of.get(result.class_name)
        if surface:
            props = ET.SubElement(case, "properties")
            ET.SubElement(props, "property", name="surface", value=surface)
        if result.outcome == "failed":
            failure = ET.SubElement(case, "failure", message=(result.detail.splitlines() or ["failed"])[0])
            failure.text = result.detail
        elif result.outcome == "skipped":
            ET.SubElement(case, "skipped")
    return ET.tostring(root, encoding="unicode")


def default_run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        command, cwd=REPO_ROOT, capture_output=capture, text=True, encoding="utf-8", errors="replace"
    )


def require_one_device(adb: str, run) -> str:
    """The serial of the one ready device or emulator, else why there is not exactly one."""
    devices = android_release.connected_devices(adb=adb, run_command=lambda cmd, **_options: run(cmd, capture=True))
    if not devices:
        raise ExternalRunError(
            "No device or emulator attached (`adb devices` found none). Start the emulator "
            "(emulator -avd medium_phone -no-snapshot-save -gpu swangle_indirect) and wait for it to boot."
        )
    if len(devices) > 1:
        raise ExternalRunError(f"More than one device is attached ({', '.join(devices)}); the External run needs exactly one.")
    return devices[0]


def require_play_services(adb: str, serial: str, run) -> None:
    proc = run([adb, "-s", serial, "shell", "pm", "list", "packages", PLAY_SERVICES], capture=True)
    if f"package:{PLAY_SERVICES}" not in (proc.stdout or "").splitlines():
        raise ExternalRunError(
            f"{serial} has no Google Play Services ({PLAY_SERVICES}), which the External tests need. "
            "Use an emulator image marked \"Google Play\" (the medium_phone AVD is one)."
        )


def funded_account_id(run) -> str:
    """Signs the funded Supabase test account in and returns its id. The helper prints a JSON line
    holding the access token too; it is parsed for the id and never shown. Its own stderr names a
    missing or rejected credential."""
    proc = run(["node", str(LIVE_TOKEN_CLI)], capture=True)
    if proc.returncode != 0:
        raise ExternalRunError(
            "Signing in the funded Supabase test account failed (reason above); nothing was built or installed."
        )
    try:
        account_id = str(json.loads(proc.stdout)["accountId"])
    except (ValueError, KeyError, TypeError):
        raise ExternalRunError("The test-account sign-in returned no account id; nothing was built or installed.") from None
    if not _ACCOUNT_ID.match(account_id):
        raise ExternalRunError("The test-account sign-in returned an account id that is not a plain identifier.")
    return account_id


def run_suite(surfaces: list[str], results_file: Path | None, *, adb: str | None = None, run=default_run,
              tests_dir: Path = TESTS_DIR, out=print) -> int:
    classes = surface_classes(tests_dir)
    surfaces = surfaces or sorted(classes)
    for surface in surfaces:
        if surface not in classes:
            raise ExternalRunError(f"No Android test class is tagged @ExternalSurface(\"{surface}\") in {tests_dir}.")
    surface_of = {cls: surface for surface in surfaces for cls in classes[surface]}

    adb = adb or android_release.default_adb()
    serial = require_one_device(adb, run)
    require_play_services(adb, serial, run)
    account_id = funded_account_id(run)

    def adb_cmd(*args: str) -> list[str]:
        return [adb, "-s", serial, *args]

    build = run([android_release.GRADLEW, "-p", str(ANDROID_DIR), "assembleDebug", "assembleDebugAndroidTest"])
    if build.returncode != 0:
        raise ExternalRunError("The Gradle build failed.")
    for apk in (DEBUG_APK, TEST_APK):
        if run(adb_cmd("install", "-r", str(apk))).returncode != 0:
            raise ExternalRunError(f"Installing {apk.name} failed.")

    # An idle screen makes Compose tests fail with a misleading "No compose hierarchies found".
    run(adb_cmd("shell", "input", "keyevent", "KEYCODE_WAKEUP"))
    run(adb_cmd("shell", "svc", "power", "stayon", "true"))
    marker = run(adb_cmd("shell", f"echo {account_id} > {MARKER_PATH}"))
    if marker.returncode != 0:
        raise ExternalRunError("Could not write the marker file on the device.")
    try:
        proc = run(
            adb_cmd("shell", "am", "instrument", "-w", "-r", "-e", "class", ",".join(sorted(surface_of)), INSTRUMENTATION),
            capture=True,
        )
    finally:
        # A later Gradle run must not see the marker, and a test that died offline must not leave
        # the emulator in airplane mode (the offline test restores it itself on every other path).
        run(adb_cmd("shell", "rm", "-f", MARKER_PATH))
        run(adb_cmd("shell", "cmd", "connectivity", "airplane-mode", "disable"))

    results, problem = parse_instrumentation(proc.stdout or "")
    for result in results:
        out(f"{result.outcome.upper():7} {result.class_name.rsplit('.', 1)[-1]}#{result.name}")
        if result.detail:
            out(result.detail)
    if results_file is not None:
        results_file.write_text(junit_xml(results, surface_of), encoding="utf-8")
    if problem:
        out(f"The instrumentation run reported: {problem}")
    if not results:
        out("No test ran; failing the run.")
    ok = proc.returncode == 0 and not problem and bool(results) and all(r.outcome != "failed" for r in results)
    return 0 if ok else 1


def main(argv: list[str] | None = None, *, env=None, **kwargs) -> int:
    env = os.environ if env is None else env
    surfaces = [s for s in env.get("EXTERNAL_SURFACES", "").split(",") if s]
    results = env.get("EXTERNAL_RESULTS_FILE")
    out = kwargs.get("out", print)
    try:
        return run_suite(surfaces, Path(results) if results else None, **kwargs)
    except (ExternalRunError, RuntimeError) as exc:  # RuntimeError: adb could not be found
        out(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
