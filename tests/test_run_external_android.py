"""Function tests for scripts/run_external_android.py (#39): the Android External runner that
external_wrapper.py calls. A fake command runner stands in for gradle, adb and the sign-in helper, so
no device, build, network or credential is touched. The instrumentation output used here has the
shape `adb shell am instrument -w -r` really printed on the medium_phone emulator (2026-10-20)."""

import importlib.util
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

pytestmark = [pytest.mark.core, pytest.mark.minor]

_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = _ROOT / "scripts"
sys.path.insert(0, str(_SCRIPTS))
for _name in ("external_freshness", "external_wrapper", "run_external_android"):
    _spec = importlib.util.spec_from_file_location(_name, _SCRIPTS / f"{_name}.py")
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[_name] = _module
    _spec.loader.exec_module(_module)

rea = sys.modules["run_external_android"]
ew = sys.modules["external_wrapper"]
ef = sys.modules["external_freshness"]

SURFACE = "revenuecat-android-sdk"
CLASS = "com.rigcheck.app.RevenueCatAndroidSdkExternalTest"
ACCOUNT = "0fb5d148-58cf-489a-be2b-e85eb885a190"
TOKEN = "eyJ-secret-access-token"


def _block(*lines):
    return list(lines)


def instrumentation_output(tests):
    """`am instrument -r` text for (name, status_code, stack) tests, CRLF like adb prints it."""
    lines = []
    for name, code, stack in tests:
        head = [f"INSTRUMENTATION_STATUS: class={CLASS}", "INSTRUMENTATION_STATUS: current=1",
                "INSTRUMENTATION_STATUS: id=AndroidJUnitRunner", "INSTRUMENTATION_STATUS: numtests=6"]
        lines += [*head, "INSTRUMENTATION_STATUS: stream=", f"{CLASS}:", f"INSTRUMENTATION_STATUS: test={name}",
                  "INSTRUMENTATION_STATUS_CODE: 1"]
        if code is None:
            continue  # the process died before the test reported
        lines += head
        if stack:
            lines += [f"INSTRUMENTATION_STATUS: stack={stack[0]}", *stack[1:], "",
                      "INSTRUMENTATION_STATUS: stream=", f"Error in {name}({CLASS}):", stack[0]]
        else:
            lines += ["INSTRUMENTATION_STATUS: stream=."]
        lines += [f"INSTRUMENTATION_STATUS: test={name}", f"INSTRUMENTATION_STATUS_CODE: {code}"]
    return "\r\n".join(lines) + "\r\n"


PASSING = instrumentation_output([("offeringsWork", 0, None), ("loginWorks", 0, None)])
FAILING = instrumentation_output([
    ("offeringsWork", 0, None),
    ("loginFails", -2, ["java.lang.AssertionError: no SCAN entry", "\tat org.junit.Assert.fail(Assert.java:89)"]),
])


class Device:
    """A scripted adb + gradle + sign-in helper. `run` is what run_external_android calls."""

    def __init__(self, *, devices=("emulator-5554",), play_services=True, sign_in_code=0, sign_in_stdout=None,
                 instrument_stdout=PASSING, instrument_code=0, build_code=0, install_code=0):
        self.devices, self.play_services = list(devices), play_services
        self.sign_in_code = sign_in_code
        self.sign_in_stdout = sign_in_stdout if sign_in_stdout is not None else json.dumps(
            {"accessToken": TOKEN, "accountId": ACCOUNT})
        self.instrument_stdout, self.instrument_code = instrument_stdout, instrument_code
        self.build_code, self.install_code = build_code, install_code
        self.calls = []
        self.raise_on_instrument = False

    def __call__(self, command, *, capture=False):
        self.calls.append(list(command))
        text = " ".join(command)
        done = lambda code=0, stdout="": SimpleNamespace(returncode=code, stdout=stdout)  # noqa: E731
        if command[1:] == ["devices"]:
            rows = "".join(f"{d}\tdevice\n" for d in self.devices)
            return done(stdout="List of devices attached\n" + rows)
        if "pm list packages" in text:
            return done(stdout="package:com.google.android.gms\n" if self.play_services else "")
        if command[0] == "node":
            return done(self.sign_in_code, self.sign_in_stdout)
        if "assembleDebug" in text:
            return done(self.build_code)
        if " install " in f" {text} ":
            return done(self.install_code)
        if "am instrument" in text:
            if self.raise_on_instrument:
                raise KeyboardInterrupt
            return done(self.instrument_code, self.instrument_stdout)
        return done()

    def ran(self, fragment):
        return [c for c in self.calls if fragment in " ".join(c)]


