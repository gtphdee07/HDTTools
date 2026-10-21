"""Function tests for scripts/android_suite_loop.py (#127): how one finished
instrumented run is labelled (passed, a real test failure, or an
infrastructure abort), and that the repeat loop restarts the emulator before
every run, counts each outcome, and tells a dead emulator from a failing test.
All fakes - no emulator, adb or Gradle is touched."""

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.minor]

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
spec = importlib.util.spec_from_file_location("android_suite_loop", _SCRIPTS / "android_suite_loop.py")
asl = importlib.util.module_from_spec(spec)
sys.modules["android_suite_loop"] = asl
spec.loader.exec_module(asl)

OK_OUTPUT = "INSTRUMENTATION_STATUS: ...\n\nTime: 512.3\n\nOK (97 tests)\n\n"
FAIL_OUTPUT = (
    "There was 1 failure:\n1) someTest(com.rigcheck.app.SomeTest)\njava.lang.AssertionError: x\n\n"
    "FAILURES!!!\nTests run: 97,  Failures: 1\n"
)


@pytest.mark.parametrize(
    "marker",
    [
        "INSTRUMENTATION_ABORTED: System has crashed.",
        "Process crashed. System has crashed",
        "Can't find service: input",
        "error: device offline",
        "error: device 'emulator-5554' not found",
        "error: no devices/emulators found",
        "android.app.ShellCommandUnresponsiveException",
        "ReferenceQueueDaemon timed out",
        "INSTRUMENTATION_FAILED: com.rigcheck.app.test/com.rigcheck.app.CustomTestRunner",
    ],
)
def test_each_known_emulator_death_is_an_infrastructure_abort(marker):
    outcome = asl.classify_run(f"some progress\n{marker}\n", returncode=1)
    assert outcome.kind == asl.INFRA_ABORT
    assert outcome.reason  # the summary quotes it, so it can't be blank


def test_an_ok_summary_is_a_pass_and_carries_the_test_count():
    outcome = asl.classify_run(OK_OUTPUT, returncode=0)
    assert outcome.kind == asl.PASSED
    assert outcome.tests == 97


def test_a_finished_run_with_failures_is_a_test_failure_not_an_abort():
    outcome = asl.classify_run(FAIL_OUTPUT, returncode=0)
    assert outcome.kind == asl.TEST_FAILED
    assert outcome.tests == 97


def test_a_test_failure_that_is_followed_by_a_system_crash_is_an_abort():
    # The mid-suite hang in #127: a test fails with "Activity never becomes
    # requested state DESTROYED", then the system server dies. The failure is
    # a symptom, so the run must not count against the app's tests.
    output = (
        "java.lang.AssertionError: Activity never becomes requested state DESTROYED\n"
        "INSTRUMENTATION_ABORTED: System has crashed.\n" + FAIL_OUTPUT
    )
    assert asl.classify_run(output, returncode=1).kind == asl.INFRA_ABORT


def test_output_with_no_result_line_at_all_is_an_abort():
    assert asl.classify_run("", returncode=0).kind == asl.INFRA_ABORT
    assert asl.classify_run("INSTRUMENTATION_STATUS: class=x\n", returncode=0).kind == asl.INFRA_ABORT


def test_an_ok_summary_with_a_nonzero_exit_is_not_a_pass():
    # am instrument's own exit code ignores JUnit failures (test-weekly.ps1's
    # comment), but a non-zero exit with an OK line is not something to trust.
    assert asl.classify_run(OK_OUTPUT, returncode=1).kind != asl.PASSED


def test_an_ok_run_with_too_few_tests_is_not_a_pass():
    # A filter or a dropped class would shrink the count; a documented full
    # run says how many tests it expects.
    outcome = asl.classify_run(OK_OUTPUT, returncode=0, expected_tests=120)
    assert outcome.kind == asl.TEST_FAILED
    assert "97" in outcome.reason and "120" in outcome.reason


def test_the_expected_count_is_met_exactly_for_a_pass():
    assert asl.classify_run(OK_OUTPUT, returncode=0, expected_tests=97).kind == asl.PASSED


