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
"""

from __future__ import annotations

import argparse
import json
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("platform")
    parser.add_argument("suite")
    parser.add_argument("exit_code", type=int)
    args = parser.parse_args(argv)

    record(args.platform, args.suite, args.exit_code)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
