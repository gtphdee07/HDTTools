"""The status file a supervised long command leaves behind (#200), and the reader for it.

`scripts/run_supervisor.py` runs a command and appends one JSON line per event to
`android/build/run-status/<run-id>.jsonl`, and rewrites `latest.json` (one line, replaced
atomically) with the newest state. This module owns that layout: `StatusWriter` writes it,
`read_latest` reads it without ever returning a half-written line, and the command line
tells a person (or the session that started the run) what the run is doing:

  uv run scripts/run_status.py [--max-age-s 120] [--dir DIR]

Exit code: 0 the newest run is running or finished and its file is fresh, 1 the file is older
than --max-age-s or the run is `hung`, 2 no run was found.

Fields of a line: `t` (ISO time, UTC), `run_id`, `phase` (boot, install, test, done, hung,
failed), `command`, `test` (class.method now running, when known), `n` and `of` (tests
finished and expected, when known), `last_output_age_s`, `device` (ok, slow, offline, or none
when the command does not use a device); a line may also carry `reason`, `outcome`,
`exit_code` and `evidence`.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DIR = REPO_ROOT / "android" / "build" / "run-status"
LATEST = "latest.json"

ACTIVE_PHASES = ("boot", "install", "test")  # the others are done, hung and failed

DEFAULT_MAX_AGE_S = 120.0


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_time(stamp: str | None) -> datetime | None:
    try:
        return datetime.strptime(stamp or "", "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def replace_file(source: Path, target: Path, *, sleep: Callable[[float], None] = time.sleep, tries: int = 5) -> None:
    """os.replace, retried: on Windows it fails while a reader holds the target open."""
    for attempt in range(tries):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if attempt == tries - 1:
                raise
            sleep(0.05)


class StatusWriter:
    """Appends each event to `<run-id>.jsonl` and replaces `latest.json` with it. A field not given
    to `emit` keeps the value of the last event, so `test`, `n` and `of` survive a heartbeat."""

    def __init__(
        self,
        run_id: str,
        command: str,
        directory: Path,
        *,
        now: Callable[[], datetime] = utc_now,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.run_id = run_id
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.log = self.directory / f"{run_id}.jsonl"
        self.latest = self.directory / LATEST
        self._now = now
        self._sleep = sleep
        self.state: dict = {
            "t": None, "run_id": run_id, "phase": None, "command": command,
            "test": None, "n": None, "of": None, "last_output_age_s": 0.0, "device": "none",
        }

    def emit(self, phase: str, **fields) -> dict:
        self.state.update(fields)
        self.state["phase"] = phase
        self.state["t"] = iso(self._now())
        line = json.dumps(self.state, ensure_ascii=False)
        with open(self.log, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")  # one write, so a reader sees whole lines
        temp = self.latest.with_name(f"{LATEST}.{os.getpid()}.tmp")
        temp.write_text(line + "\n", encoding="utf-8")
        replace_file(temp, self.latest, sleep=self._sleep)
        return dict(self.state)


def _last_complete_line(path: Path) -> dict | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in reversed(text.split("\n")[:-1]):  # the final piece has no newline yet: it may be half written
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if isinstance(record, dict):
            return record
    return None


def read_latest(directory: Path, *, sleep: Callable[[float], None] = time.sleep, tries: int = 3) -> dict | None:
    """The newest state, or None when no run has left a file. `latest.json` is replaced as a whole, so it
    is either the old line or the new one; if it still does not parse (a copy in flight, a crash), fall
    back to the last complete line of the newest log."""
    directory = Path(directory)
    for attempt in range(tries):
        try:
            record = json.loads((directory / LATEST).read_text(encoding="utf-8"))
        except FileNotFoundError:
            break
        except (OSError, ValueError):
            if attempt < tries - 1:
                sleep(0.05)
            continue
        if isinstance(record, dict):
            return record
    logs = sorted(directory.glob("*.jsonl"), key=lambda p: p.stat().st_mtime) if directory.is_dir() else []
    for log in reversed(logs):
        record = _last_complete_line(log)
        if record is not None:
            return record
    return None


def age_seconds(record: dict, now: datetime) -> float | None:
    stamp = parse_time(record.get("t"))
    return max((now - stamp).total_seconds(), 0.0) if stamp else None


def describe(record: dict, now: datetime) -> str:
    """The newest state in words."""
    phase = record.get("phase")
    run = record.get("run_id", "?")
    seen = age_seconds(record, now)
    when = f"last update {seen:.0f} s ago" if seen is not None else "last update time unknown"
    progress = ""
    if record.get("n") is not None:
        progress = f", {record['n']} of {record['of']} tests finished" if record.get("of") else f", {record['n']} tests finished"
    test = f" ({record['test']})" if record.get("test") and phase == "test" else ""
    if phase == "hung":
        why = record.get("reason") or "no reason recorded"
        if record.get("detail"):
            why += f" ({record['detail']})"
        return f"Run {run} HUNG: {why}{progress}. Evidence: {record.get('evidence') or 'none'}."
    if phase == "failed":
        return f"Run {run} failed (exit {record.get('exit_code')}, {record.get('outcome') or 'unclassified'}){progress}; {when}."
    if phase == "done":
        return f"Run {run} finished{progress}; {when}."
    output = record.get("last_output_age_s")
    quiet = f", no output for {output:.0f} s" if isinstance(output, (int, float)) else ""
    return f"Run {run} is in {phase}{test}{progress}{quiet}, device {record.get('device', 'none')}; {when}."


def check(directory: Path, now: datetime, max_age_s: float = DEFAULT_MAX_AGE_S) -> tuple[int, str]:
    record = read_latest(directory)
    if record is None:
        return 2, f"No run found in {directory}."
    text = describe(record, now)
    seen = age_seconds(record, now)
    if record.get("phase") == "hung":
        return 1, text
    if seen is None or seen > max_age_s:
        return 1, f"STALE (older than {max_age_s:.0f} s): {text}"
    return 0, text


def main(argv: list[str] | None = None, *, out: Callable[[str], None] = print, now: Callable[[], datetime] = utc_now) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--max-age-s", type=float, default=DEFAULT_MAX_AGE_S, help="a file older than this is stale (default 120)")
    parser.add_argument("--dir", type=Path, default=DEFAULT_DIR, help="the run-status directory")
    args = parser.parse_args(argv)
    code, text = check(args.dir, now(), args.max_age_s)
    out(text)
    return code


if __name__ == "__main__":
    sys.exit(main())