class Script:
    """Fake emulator + runner: records the order of restarts and runs, and
    answers each run from a list."""

    def __init__(self, outputs, restart_results=None):
        self.events = []
        self.numbers = []
        self.outputs = list(outputs)
        self.restart_results = list(restart_results or [])

    def restart(self):
        self.events.append("restart")
        return self.restart_results.pop(0) if self.restart_results else True

    def run_once(self, number):
        self.events.append("run")
        self.numbers.append(number)
        output, code = self.outputs.pop(0)
        return output, code


def run_loop(script, n):
    return asl.run_loop(n, restart=script.restart, run_once=script.run_once, out=lambda _: None)


def test_the_emulator_is_restarted_before_every_run():
    script = Script([(OK_OUTPUT, 0)] * 3)
    report = run_loop(script, 3)
    assert script.events == ["restart", "run"] * 3
    assert report.passed == 3 and report.runs == 3


def test_restart_every_k_reuses_the_emulator_between_restarts():
    # For measuring how many back-to-back suites a warm emulator survives
    # (the mid-suite hang in #127 came after 2-3 runs without a restart).
    script = Script([(OK_OUTPUT, 0)] * 5)
    asl.run_loop(5, restart=script.restart, run_once=script.run_once, restart_every=2, out=lambda _: None)
    assert script.events == ["restart", "run", "run", "restart", "run", "run", "restart", "run"]


def test_an_abort_forces_a_restart_before_the_next_run_even_when_reusing():
    # A dead emulator can't run the next suite, so reuse never outlives an abort.
    abort = ("INSTRUMENTATION_ABORTED: System has crashed.", 1)
    script = Script([abort, (OK_OUTPUT, 0), (OK_OUTPUT, 0)])
    asl.run_loop(3, restart=script.restart, run_once=script.run_once, restart_every=0, out=lambda _: None)
    assert script.events == ["restart", "run", "restart", "run", "run"]


def test_counts_separate_passes_failures_and_aborts():
    script = Script(
        [
            (OK_OUTPUT, 0),
            (FAIL_OUTPUT, 0),
            ("INSTRUMENTATION_ABORTED: System has crashed.", 1),
            (OK_OUTPUT, 0),
        ]
    )
    report = run_loop(script, 4)
    assert (report.passed, report.test_failed, report.infra_aborted) == (2, 1, 1)
    assert report.finished == 3  # passes plus real failures reached the end of the suite


def test_a_restart_that_never_boots_counts_as_an_abort_and_no_tests_run():
    script = Script([(OK_OUTPUT, 0)], restart_results=[False, True])
    report = run_loop(script, 2)
    assert script.events == ["restart", "restart", "run"]
    assert report.infra_aborted == 1 and report.passed == 1


def test_a_run_is_numbered_by_the_loop_so_its_log_matches_the_summary():
    # Run 1 never booted, so the first suite that ran is run 2: its run-2.log
    # must be the one the summary's "run 2" line points at.
    script = Script([(OK_OUTPUT, 0)], restart_results=[False, True])
    run_loop(script, 2)
    assert script.numbers == [2]


def test_an_install_failure_is_an_abort_that_says_so():
    outcome = asl.classify_run("install of app-debug.apk failed:\nadb: failed to install: INSTALL_FAILED_X\n", 1)
    assert outcome.kind == asl.INFRA_ABORT
    assert "install of app-debug.apk failed" in outcome.reason


def test_gradle_output_is_read_by_the_same_rules():
    # Texts copied from real `connectedDebugAndroidTest` runs on 2026-10-19.
    passed = "Starting 132 tests on medium_phone(AVD) - 16\nFinished 132 tests on medium_phone(AVD) - 16\nBUILD SUCCESSFUL in 5m 22s\n"
    assert asl.classify_run(passed, returncode=0).tests == 132
    assert asl.classify_run(passed, returncode=0).kind == asl.PASSED
    dropped = (
        "com.android.ddmlib.AdbCommandRejectedException: device offline\n"
        "Test run failed to complete. Expected 132 tests, received 13\nBUILD FAILED in 56s\n"
    )
    outcome = asl.classify_run(dropped, returncode=1)
    assert outcome.kind == asl.INFRA_ABORT
    failing = "ChipTest > someTest[medium_phone(AVD) - 16] FAILED\nThere were failing tests. See the report\nBUILD FAILED\n"
    assert asl.classify_run(failing, returncode=1).kind == asl.TEST_FAILED


