"""Function tests for scripts/run_supervisor.py (#200): the status file a supervised command leaves, the
`am instrument -r` reader, each stall rule (output, one test, the device), the evidence step, the stop
decision (flag and stop, or flag only), the exit code and label of a hung run, the suite caps, and the
retry-once rule for a device run. Fakes only: a clock that moves when something waits, a scripted
process and a scripted adb - no emulator, adb, process or real wait is touched."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from tests._supervisor_fakes import (
    NO_DEVICE, FakeAdb, FakeClock, FakeProc, healthy_adb, record, timeout_error,
)

pytestmark = [pytest.mark.core, pytest.mark.minor]

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))
spec = importlib.util.spec_from_file_location("run_supervisor", _SCRIPTS / "run_supervisor.py")
rs = importlib.util.module_from_spec(spec)
sys.modules["run_supervisor"] = rs
spec.loader.exec_module(rs)
import run_status  # noqa: E402

CLS = "com.rigcheck.app.ui.FooTest"
INSTALL = b"Installing APK 'app-debug.apk' on 'medium_phone(AVD)'\n"


def ok(cls, test, current, total=3):
    return record(1, cls, test, current, total) + record(0, cls, test, current, total)


def run(tmp_path, proc_factory, *, device=False, adb=None, limits=None, on_stall="stop", phase=None, echo=None):
    clock = FakeClock()
    proc = proc_factory(clock)
    writer = run_status.StatusWriter("r1", "fake command", tmp_path, now=clock.wall, sleep=lambda _: None)
    result = rs.supervise(
        ["fake"], writer=writer, spawn=lambda argv: proc, clock=clock, limits=limits or rs.Limits(), device=device, adb=adb,
        tool=lambda argv, timeout: (0, b"tasklist"), on_stall=on_stall, phase=phase, echo=echo,
    )
    return result, proc, lines(tmp_path)


def lines(tmp_path):
    return [json.loads(ln) for ln in (tmp_path / "r1.jsonl").read_text(encoding="utf-8").splitlines()]


def progress(entries):
    return [(e["phase"], e["test"], e["n"], e["of"]) for e in entries]


# --- the status file ---------------------------------------------------------------------------


def test_the_phase_moves_boot_install_test_done_and_n_rises_to_of(tmp_path):
    def factory(clock):
        script = [(1, INSTALL), (5, ok(CLS, "a", 1)), (8, ok(CLS, "b", 2)), (11, ok(CLS, "c", 3))]
        return FakeProc(clock, script, exit_at=12)

    result, _, entries = run(tmp_path, factory, device=True, adb=healthy_adb())
    phases = [e["phase"] for e in entries]
    assert [p for i, p in enumerate(phases) if i == 0 or p != phases[i - 1]] == ["boot", "install", "test", "done"]
    assert [e["n"] for e in entries if e["phase"] == "test"][-1] == 3 and entries[-1]["of"] == 3
    ns = [e["n"] for e in entries if e["n"] is not None]
    assert ns == sorted(ns)
    assert entries[-1]["phase"] == "done" and entries[-1]["outcome"] == "passed"
    assert result.exit_code == 0 and result.outcome == rs.PASSED


def test_every_line_has_the_documented_fields(tmp_path):
    _, _, entries = run(tmp_path, lambda c: FakeProc(c, [(1, b"hello\n")], exit_at=2))
    for entry in entries:
        assert {"t", "run_id", "phase", "command", "test", "n", "of", "last_output_age_s", "device"} <= set(entry)
        assert entry["run_id"] == "r1" and entry["command"] == "fake command" and entry["device"] == "none"


def test_latest_json_holds_the_newest_line(tmp_path):
    _, _, entries = run(tmp_path, lambda c: FakeProc(c, [(1, b"x\n")], exit_at=2))
    latest = json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))
    assert latest == entries[-1] and latest["phase"] == "done"


def test_a_command_without_a_device_starts_in_the_test_phase(tmp_path):
    _, _, entries = run(tmp_path, lambda c: FakeProc(c, [(1, b"x\n")], exit_at=2))
    assert entries[0]["phase"] == "test"


# --- reading am instrument -r --------------------------------------------------------------------


def feed(text: bytes):
    parser = rs.Progress()
    events = []
    for line in text.decode().split("\n"):
        events.extend(parser.feed(line))
    return parser, [(e.kind, e.test, e.code, e.of) for e in events]


def test_a_passing_run_gives_a_start_and_a_finish_per_test_with_n_and_of():
    parser, events = feed(ok(CLS, "a", 1, 2) + ok(CLS, "b", 2, 2))
    assert events == [
        ("of", None, None, 2), ("test_started", f"{CLS}.a", None, None), ("test_finished", f"{CLS}.a", 0, None),
        ("test_started", f"{CLS}.b", None, None), ("test_finished", f"{CLS}.b", 0, None),
    ]
    assert (parser.n, parser.of, parser.failures) == (2, 2, 0)


def test_a_failing_test_is_counted_and_its_stack_trace_does_not_break_the_next_record():
    text = record(1, CLS, "a", 1, 2) + record(-2, CLS, "a", 1, 2, stack="java.lang.AssertionError: x\n\tat Foo.bar(Foo.kt:1)") + ok(CLS, "b", 2, 2)
    parser, events = feed(text)
    assert [e for e in events if e[0] == "test_finished"] == [("test_finished", f"{CLS}.a", -2, None), ("test_finished", f"{CLS}.b", 0, None)]
    assert (parser.n, parser.failures) == (2, 1)


def test_a_truncated_run_leaves_the_last_test_running():
    parser, events = feed(ok(CLS, "a", 1, 3) + record(1, CLS, "b", 2, 3)[:-40])  # cut inside the next record
    assert events[-1] == ("test_finished", f"{CLS}.a", 0, None)
    assert parser.n == 1
    parser, events = feed(ok(CLS, "a", 1, 3) + record(1, CLS, "b", 2, 3))
    assert events[-1][:2] == ("test_started", f"{CLS}.b") and parser.n == 1


def test_the_runners_own_status_block_without_a_test_is_not_a_test():
    block = b"INSTRUMENTATION_STATUS: id=AndroidJUnitRunner\nINSTRUMENTATION_STATUS: numtests=5\nINSTRUMENTATION_STATUS_CODE: 1\n"
    parser, events = feed(block)
    assert [e[0] for e in events] == ["of"] and parser.n == 0 and parser.of == 5


def test_each_written_line_names_the_running_test_and_the_counts(tmp_path):
    script = [(1, record(1, CLS, "a", 1, 2)), (3, record(0, CLS, "a", 1, 2)), (4, record(1, CLS, "b", 2, 2)), (6, record(0, CLS, "b", 2, 2))]
    _, _, entries = run(tmp_path, lambda c: FakeProc(c, script, exit_at=7))
    rows = progress(entries)
    assert (("test", f"{CLS}.a", 0, 2)) in rows  # a is running, none finished
    assert (("test", None, 1, 2)) in rows  # a finished
    assert (("test", f"{CLS}.b", 1, 2)) in rows
    assert rows[-1] == ("done", None, 2, 2)


def test_a_gradle_count_line_sets_of():
    parser, events = feed(b"Starting 36 tests on medium_phone(AVD) - 14\n")
    assert parser.of == 36 and events[0][0] == "of"


# --- stall rules -------------------------------------------------------------------------------


def test_no_output_for_longer_than_the_limit_is_hung_with_the_evidence_saved(tmp_path):
    result, proc, entries = run(tmp_path, lambda c: FakeProc(c, [(1, b"starting\n")], exit_at=None))
    assert result.phase == "hung" and result.reason == "no output"
    assert entries[-1]["phase"] == "hung" and entries[-1]["reason"] == "no output"
    assert result.exit_code == rs.HUNG_EXIT_CODE and proc.killed
    saved = {p.name for p in (tmp_path / "r1").iterdir()}
    assert {"output-tail.txt", "processes.txt", "evidence.json"} <= saved
    assert "starting" in (tmp_path / "r1" / "output-tail.txt").read_text(encoding="utf-8")


def test_output_just_inside_the_limit_is_not_a_stall(tmp_path):
    result, _, _ = run(tmp_path, lambda c: FakeProc(c, [(100, b"late\n")], exit_at=200), limits=rs.Limits(output_s=120))
    assert result.phase == "done"


def test_one_test_running_longer_than_the_test_limit_is_hung_and_names_it(tmp_path):
    script = [(1, ok(CLS, "a", 1)), (2, record(1, CLS, "stuck", 2))]
    result, _, entries = run(tmp_path, lambda c: FakeProc(c, script), limits=rs.Limits(output_s=600, test_s=90))
    assert result.reason == "test too long"
    assert entries[-1]["phase"] == "hung" and entries[-1]["test"] == f"{CLS}.stuck" and entries[-1]["reason"] == "test too long"
    assert f"{CLS}.stuck" in entries[-1]["detail"]


def test_a_test_that_keeps_finishing_is_never_too_long(tmp_path):
    script = []
    for i in range(1, 11):
        script += [(i * 60 - 59, record(1, CLS, f"t{i}", i, 10)), (i * 60, record(0, CLS, f"t{i}", i, 10))]
    result, _, _ = run(tmp_path, lambda c: FakeProc(c, script, exit_at=650), limits=rs.Limits(output_s=120, test_s=90))
    assert result.phase == "done"


def test_a_run_over_its_wall_cap_is_hung_even_while_it_prints(tmp_path):
    script = [(t, b"tick\n") for t in range(5, 400, 5)]
    result, _, _ = run(tmp_path, lambda c: FakeProc(c, script), limits=rs.Limits(output_s=120, wall_s=100))
    assert result.reason == "wall cap"


def device_phase_proc(clock, until=400):
    return FakeProc(clock, [(1, INSTALL), (2, record(1, CLS, "a", 1))] + [(t, b".\n") for t in range(30, until, 30)], exit_at=until + 5)


def test_a_device_that_stops_answering_getprop_three_checks_in_a_row_is_hung(tmp_path):
    adb = healthy_adb(lambda args: timeout_error() if args[:2] == ["shell", "getprop"] else None)
    result, _, entries = run(tmp_path, device_phase_proc, device=True, adb=adb, limits=rs.Limits(output_s=600, test_s=600))
    assert result.reason == "device not responding"
    assert entries[-1]["phase"] == "hung"
    assert len(adb.called("shell", "getprop", "sys.boot_completed")) >= 3
    checks = [t for args, t in adb.calls if args == ["devices"] or args[:2] == ["shell", "getprop"]]
    assert checks and all(timeout == rs.DEVICE_CALL_TIMEOUT_S == 5 for timeout in checks)


def test_a_device_missing_from_adb_devices_three_checks_in_a_row_is_hung(tmp_path):
    adb = FakeAdb(lambda args: (0, NO_DEVICE) if args == ["devices"] else (0, b"1\n"))
    result, _, _ = run(tmp_path, device_phase_proc, device=True, adb=adb, limits=rs.Limits(output_s=600, test_s=600))
    assert result.reason == "device offline"


def test_a_single_missed_device_check_is_not_a_stall(tmp_path):
    answers = iter([False, True, True, False, True, True] + [True] * 100)
    adb = healthy_adb(lambda args: (timeout_error() if not next(answers) else None) if args[:2] == ["shell", "getprop"] else None)
    result, _, entries = run(tmp_path, device_phase_proc, device=True, adb=adb, limits=rs.Limits(output_s=600, test_s=600))
    assert result.phase == "done"
    assert "slow" in {e["device"] for e in entries} and entries[-1]["device"] == "ok"


def test_a_device_still_booting_cannot_make_a_stall(tmp_path):
    adb = FakeAdb(lambda args: (0, NO_DEVICE) if args == ["devices"] else (1, b""))
    result, _, entries = run(
        tmp_path, lambda c: FakeProc(c, [(t, b"booting\n") for t in range(10, 100, 10)], exit_at=100), device=True, adb=adb,
    )
    assert result.phase == "done" and {e["phase"] for e in entries} == {"boot", "done"}


# --- evidence ----------------------------------------------------------------------------------


def test_the_evidence_of_a_device_run_has_every_item(tmp_path):
    def answer(args):
        if args[:2] == ["shell", "dumpsys"]:
            return 0, b"\n".join(b"window %d" % i for i in range(500))
        return None

    adb = healthy_adb(answer)
    manifest = rs.collect_evidence(tmp_path / "ev", output_tail=["a", "b"], device=True, adb=adb, tool=lambda argv, timeout: (0, b"ps"))
    assert set(manifest) == {"output-tail", "process-list", "logcat", "screencap", "window", "devices"}
    assert set(manifest.values()) == {"saved"}
    assert {p.name for p in (tmp_path / "ev").iterdir()} == {
        "output-tail.txt", "processes.txt", "logcat.txt", "screencap.png", "window.txt", "devices.txt", "evidence.json",
    }
    assert len((tmp_path / "ev" / "window.txt").read_bytes().splitlines()) == rs.WINDOW_HEAD_LINES
    assert adb.called("logcat", "-d", "-t", str(rs.LOGCAT_LINES)) and adb.called("devices", "-l")


def test_a_command_without_a_device_saves_only_the_output_and_the_process_list(tmp_path):
    adb = healthy_adb()
    manifest = rs.collect_evidence(tmp_path / "ev", output_tail=["a"], device=False, adb=adb, tool=lambda argv, timeout: (0, b"ps"))
    assert set(manifest) == {"output-tail", "process-list"} and adb.calls == []


def test_the_output_saved_is_the_last_200_lines(tmp_path):
    rs.collect_evidence(tmp_path / "ev", output_tail=[f"line {i}" for i in range(500)], device=False, adb=None, tool=lambda a, t: (0, b""))
    saved = (tmp_path / "ev" / "output-tail.txt").read_text(encoding="utf-8").splitlines()
    assert saved[0] == "line 300" and saved[-1] == "line 499"


def test_the_evidence_finishes_when_every_adb_call_times_out_and_the_run_still_ends_hung(tmp_path):
    seen = []

    def answer(args):
        seen.append(args)
        return timeout_error()

    adb = FakeAdb(answer)
    result, proc, entries = run(tmp_path, device_phase_proc, device=True, adb=adb, limits=rs.Limits(output_s=600, test_s=600))
    assert result.phase == "hung" and entries[-1]["phase"] == "hung" and proc.killed
    manifest = json.loads((tmp_path / "r1" / "evidence.json").read_text(encoding="utf-8"))
    assert manifest["output-tail"] == "saved"
    assert all(manifest[k].startswith("failed") for k in ("logcat", "screencap", "window", "devices"))
    assert all(timeout == rs.EVIDENCE_CALL_TIMEOUT_S for args, timeout in adb.calls if args[0] in ("logcat", "exec-out"))


def test_an_unwritable_evidence_item_is_a_failure_in_the_manifest_not_an_exception(tmp_path):
    blocker = tmp_path / "ev"
    blocker.mkdir()
    (blocker / "logcat.txt").mkdir()  # a directory where the file should go
    manifest = rs.collect_evidence(blocker, output_tail=[], device=True, adb=healthy_adb(), tool=lambda a, t: (0, b""))
    assert manifest["logcat"].startswith("failed") and manifest["devices"] == "saved"


# --- what happens to the run on a stall --------------------------------------------------------


def test_flag_and_stop_kills_the_process_and_the_emulator(tmp_path):
    adb = healthy_adb(lambda args: timeout_error() if args[:2] == ["shell", "getprop"] else None)
    result, proc, _ = run(tmp_path, device_phase_proc, device=True, adb=adb, limits=rs.Limits(output_s=600, test_s=600))
    assert proc.killed and adb.called("emu", "kill") and result.exit_code == rs.HUNG_EXIT_CODE


def test_flag_only_leaves_the_process_alive_and_still_exits_hung(tmp_path):
    adb = healthy_adb(lambda args: timeout_error() if args[:2] == ["shell", "getprop"] else None)

    def factory(clock):
        return FakeProc(clock, [(1, INSTALL), (2, record(1, CLS, "a", 1))] + [(t, b".\n") for t in range(30, 300, 30)], exit_at=300)

    result, proc, entries = run(tmp_path, factory, device=True, adb=adb, on_stall="flag", limits=rs.Limits(output_s=600, test_s=600))
    assert not proc.killed and not adb.called("emu", "kill")
    assert result.phase == "hung" and result.exit_code == rs.HUNG_EXIT_CODE
    assert proc.ended  # the wrapper kept draining the output until the process finished
    assert entries[-1]["phase"] == "hung" and [e["phase"] for e in entries].count("hung") >= 2


def test_an_unknown_stall_action_is_refused(tmp_path):
    with pytest.raises(ValueError):
        run(tmp_path, lambda c: FakeProc(c), on_stall="ignore")


# --- how a finished run is labelled --------------------------------------------------------------


def test_a_hung_run_exits_with_the_hung_code_and_is_an_infra_abort_never_a_test_failure(tmp_path):
    result, _, entries = run(tmp_path, lambda c: FakeProc(c, [(1, b"x\n")]))
    assert result.exit_code == rs.HUNG_EXIT_CODE == 124
    assert result.outcome == rs.INFRA_ABORT != rs.TEST_FAILED and entries[-1]["outcome"] == "infra-abort"
    assert "run hung" in result.output  # the suite loop's classifier reads this


def test_a_nonzero_exit_is_a_failure_and_zero_is_a_pass(tmp_path):
    failed, _, entries = run(tmp_path, lambda c: FakeProc(c, [(1, b"x\n")], exit_at=2, code=3))
    assert (failed.exit_code, failed.outcome, failed.phase) == (3, rs.TEST_FAILED, "failed") and entries[-1]["exit_code"] == 3


def test_a_device_command_that_prints_a_device_death_is_an_infra_abort(tmp_path):
    result, _, _ = run(tmp_path, lambda c: FakeProc(c, [(1, b"error: device offline\n")], exit_at=2, code=1), device=True, adb=healthy_adb())
    assert result.outcome == rs.INFRA_ABORT and result.exit_code == 1 and "device offline" in result.reason


def test_failures_in_an_instrument_run_that_exits_zero_are_a_test_failure(tmp_path):
    script = [(1, record(1, CLS, "a", 1, 1)), (2, record(-2, CLS, "a", 1, 1))]
    result, _, _ = run(tmp_path, lambda c: FakeProc(c, script, exit_at=3, code=0))
    assert result.outcome == rs.TEST_FAILED and result.exit_code == 1


def test_a_character_split_across_two_reads_stays_whole_in_the_saved_output(tmp_path):
    word = "température".encode()
    split = word.index("é".encode()) + 1  # between the two bytes of é
    result, _, _ = run(tmp_path, lambda c: FakeProc(c, [(1, word[:split]), (2, word[split:] + b"\n")], exit_at=3))
    assert "température" in result.output and "�" not in result.output


def test_the_command_output_still_reaches_the_caller(tmp_path):
    echoed = []
    run(tmp_path, lambda c: FakeProc(c, [(1, b"one\n"), (2, b"two")], exit_at=3), echo=echoed.append)
    assert b"".join(echoed) == b"one\ntwo"


# --- the suite caps ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("command", "cap"),
    [
        (["uv", "run", "pytest", "-n", "auto", "-m", "not slow and not external"], 610),
        (["uv", "run", "pytest", "-n", "auto", "-m", "slow and not external", "tests/test_x.py"], 1330),
        (["npm", "--prefix", "web", "test"], 300),
        (["npm", "--prefix", "workers/scan-proxy", "test"], 60),  # 10 x 2 s, raised to the floor
        (["uv", "run", "scripts/android_session_end.py"], 1060),
        (["uv", "run", "scripts/static_checks.py", "core"], 1960),
        (["something", "else"], rs.DEFAULT_CAP_S),
    ],
)
def test_a_suite_cap_is_about_ten_times_its_measured_run(command, cap):
    assert rs.suite_cap_s(command) == cap


def test_the_cap_factor_can_be_changed():
    assert rs.suite_cap_s(["npm", "--prefix", "web", "test"], factor=20) == 600


def supervised(tmp_path, proc_factory, command):
    clock = FakeClock()
    return rs.supervised_run_command(
        command, status_dir=tmp_path, spawn=lambda argv: proc_factory(clock), clock=clock, echo=lambda _: None, now=clock.wall,
    )


def test_a_suite_that_hits_its_cap_returns_the_hung_code_with_a_reason(tmp_path):
    ticks = [(t, b"tick\n") for t in range(10, 2000, 10)]
    result = supervised(tmp_path, lambda c: FakeProc(c, ticks), ["npm", "--prefix", "workers/scan-proxy", "test"])
    assert result.returncode == rs.HUNG_EXIT_CODE and result.hung_reason.startswith("wall cap")


def test_a_silent_suite_is_hung_by_the_output_limit_before_its_cap(tmp_path):
    result = supervised(tmp_path, lambda c: FakeProc(c, [(1, b"x\n")]), ["uv", "run", "scripts/static_checks.py", "core"])
    assert result.returncode == rs.HUNG_EXIT_CODE and result.hung_reason.startswith("no output")


def test_a_suite_that_passes_or_fails_returns_its_own_exit_code_and_no_hung_reason(tmp_path):
    passed = supervised(tmp_path, lambda c: FakeProc(c, [(1, b"x\n")], exit_at=2), ["npm", "--prefix", "web", "test"])
    failed = supervised(tmp_path, lambda c: FakeProc(c, [(1, b"x\n")], exit_at=2, code=1), ["npm", "--prefix", "web", "test"])
    assert (passed.returncode, passed.hung_reason, failed.returncode, failed.hung_reason) == (0, "", 1, "")


# --- the device run that is retried once ---------------------------------------------------------


class Attempts:
    def __init__(self, results, fresh=True):
        self.results = list(results)
        self.fresh = fresh
        self.runs = 0
        self.boots = 0

    def attempt(self):
        self.runs += 1
        return self.results.pop(0)

    def boot(self):
        self.boots += 1
        return self.fresh


def retry(a):
    return rs.run_with_one_retry(a.attempt, is_infra_abort=lambda r: r == rs.INFRA_ABORT, fresh_emulator=a.boot, out=lambda _: None)


def test_an_infra_abort_is_retried_exactly_once_on_a_fresh_emulator():
    a = Attempts([rs.INFRA_ABORT, rs.PASSED])
    assert retry(a) == (rs.PASSED, 2) and (a.runs, a.boots) == (2, 1)


def test_a_second_infra_abort_is_the_answer_and_there_is_no_third_run():
    a = Attempts([rs.INFRA_ABORT, rs.INFRA_ABORT, rs.PASSED])
    assert retry(a) == (rs.INFRA_ABORT, 2) and (a.runs, a.boots) == (2, 1)


def test_a_failing_test_is_never_retried():
    a = Attempts([rs.TEST_FAILED, rs.PASSED])
    assert retry(a) == (rs.TEST_FAILED, 1) and (a.runs, a.boots) == (1, 0)


def test_a_fresh_emulator_that_does_not_come_up_keeps_the_abort_without_a_second_run():
    a = Attempts([rs.INFRA_ABORT, rs.PASSED], fresh=False)
    assert retry(a) == (rs.INFRA_ABORT, 1) and (a.runs, a.boots) == (1, 1)


# --- the command line ---------------------------------------------------------------------------


def test_the_command_line_needs_a_command_after_the_double_dash():
    with pytest.raises(SystemExit):
        rs.main(["--device"])


def test_retrying_needs_a_device():
    with pytest.raises(SystemExit):
        rs.main(["--retry-infra-abort", "--", "echo", "hi"])


def parsed(*flags):
    import argparse

    ns = argparse.Namespace(suite=False, output_limit_s=None, test_limit_s=rs.TEST_LIMIT_S, wall_limit_s=None)
    for name, value in flags:
        setattr(ns, name, value)
    return ns


def test_the_default_limits_are_120_s_of_silence_and_90_s_for_a_test_with_no_wall_cap():
    limits = rs.resolve_limits(parsed(), ["x"])
    assert (limits.output_s, limits.test_s, limits.wall_s, limits.device_misses) == (120, 90, None, 3)


def test_suite_mode_takes_the_per_suite_cap_and_a_longer_silence_unless_told_otherwise():
    command = ["npm", "--prefix", "web", "test"]
    limits = rs.resolve_limits(parsed(("suite", True)), command)
    assert (limits.output_s, limits.wall_s) == (rs.SUITE_OUTPUT_LIMIT_S, 300)
    explicit = rs.resolve_limits(parsed(("suite", True), ("output_limit_s", 45.0), ("wall_limit_s", 99.0)), command)
    assert (explicit.output_s, explicit.wall_s) == (45, 99)


def test_the_command_is_everything_after_the_double_dash():
    assert rs._split_command(["--device", "--", "gradlew", "-p", "android", "--", "x"]) == (["--device"], ["gradlew", "-p", "android", "--", "x"])
