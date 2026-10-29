"""Watches supervised runs from outside the sessions that started them (#200).

  uv run scripts/run_watch.py [--interval-s 30] [--max-age-s 120] [--dir DIR ...] [--once] [--no-balloon]

Every `--interval-s` it reads the newest status (`latest.json`, scripts/run_status.py) of every
worktree of this repository, and, while a run that uses a device is active, asks the emulator itself
whether it still answers. A run is an incident when its file is `hung`, or when a running file has not
been updated for `--max-age-s` (the supervisor rewrites it every 10 s, so a stale file means the wrapper
itself died), and a device that stops answering for two checks in a row during a device run is one more.
Each incident raises ONE alert when it appears (not one per tick) and a `cleared` line when it goes away:
the run recovered, ended, or was replaced by a new one. An alert is a Windows balloon notification (nothing
to install) and a line on stdout, so it can also run as a Monitor inside a Claude session: each line
wakes that session. Quiet ticks print nothing.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_status  # noqa: E402

INTERVAL_S = 30.0
DEVICE_MISSES = 2
WINDOW_S = 3600.0  # a hung or stale record older than this is history: starting the watcher does not re-announce it

Incident = tuple[str, str, str]  # (status directory, run id, kind: hung | stale | device)


def is_active(record: dict) -> bool:
    return record.get("phase") in run_status.ACTIVE_PHASES


def uses_device(record: dict) -> bool:
    return is_active(record) and record.get("device", "none") != "none"


def find_incidents(
    records: dict[str, dict], now: datetime, max_age_s: float, device_down: bool, window_s: float = WINDOW_S
) -> dict[Incident, str]:
    """The incidents of the moment, keyed (status directory, run id, kind) with the line to show; `records` is each status
    directory's newest record. A hung or stale record older than `window_s` is history, not news. Pure."""
    found: dict[Incident, str] = {}
    for where, record in records.items():
        age = run_status.age_seconds(record, now)
        if age is not None and age > window_s:
            continue
        if record.get("phase") == "hung":
            found[(where, record.get("run_id", "?"), "hung")] = run_status.describe(record, now)
        elif is_active(record):
            if age is None or age > max_age_s:
                found[(where, record.get("run_id", "?"), "stale")] = f"STALE (no update for more than {max_age_s:.0f} s; the wrapper may have died): " + run_status.describe(record, now)
            elif device_down and uses_device(record):
                found[(where, record.get("run_id", "?"), "device")] = f"The emulator stopped answering during run {record.get('run_id', '?')}: " + run_status.describe(record, now)
    return found


class Watcher:
    def __init__(
        self,
        *,
        read: Callable[[], dict[str, dict]],
        device_ok: Callable[[], bool],
        alert: Callable[[str, str], None],
        out: Callable[[str], None] = lambda text: print(text, flush=True),
        max_age_s: float = run_status.DEFAULT_MAX_AGE_S,
        device_misses: int = DEVICE_MISSES,
        window_s: float = WINDOW_S,
    ):
        self.read, self.device_ok, self.alert, self.out = read, device_ok, alert, out
        self.max_age_s, self.device_misses, self.window_s = max_age_s, device_misses, window_s
        self.open: dict[Incident, str] = {}
        self.misses = 0

    def tick(self, now: datetime) -> None:
        records = self.read()
        if any(uses_device(r) for r in records.values()):
            self.misses = 0 if self.device_ok() else self.misses + 1
        else:
            self.misses = 0
        incidents = find_incidents(records, now, self.max_age_s, self.misses >= self.device_misses, self.window_s)
        for key, text in incidents.items():
            if key not in self.open:
                self.out(f"ALERT [{key[0]}] {text}")
                self.alert("Run needs attention", text)
        for key in self.open:
            if key not in incidents:
                self.out(f"cleared [{key[0]}] {key[2]} ({key[1]}): the run recovered, ended or was replaced")
        self.open = incidents


def powershell_quote(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def balloon_script(title: str, text: str) -> str:
    """The PowerShell that shows a balloon notification (Windows, no install)."""
    return (
        "Add-Type -AssemblyName System.Windows.Forms; Add-Type -AssemblyName System.Drawing; "
        "$n = New-Object System.Windows.Forms.NotifyIcon; $n.Icon = [System.Drawing.SystemIcons]::Warning; "
        f"$n.Visible = $true; $n.ShowBalloonTip(15000, {powershell_quote(title)}, {powershell_quote(text[:250])}, 'Warning'); "
        "Start-Sleep -Seconds 16; $n.Dispose()"
    )


def balloon(title: str, text: str) -> None:
    """The one place a notification is raised. Does not wait for the balloon to go away; a no-op off Windows."""
    if os.name != "nt":
        return
    subprocess.Popen(
        ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", balloon_script(title, text)],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def emulator_answers() -> bool:
    """Does the emulator answer `adb`? (True when there is no Android SDK to ask.) Only called during a device run."""
    import run_supervisor as rs

    adb = rs.real_adb()
    return adb is None or rs.device_state(adb) == "ok"


def worktree_status_dirs(repo: Path) -> list[Path]:
    """The run-status directory of every worktree of the repository (the main checkout and each ticket worktree)."""
    result = subprocess.run(["git", "worktree", "list", "--porcelain"], cwd=repo, capture_output=True, text=True, timeout=30)
    roots = [Path(ln[len("worktree "):]) for ln in result.stdout.splitlines() if ln.startswith("worktree ")]
    return [root / "android" / "build" / "run-status" for root in roots]


def read_all(directories: Callable[[], list[Path]]) -> dict[str, dict]:
    records = {}
    for directory in directories():
        record = run_status.read_latest(directory) if directory.is_dir() else None
        if record is not None:
            records[str(directory)] = record
    return records


def main(
    argv: list[str] | None = None,
    *,
    now: Callable[[], datetime] = run_status.utc_now,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--interval-s", type=float, default=INTERVAL_S)
    parser.add_argument("--max-age-s", type=float, default=run_status.DEFAULT_MAX_AGE_S)
    parser.add_argument("--dir", type=Path, action="append", default=[], help="a run-status directory to watch (default: every worktree's)")
    parser.add_argument("--once", action="store_true", help="look once and exit")
    parser.add_argument("--no-balloon", action="store_true", help="stdout lines only")
    args = parser.parse_args(argv)

    repo = Path(__file__).resolve().parent.parent
    directories = (lambda: args.dir) if args.dir else (lambda: worktree_status_dirs(repo))
    watcher = Watcher(
        read=lambda: read_all(directories),
        device_ok=emulator_answers,
        alert=(lambda title, text: None) if args.no_balloon else balloon,
        max_age_s=args.max_age_s,
    )
    while True:
        watcher.tick(now())
        if args.once:
            return 0
        sleep(args.interval_s)


if __name__ == "__main__":
    sys.exit(main())