def test_the_longest_streak_of_passes_is_reported():
    kinds = [(OK_OUTPUT, 0), (OK_OUTPUT, 0), (FAIL_OUTPUT, 0), (OK_OUTPUT, 0), (OK_OUTPUT, 0), (OK_OUTPUT, 0)]
    report = run_loop(Script(kinds), 6)
    assert report.longest_pass_streak == 3


def test_a_dead_run_does_not_break_a_streak_of_passes_it_is_not_counted_in():
    # An infra abort says nothing about the app: it is reported, not treated
    # as a failed run in the streak (the ticket's 5 passes need a clean count
    # of finished runs, and the abort total shows what was thrown away).
    script = Script([(OK_OUTPUT, 0), ("INSTRUMENTATION_ABORTED: System has crashed.", 1), (OK_OUTPUT, 0)])
    report = run_loop(script, 3)
    assert report.longest_pass_streak == 2
    assert report.infra_aborted == 1


def test_exit_code_is_zero_only_when_every_run_passed():
    assert run_loop(Script([(OK_OUTPUT, 0)] * 2), 2).exit_code == 0
    assert run_loop(Script([(OK_OUTPUT, 0), (FAIL_OUTPUT, 0)]), 2).exit_code == 1
    abort = ("INSTRUMENTATION_ABORTED: System has crashed.", 1)
    assert run_loop(Script([(OK_OUTPUT, 0), abort]), 2).exit_code == 2
    # a real failure outranks an abort: the owner must look at the failure first
    assert run_loop(Script([abort, (FAIL_OUTPUT, 0)]), 2).exit_code == 1


def test_the_summary_names_each_count_and_the_abort_reasons():
    lines = []
    script = Script([(OK_OUTPUT, 0), ("error: device offline", 1)])
    report = asl.run_loop(2, restart=script.restart, run_once=script.run_once, out=lines.append)
    text = "\n".join(lines)
    assert "1 of 2 runs passed" in text
    assert "1 aborted for infrastructure reasons" in text
    assert "device offline" in text
    assert report.summary().count("\n") >= 2


def test_the_emulator_is_cold_booted_on_the_software_gpu_by_default():
    # #127: on the host-GPU backend the system server hangs in a screen capture
    # (watchdog kill) and adb drops; on swangle_indirect every run finished.
    command = asl.emulator_command("emu.exe", avd="medium_phone")
    assert command[:3] == ["emu.exe", "-avd", "medium_phone"]
    assert "-no-snapshot" in command
    assert command[command.index("-gpu") + 1] == "swangle_indirect"


def test_the_gpu_mode_and_extra_flags_can_be_overridden_for_comparison_runs():
    command = asl.emulator_command("emu.exe", avd="a", gpu="host", extra_args=["-memory", "4096"])
    assert command[command.index("-gpu") + 1] == "host"
    assert command[-2:] == ["-memory", "4096"]


class FakeAdb:
    """Fake adb: `adb(*args)` returns (exit code, stdout). An answer that is
    callable is called with how many times that same command has run."""

    def __init__(self, answers):
        self.answers = answers
        self.calls = []

    def __call__(self, *args):
        self.calls.append(args)
        answer = self.answers.get(args, (0, ""))
        return answer(self.calls.count(args)) if callable(answer) else answer


READY = {
    ("get-state",): (0, "device\n"),
    ("shell", "getprop", "sys.boot_completed"): (0, "1\n"),
    ("shell", "service", "check", "input"): (0, "Service input: found\n"),
    ("shell", "service", "check", "activity"): (0, "Service activity: found\n"),
    ("shell", "service", "check", "package"): (0, "Service package: found\n"),
    ("shell", "service", "check", "window"): (0, "Service window: found\n"),
}


def test_a_device_is_ready_only_when_booted_and_every_service_answers():
    assert asl.not_ready_reason(FakeAdb(READY)) is None
    for key, bad, expect in [
        (("get-state",), (1, "error: device offline\n"), "offline"),
        (("shell", "getprop", "sys.boot_completed"), (0, "\n"), "boot"),
        (("shell", "service", "check", "input"), (0, "Service input: not found\n"), "input"),
        (("shell", "service", "check", "activity"), (1, "Can't find service: activity\n"), "activity"),
    ]:
        reason = asl.not_ready_reason(FakeAdb({**READY, key: bad}))
        assert reason is not None and expect in reason


