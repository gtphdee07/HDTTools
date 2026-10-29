"""Function tests for scripts/run_watch.py (#200): one alert per incident (a stale or hung run, a device that
stops answering during a run), cleared when the run recovers or ends, nothing for a quiet tick. The clock is a
parameter, the status files are real files in tmp_path written by the status writer, and the alert is a fake
(the Windows balloon is one small function a test replaces)."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.minor]

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import run_status  # noqa: E402
import run_watch  # noqa: E402

T0 = datetime(2026, 10, 28, 12, 0, 0, tzinfo=timezone.utc)


def at(seconds):
    return T0 + timedelta(seconds=seconds)


class Rig:
    """A watcher over status directories, with a scripted emulator and a recording alert."""

    def __init__(self, tmp_path, dirs=("a",)):
        self.dirs = {name: tmp_path / name for name in dirs}
        self.alerts, self.lines = [], []
        self.device = True
        self.device_polls = 0
        self.watcher = run_watch.Watcher(
            read=lambda: run_watch.read_all(lambda: list(self.dirs.values())),
            device_ok=self.answer, alert=lambda title, text: self.alerts.append((title, text)), out=self.lines.append,
            max_age_s=120, device_misses=2,
        )

    def answer(self):
        self.device_polls += 1
        return self.device

    def write(self, name, phase, when, run_id="r1", **fields):
        writer = run_status.StatusWriter(run_id, "gradlew connected", self.dirs[name], now=lambda: at(when), sleep=lambda _: None)
        writer.emit(phase, **fields)

    def tick(self, seconds):
        self.watcher.tick(at(seconds))
        return len(self.alerts)


def test_a_quiet_tick_prints_nothing_and_alerts_nothing(tmp_path):
    rig = Rig(tmp_path)
    rig.write("a", "test", 0, device="ok")
    assert rig.tick(10) == 0 and rig.lines == []


def test_a_stale_running_file_raises_exactly_one_alert_however_many_ticks_follow(tmp_path):
    rig = Rig(tmp_path)
    rig.write("a", "test", 0, device="none")
    assert rig.tick(100) == 0
    assert [rig.tick(t) for t in (130, 160, 190, 220)] == [1, 1, 1, 1]
    assert len(rig.lines) == 1 and rig.lines[0].startswith("ALERT [") and "STALE" in rig.lines[0]


def test_a_hung_file_raises_one_alert_and_says_why(tmp_path):
    rig = Rig(tmp_path)
    rig.write("a", "hung", 0, reason="no output", detail="no output for 121 s (limit 120 s)", evidence="E:/ev")
    assert [rig.tick(t) for t in (1, 31, 61)] == [1, 1, 1]
    assert "HUNG" in rig.lines[0] and "no output for 121 s" in rig.lines[0]


def test_a_recovered_run_clears_the_incident_and_a_new_stall_is_a_new_alert(tmp_path):
    rig = Rig(tmp_path)
    rig.write("a", "test", 0)
    assert rig.tick(200) == 1
    rig.write("a", "test", 210)  # the wrapper is alive again
    assert rig.tick(220) == 1
    assert rig.lines[-1].startswith("cleared [") and "stale" in rig.lines[-1]
    assert rig.tick(500) == 2  # stale again: a fresh incident
    assert len(rig.lines) == 3


def test_a_run_that_ends_clears_its_incident(tmp_path):
    rig = Rig(tmp_path)
    rig.write("a", "test", 0)
    rig.tick(200)
    rig.write("a", "done", 205, outcome="passed")
    rig.tick(210)
    assert rig.lines[-1].startswith("cleared [") and not rig.watcher.open


def test_a_finished_or_failed_run_is_never_stale(tmp_path):
    rig = Rig(tmp_path)
    rig.write("a", "done", 0)
    rig.write("a", "failed", 1, outcome="test-failed", exit_code=1)
    assert rig.tick(10_000) == 0


def test_a_new_hung_run_in_the_same_directory_is_a_new_incident(tmp_path):
    rig = Rig(tmp_path)
    rig.write("a", "hung", 0, run_id="r1", reason="no output")
    rig.tick(1)
    rig.write("a", "hung", 100, run_id="r2", reason="no output")
    assert rig.tick(101) == 2


def test_each_worktree_is_watched_on_its_own(tmp_path):
    rig = Rig(tmp_path, dirs=("a", "b"))
    rig.write("a", "test", 0)
    rig.write("b", "hung", 0, reason="test too long", test="a.B.c")
    assert rig.tick(200) == 2


def test_a_device_that_stops_answering_during_a_device_run_raises_one_alert(tmp_path):
    rig = Rig(tmp_path)
    rig.device = False
    for t in (0, 10, 20, 30):
        rig.write("a", "test", t, device="ok")
    assert rig.tick(1) == 0  # one missed check is not an incident
    assert [rig.tick(2), rig.tick(3), rig.tick(4)] == [1, 1, 1]
    assert "emulator stopped answering" in rig.lines[0]


def test_a_device_that_answers_again_clears_the_device_incident(tmp_path):
    rig = Rig(tmp_path)
    rig.device = False
    rig.write("a", "test", 0, device="ok")
    rig.tick(1)
    rig.tick(2)
    rig.device = True
    rig.write("a", "test", 3, device="ok")
    rig.tick(4)
    assert rig.lines[-1].startswith("cleared [") and "device" in rig.lines[-1]


def test_a_single_good_check_resets_the_missed_checks(tmp_path):
    rig = Rig(tmp_path)
    rig.write("a", "test", 0, device="ok")
    for answer in (False, True, False, True):
        rig.device = answer
        assert rig.tick(1) == 0


def test_the_emulator_is_only_asked_while_a_device_run_is_active(tmp_path):
    rig = Rig(tmp_path)
    rig.write("a", "test", 0, device="none")  # a run that does not use the device
    rig.tick(1)
    rig.write("a", "done", 2, device="ok")
    rig.tick(3)
    assert rig.device_polls == 0
    rig.write("a", "test", 4, device="ok")
    rig.tick(5)
    assert rig.device_polls == 1


def test_a_hung_run_does_not_also_raise_a_device_incident(tmp_path):
    rig = Rig(tmp_path)
    rig.device = False
    rig.write("a", "hung", 0, device="offline", reason="device offline")
    assert rig.tick(1) == 1 and rig.tick(2) == 1


def test_no_status_directory_at_all_is_quiet(tmp_path):
    rig = Rig(tmp_path)
    assert rig.tick(5) == 0 and rig.lines == []


def test_the_balloon_text_is_quoted_so_a_test_name_cannot_break_the_script():
    script = run_watch.balloon_script("Run needs attention", "it's \"bad\"; Remove-Item x")
    assert "'it''s \"bad\"; Remove-Item x'" in script
    assert script.count("ShowBalloonTip") == 1 and "Run needs attention" in script


def test_once_looks_one_time_and_exits(tmp_path):
    sink = tmp_path / "s"
    run_status.StatusWriter("r1", "x", sink, now=lambda: at(0), sleep=lambda _: None).emit("hung", reason="no output")
    assert run_watch.main(["--once", "--no-balloon", "--dir", str(sink), "--max-age-s", "120"]) == 0
