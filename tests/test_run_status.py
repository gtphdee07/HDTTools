"""Function tests for scripts/run_status.py (#200): the status file layout the supervisor writes and the
reader's exit codes (0 fresh and running or finished, 1 stale or hung, 2 none), including a file that is
being rewritten. The clock is a parameter and every file lives in tmp_path."""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.minor]

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import run_status as rst  # noqa: E402

T0 = datetime(2026, 10, 28, 12, 0, 0, tzinfo=timezone.utc)


def writer(tmp_path, run_id="r1", at=T0, sleep=lambda _: None):
    return rst.StatusWriter(run_id, "gradlew connected", tmp_path, now=lambda: at, sleep=sleep)


def test_each_event_is_one_line_in_the_log_and_replaces_latest_json(tmp_path):
    w = writer(tmp_path)
    w.emit("boot")
    w.emit("test", test="a.B.c", n=1, of=9)
    log = [json.loads(ln) for ln in (tmp_path / "r1.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [e["phase"] for e in log] == ["boot", "test"]
    latest = json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))
    assert latest == log[-1] and latest["t"] == "2026-10-28T12:00:00Z"
    assert (latest["test"], latest["n"], latest["of"], latest["device"], latest["run_id"]) == ("a.B.c", 1, 9, "none", "r1")


def test_a_field_not_given_keeps_the_last_value(tmp_path):
    w = writer(tmp_path)
    w.emit("test", test="a.B.c", n=4, of=9)
    assert w.emit("test", last_output_age_s=12.0)["n"] == 4


def test_no_temporary_file_is_left_behind(tmp_path):
    writer(tmp_path).emit("boot")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["latest.json", "r1.jsonl"]


def test_the_replace_is_retried_when_a_reader_holds_the_file(tmp_path, monkeypatch):
    real, calls = rst.os.replace, []

    def flaky(source, target):
        calls.append(1)
        if len(calls) < 3:
            raise PermissionError("held open")
        real(source, target)

    monkeypatch.setattr(rst.os, "replace", flaky)
    writer(tmp_path).emit("boot")
    assert len(calls) == 3 and json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))["phase"] == "boot"


class StepEvent:
    """A stand-in for threading.Event: `wait` answers False (keep going) `beats` times, then True (stop)."""

    def __init__(self, beats):
        self.beats = beats
        self.waited = []

    def wait(self, timeout=None):
        self.waited.append(timeout)
        self.beats -= 1
        return self.beats < 0

    def set(self):
        self.beats = -1


def test_the_heartbeat_rewrites_the_current_state_every_interval_while_the_run_is_active(tmp_path):
    clock = iter(range(0, 1000, 10))
    w = rst.StatusWriter("r1", "boot", tmp_path, now=lambda: T0 + timedelta(seconds=next(clock)), sleep=lambda _: None)
    w.emit("boot", device="none")
    stop = StepEvent(beats=3)
    rst.Heartbeat(w, interval_s=10, stop=stop).run()
    lines = [json.loads(ln) for ln in (tmp_path / "r1.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [e["phase"] for e in lines] == ["boot"] * 4 and stop.waited == [10, 10, 10, 10]
    assert [e["t"][-3:-1] for e in lines] == ["00", "10", "20", "30"]  # each beat is a newer time, so the file never goes stale


def test_a_beat_never_overwrites_a_line_that_ended_the_run(tmp_path):
    w = writer(tmp_path)
    w.emit("boot")
    w.emit("failed", outcome="infra-abort")
    assert w.refresh() is False
    rst.Heartbeat(w, stop=StepEvent(beats=2)).run()
    assert json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))["phase"] == "failed"


def test_the_heartbeat_thread_starts_and_stops_with_the_block(tmp_path):
    w = writer(tmp_path)
    w.emit("boot")
    stop = StepEvent(beats=0)
    with rst.Heartbeat(w, stop=stop):
        pass
    assert stop.beats == -1


def check(tmp_path, seconds_later=0, max_age=120):
    return rst.check(tmp_path, T0 + timedelta(seconds=seconds_later), max_age)


def test_a_fresh_running_file_exits_0(tmp_path):
    writer(tmp_path).emit("test", test="a.B.c", n=2, of=10, device="ok", last_output_age_s=3.0)
    code, text = check(tmp_path, 30)
    assert code == 0 and "r1" in text and "2 of 10" in text and "a.B.c" in text


def test_a_fresh_done_file_exits_0(tmp_path):
    writer(tmp_path).emit("done", n=10, of=10, outcome="passed", exit_code=0)
    assert check(tmp_path, 5)[0] == 0


def test_a_file_older_than_max_age_exits_1(tmp_path):
    writer(tmp_path).emit("test")
    assert check(tmp_path, 121)[0] == 1 and "STALE" in check(tmp_path, 121)[1]
    assert check(tmp_path, 120)[0] == 0
    assert check(tmp_path, 121, max_age=300)[0] == 0  # --max-age-s moves the line


def test_a_hung_file_exits_1_even_when_fresh_and_says_why(tmp_path):
    writer(tmp_path).emit("hung", reason="no output", detail="no output for 121 s (limit 120 s)", evidence="E:/ev")
    code, text = check(tmp_path, 1)
    assert code == 1 and "HUNG" in text and "no output for 121 s" in text and "E:/ev" in text


def test_no_run_exits_2(tmp_path):
    assert check(tmp_path / "missing")[0] == 2
    assert check(tmp_path)[0] == 2


def test_a_latest_json_being_rewritten_is_never_read_half_written(tmp_path):
    w = writer(tmp_path)
    w.emit("test", n=1, of=5)
    w.emit("test", n=2, of=5)
    good = (tmp_path / "latest.json").read_text(encoding="utf-8")
    (tmp_path / "latest.json").write_text(good[: len(good) // 2], encoding="utf-8")  # cut mid-line
    record = rst.read_latest(tmp_path, sleep=lambda _: None)
    assert record["n"] == 2 and record["phase"] == "test"


def test_a_half_written_last_log_line_is_skipped_for_the_one_before(tmp_path):
    w = writer(tmp_path)
    w.emit("test", n=1, of=5)
    w.emit("test", n=2, of=5)
    (tmp_path / "latest.json").unlink()
    with open(tmp_path / "r1.jsonl", "a", encoding="utf-8") as log:
        log.write('{"t": "2026-10-28T12:00:00Z", "phase": "te')  # the writer is mid-append: no newline yet
    assert rst.read_latest(tmp_path, sleep=lambda _: None)["n"] == 2


def test_the_newest_run_wins_when_latest_json_is_missing(tmp_path):
    writer(tmp_path, "old").emit("done")
    newer = writer(tmp_path, "new")
    newer.emit("test")
    (tmp_path / "latest.json").unlink()
    import os
    os.utime(tmp_path / "old.jsonl", (1, 1))
    assert rst.read_latest(tmp_path)["run_id"] == "new"


def test_the_command_line_prints_the_line_and_returns_the_code(tmp_path):
    writer(tmp_path).emit("test", n=1, of=2)
    printed = []
    code = rst.main(["--dir", str(tmp_path), "--max-age-s", "60"], out=printed.append, now=lambda: T0 + timedelta(seconds=10))
    assert code == 0 and "Run r1 is in test" in printed[0]
    assert rst.main(["--dir", str(tmp_path / "none")], out=printed.append, now=lambda: T0) == 2