def test_readiness_needs_several_good_polls_in_a_row_not_one_lucky_one():
    # "device offline" 22 s after boot (#127): the first poll after boot can
    # look fine and the transport then drops. A bad poll restarts the streak.
    def flaky(n):
        return (1, "error: device offline\n") if n == 2 else (0, "device\n")

    adb = FakeAdb({**READY, ("get-state",): flaky})
    ok = asl.wait_until_ready(adb, consecutive=3, timeout_s=600, poll_s=2, sleep=lambda _: None, now=lambda: 0)
    assert ok is True
    # good, bad, then three good in a row: five polls in all.
    assert adb.calls.count(("get-state",)) == 5


def test_readiness_gives_up_at_the_timeout():
    clock = iter(range(0, 10000, 100))
    adb = FakeAdb({**READY, ("get-state",): (1, "error: device offline\n")})
    ok = asl.wait_until_ready(adb, consecutive=3, timeout_s=300, poll_s=1, sleep=lambda _: None, now=lambda: next(clock))
    assert ok is False


def run_instrument(tests_dir=None):
    """Runs instrument_once against a fake adb; returns the calls it made."""
    calls = []

    def adb(*args, timeout=None):
        calls.append(args)
        return (0, "Success\n") if args[0] == "install" else (0, "OK (132 tests)\n")

    kwargs = {} if tests_dir is None else {"tests_dir": tests_dir}
    text, code = asl.instrument_once(adb, suite_timeout_s=60, **kwargs)
    assert (code, text) == (0, "OK (132 tests)\n")
    return calls


def excluded_by(calls):
    (instrument,) = [c for c in calls if c[:3] == ("shell", "am", "instrument")]
    assert instrument[instrument.index("-e") + 1] == "notClass"
    return instrument[instrument.index("-e") + 2].split(",")


def test_the_suite_command_leaves_out_the_weekly_class_and_clears_its_marker():
    # The Gradle task excludes PaywallScreenWeeklyTest (it needs the network and a funded test user);
    # a raw `am instrument` runs it unless told not to, and would label its failure a real test failure.
    calls = run_instrument()
    assert asl.WEEKLY_CLASS in excluded_by(calls)
    instrument = next(c for c in calls if c[:3] == ("shell", "am", "instrument"))
    assert ("shell", "rm", "-f", asl.WEEKLY_MARKER) in calls
    assert calls.index(("shell", "rm", "-f", asl.WEEKLY_MARKER)) < calls.index(instrument)


def test_the_suite_command_leaves_out_the_external_surface_class_of_the_real_tree():
    # #153: Gradle keeps @ExternalSurface classes out (notAnnotation); the raw run did not, so
    # RevenueCatAndroidSdkExternalTest's 6 live tests ran, failed, and no run was ever green.
    assert "com.rigcheck.app.RevenueCatAndroidSdkExternalTest" in excluded_by(run_instrument())


def test_every_tagged_class_is_left_out_without_a_hand_kept_list(tmp_path):
    # A class tagged tomorrow must be excluded with no edit to the script: the set comes from the
    # same discovery run_external_android.py uses (class-level @ExternalSurface in *ExternalTest.kt).
    (tmp_path / "AlphaExternalTest.kt").write_text(
        'package com.example.one\n\n@ExternalSurface("alpha")\nclass AlphaExternalTest {\n}\n', encoding="utf-8"
    )
    (tmp_path / "BetaExternalTest.kt").write_text(
        'package com.example.two\n\n@ExternalSurface("beta")\n@RunWith(AndroidJUnit4::class)\nclass BetaExternalTest {\n}\n',
        encoding="utf-8",
    )
    (tmp_path / "PlainTest.kt").write_text("package com.example.three\n\nclass PlainTest {\n}\n", encoding="utf-8")

    excluded = excluded_by(run_instrument(tmp_path))

    assert set(excluded) == {asl.WEEKLY_CLASS, "com.example.one.AlphaExternalTest", "com.example.two.BetaExternalTest"}