def run_it(device, tmp_path, surfaces=(SURFACE,), tests_dir=rea.TESTS_DIR):
    results = tmp_path / "results.xml"
    lines = []
    code = rea.main(env={"EXTERNAL_SURFACES": ",".join(surfaces), "EXTERNAL_RESULTS_FILE": str(results)},
                    run=device, adb="adb", tests_dir=tests_dir, out=lines.append)
    return code, results, lines


# --- reading the tests' tags ---------------------------------------------------------------------


def test_surface_classes_reads_the_package_and_the_annotation_even_with_other_annotations_between(tmp_path):
    (tmp_path / "AExternalTest.kt").write_text(
        'package com.x\n\n@ExternalSurface("one-surface")\n@RunWith(AndroidJUnit4::class)\nclass A {}\n')
    (tmp_path / "BExternalTest.kt").write_text('package com.y\n@ExternalSurface("two")\nclass B\nclass C\n')
    (tmp_path / "Untagged.kt").write_text('package com.z\n@ExternalSurface("hidden")\nclass D\n')
    assert rea.surface_classes(tmp_path) == {"one-surface": ["com.x.A"], "two": ["com.y.B"]}


def test_the_real_external_test_class_is_tagged_for_its_manifest_surface():
    assert rea.surface_classes() == {SURFACE: [CLASS]}


def test_every_tagged_surface_is_an_active_android_owned_surface_in_the_manifest():
    surfaces = ef.load_manifest()["surfaces"]
    for name in rea.surface_classes():
        assert surfaces[name]["status"] == "active", name
        assert surfaces[name]["owner"] == "android", name


def test_the_wrappers_untagged_guard_looks_where_the_runner_does():
    has_tests = ew.tagged_in(rea.TESTS_DIR, rea.TEST_GLOB, ew.TAG_FORMATS["annotation"])
    assert has_tests(SURFACE) and not has_tests("google-play-billing")


def test_the_powershell_wrapper_passes_the_runners_directory_and_glob():
    text = (_ROOT / "android" / "test-external.ps1").read_text(encoding="utf-8")
    relative = rea.TESTS_DIR.relative_to(_ROOT / "android")
    assert str(relative) in text and f"'{rea.TEST_GLOB}'" in text
    assert "--tag-style annotation" in text and "--platform android" in text


def test_the_runner_uses_the_marker_path_and_instrumentation_the_test_app_declares():
    runner = (rea.TESTS_DIR / "CustomTestRunner.kt").read_text(encoding="utf-8")
    assert f'WEEKLY_MARKER_PATH = "{rea.MARKER_PATH}"' in runner
    # <test package>/<runner class>: the package is the app id plus ".test", the class is the one the file declares.
    declared = re.search(r"^class (\w+) : AndroidJUnitRunner", runner, re.MULTILINE).group(1)
    assert rea.INSTRUMENTATION == f"com.rigcheck.app.test/com.rigcheck.app.{declared}"
    gradle = (_ROOT / "android" / "app" / "build.gradle.kts").read_text(encoding="utf-8")
    assert f'applicationId = "{rea.INSTRUMENTATION.split(".test/")[0]}"' in gradle
    assert f'testInstrumentationRunner = "com.rigcheck.app.{declared}"' in gradle


def test_the_gradle_default_run_keeps_every_tagged_class_out_by_the_annotations_real_name():
    gradle = (_ROOT / "android" / "app" / "build.gradle.kts").read_text(encoding="utf-8")
    source = (rea.TESTS_DIR / "testsupport" / "ExternalSurface.kt").read_text(encoding="utf-8")
    package = re.search(r"^package\s+([\w.]+)", source, re.MULTILINE).group(1)
    name = re.search(r"annotation class (\w+)", source).group(1)
    assert f'["notAnnotation"] = "{package}.{name}"' in gradle


