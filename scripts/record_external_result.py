"""Records one External-suite's real result for the dashboard (roadmap
item #7), so scripts/generate_dashboard.py can show External's status
without re-running real network calls on every regen.

Called from the end of each External wrapper script (android/test-weekly.ps1,
workers/scan-proxy/test-weekly.ps1, workers/scan-proxy/test-release.ps1),
right before they exit, so a real run's result is always what's recorded
- never a live re-run triggered just to update the dashboard graphic.

Usage: uv run scripts/record_external_result.py <platform> <suite> <exit-code>
    platform    e.g. "android", "scan_proxy"
    suite       e.g. "weekly", "release" - a free-form key, one JSON entry
                per platform+suite pair
    exit-code   0 means passed; anything else means failed

Per-surface (ADR-0008) - what the freshness script and the release gate read:
    uv run scripts/record_external_result.py --surface NAME
        --outcome pass|fail|skipped [--versions JSON] [--commit SHA]
        [--override-reason TEXT]
The old platform+suite entries are kept as history only; the gate ignores them.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

STATUS_FILE = Path(__file__).resolve().parent / "dashboard_data" / "external_status.json"


def record(platform: str, suite: str, exit_code: int, *, now: str | None = None) -> dict:
    """Updates and returns the full status dict; also writes it to disk."""
    data = json.loads(STATUS_FILE.read_text(encoding="utf-8")) if STATUS_FILE.exists() else {}
    data.setdefault(platform, {})[suite] = {
        "passed": exit_code == 0,
        "timestamp": now or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return data


OUTCOMES = ("pass", "fail", "skipped")


def _head_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=STATUS_FILE.parent, capture_output=True, text=True, check=True
    ).stdout.strip()


def record_surface(
    surface: str,
    outcome: str,
    *,
    versions: dict[str, str] | None = None,
    commit: str | None = None,
    override_reason: str | None = None,
    now: str | None = None,
) -> dict:
    """Records one surface's run; a `skipped` outcome never replaces a real
    pass/fail, so it can't advance (or erase) the surface's freshness."""
    if outcome not in OUTCOMES:
        raise ValueError(f"outcome must be one of {OUTCOMES}, got {outcome!r}")
    data = json.loads(STATUS_FILE.read_text(encoding="utf-8")) if STATUS_FILE.exists() else {}
    timestamp = now or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    surfaces = data.setdefault("surfaces", {})

    if outcome == "skipped" and surfaces.get(surface, {}).get("result") in ("pass", "fail"):
        entry = surfaces[surface]
        entry["last_skipped_at"] = timestamp
    else:
        entry = {
            "result": outcome,
            "passed": outcome == "pass",
            "timestamp": timestamp,
            "commit": commit or _head_commit(),
            "versions": versions or {},
        }
        if outcome == "skipped":
            entry["last_skipped_at"] = timestamp
        surfaces[surface] = entry
    if override_reason:
        entry["override_reason"] = override_reason

    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return data


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0].startswith("--"):
        surface_parser = argparse.ArgumentParser(description=__doc__)
        surface_parser.add_argument("--surface", required=True)
        surface_parser.add_argument("--outcome", required=True, choices=OUTCOMES)
        surface_parser.add_argument("--versions", type=json.loads, default=None)
        surface_parser.add_argument("--commit")
        surface_parser.add_argument("--override-reason")
        a = surface_parser.parse_args(argv)
        record_surface(
            a.surface, a.outcome, versions=a.versions, commit=a.commit, override_reason=a.override_reason
        )
        return 0

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("platform")
    parser.add_argument("suite")
    parser.add_argument("exit_code", type=int)
    args = parser.parse_args(argv)

    record(args.platform, args.suite, args.exit_code)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