# --- reading `am instrument -r` ------------------------------------------------------------------


def test_parse_reads_passed_failed_and_skipped_tests_with_the_failures_stack():
    out = instrumentation_output([("a", 0, None), ("b", -2, ["java.lang.AssertionError: boom", "\tat x.y(Z.kt:1)"]),
                                  ("c", -3, None), ("d", -4, None), ("e", -1, ["java.lang.IllegalStateException: no"])])
    results, problem = rea.parse_instrumentation(out)
    assert problem is None
    assert [(r.name, r.outcome) for r in results] == [
        ("a", "passed"), ("b", "failed"), ("c", "skipped"), ("d", "skipped"), ("e", "failed")]
    assert results[1].detail.startswith("java.lang.AssertionError: boom\n\tat x.y(Z.kt:1)")
    assert all(r.class_name == CLASS for r in results)


def test_parse_counts_a_test_that_started_and_never_reported_as_failed():
    results, _ = rea.parse_instrumentation(instrumentation_output([("a", 0, None), ("died", None, None)]))
    assert [(r.name, r.outcome) for r in results] == [("a", "passed"), ("died", "failed")]


@pytest.mark.parametrize("line", [
    "INSTRUMENTATION_FAILED: com.rigcheck.app.test/com.rigcheck.app.CustomTestRunner",
    "INSTRUMENTATION_RESULT: shortMsg=Process crashed.",
])
def test_parse_reports_a_run_level_failure(line):
    _, problem = rea.parse_instrumentation(PASSING + line + "\r\n")
    assert problem


def test_parse_of_output_with_no_tests_is_empty():
    assert rea.parse_instrumentation("") == ([], None)
    assert rea.parse_instrumentation("INSTRUMENTATION_CODE: -1\r\n") == ([], None)


def test_the_junit_xml_gives_the_wrapper_each_tests_surface_and_outcome():
    results, _ = rea.parse_instrumentation(FAILING)
    xml = rea.junit_xml(results, {CLASS: SURFACE})
    counts = ew.surface_results(xml, [SURFACE, "google-play-billing"], ew.TAG_FORMATS["annotation"])
    assert counts == {SURFACE: ew.Counts(passed=1, failed=1)}


# --- the run -------------------------------------------------------------------------------------


def test_a_passing_run_builds_installs_marks_runs_the_tagged_class_and_cleans_up(tmp_path):
    device = Device()
    code, results, lines = run_it(device, tmp_path)
    assert code == 0
    names = [" ".join(c) for c in device.calls]
    order = [next(i for i, n in enumerate(names) if frag in n) for frag in
             ("assembleDebug", "app-debug.apk", "app-debug-androidTest.apk", f"echo {ACCOUNT}", "am instrument", "rm -f")]
    assert order == sorted(order)
    instrument = device.ran("am instrument")[0]
    assert instrument[instrument.index("-e") + 1:instrument.index("-e") + 3] == ["class", CLASS]
    assert "-s" in instrument and "emulator-5554" in instrument
    assert device.ran(f"echo {ACCOUNT} > {rea.MARKER_PATH}")
    assert device.ran("airplane-mode disable")
    counts = ew.surface_results(results.read_text(encoding="utf-8"), [SURFACE], ew.TAG_FORMATS["annotation"])
    assert counts == {SURFACE: ew.Counts(passed=2)}


def test_the_access_token_is_never_passed_to_the_device_or_printed(tmp_path):
    device = Device()
    _, _, lines = run_it(device, tmp_path)
    assert not [c for c in device.calls if TOKEN in " ".join(c)]
    assert not [line for line in lines if TOKEN in str(line)]


def test_a_failing_test_fails_the_run_and_the_surface_but_still_cleans_up(tmp_path):
    device = Device(instrument_stdout=FAILING)
    code, results, lines = run_it(device, tmp_path)
    assert code == 1
    counts = ew.surface_results(results.read_text(encoding="utf-8"), [SURFACE], ew.TAG_FORMATS["annotation"])
    assert counts == {SURFACE: ew.Counts(passed=1, failed=1)}
    assert device.ran(f"rm -f {rea.MARKER_PATH}")
    assert any("loginFails" in str(line) for line in lines) and any("no SCAN entry" in str(line) for line in lines)


def test_the_marker_is_removed_even_when_the_run_is_interrupted(tmp_path):
    device = Device()
    device.raise_on_instrument = True
    with pytest.raises(KeyboardInterrupt):
        run_it(device, tmp_path)
    assert device.ran(f"rm -f {rea.MARKER_PATH}") and device.ran("airplane-mode disable")


@pytest.mark.parametrize("device", [
    Device(instrument_stdout=""),
    Device(instrument_stdout=PASSING + "INSTRUMENTATION_RESULT: shortMsg=Process crashed.\r\n"),
    Device(instrument_code=1),
    Device(instrument_stdout=instrumentation_output([("died", None, None)])),
])
def test_a_run_that_ran_no_test_or_broke_is_a_failure_even_when_nothing_reported_failed(device, tmp_path):
    code, _, _ = run_it(device, tmp_path)
    assert code == 1


def test_no_device_fails_before_anything_is_built(tmp_path):
    device = Device(devices=())
    code, results, lines = run_it(device, tmp_path)
    assert code == 1 and any("No device or emulator" in str(line) for line in lines)
    assert not device.ran("assembleDebug") and not results.exists()


def test_more_than_one_device_fails_before_anything_is_built(tmp_path):
    device = Device(devices=("emulator-5554", "emulator-5556"))
    code, _, lines = run_it(device, tmp_path)
    assert code == 1 and any("More than one device" in str(line) for line in lines)
    assert not device.ran("assembleDebug")


def test_a_device_without_play_services_fails_naming_it_before_anything_is_built(tmp_path):
    device = Device(play_services=False)
    code, _, lines = run_it(device, tmp_path)
    assert code == 1 and any("Google Play Services" in str(line) for line in lines)
    assert not device.ran("assembleDebug") and not device.ran("node")


@pytest.mark.parametrize("device", [
    Device(sign_in_code=1, sign_in_stdout=""),
    Device(sign_in_stdout="not json"),
    Device(sign_in_stdout=json.dumps({"accessToken": TOKEN})),
    Device(sign_in_stdout=json.dumps({"accountId": "x; rm -rf /data", "accessToken": TOKEN})),
])
def test_an_account_that_cannot_sign_in_or_returns_no_usable_id_fails_before_anything_is_built(device, tmp_path):
    code, _, _ = run_it(device, tmp_path)
    assert code == 1
    assert not device.ran("assembleDebug") and not device.ran("am instrument")


@pytest.mark.parametrize("device, fragment", [
    (Device(build_code=1), "am instrument"),
    (Device(install_code=1), "am instrument"),
])
def test_a_failed_build_or_install_fails_the_run_without_running_tests(device, fragment, tmp_path):
    code, _, _ = run_it(device, tmp_path)
    assert code == 1 and not device.ran(fragment)


def test_a_surface_with_no_tagged_class_fails_the_run(tmp_path):
    device = Device()
    code, _, lines = run_it(device, tmp_path, surfaces=("google-play-billing",))
    assert code == 1 and any("google-play-billing" in str(line) for line in lines)
    assert not device.calls


def test_only_the_classes_of_the_requested_surfaces_run(tmp_path):
    (tmp_path / "AExternalTest.kt").write_text('package p\n@ExternalSurface("one")\nclass A\n')
    (tmp_path / "BExternalTest.kt").write_text('package p\n@ExternalSurface("two")\nclass B\n')
    device = Device(instrument_stdout=PASSING)
    run_it(device, tmp_path, surfaces=("two",), tests_dir=tmp_path)
    instrument = device.ran("am instrument")[0]
    assert instrument[instrument.index("class") + 1] == "p.B"
