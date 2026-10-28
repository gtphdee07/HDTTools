"""Capture the Android app's screen states: a PNG and the measured bounds of every tagged element (#189).

Builds and installs the debug app and its test APK on the one emulator, runs LayoutCaptureTest on it (which sets the
display to each phone frame, opens every reachable screen state of docs/android-redesign/ui-inventory.json and
measures it twice), and pulls the files to android/app/build/layout-capture/<frame>/<screen>__<state>.{png,json}.
The PNGs are build output and are not committed; the owner copies the 412x892 set to the designer. Merge the bounds
into the inventory with:

  uv run scripts/ui_inventory.py --merge-bounds android/app/build/layout-capture

Needs the single emulator already booted (no other Android ticket may be running); it refuses any other device, so
the owner's phone is never touched, and puts the display size, density and font scale back when it is done.

Usage: uv run scripts/android_layout_capture.py [--out DIR]
Exit code: 0 captured, 1 a state could not be captured or the two measurements differed, 2 the run did not complete.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import android_release  # noqa: E402
import android_suite_loop  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
EMULATOR = "emulator-5554"
APP_PACKAGE = android_suite_loop.APP_PACKAGE
TEST_CLASS = f"{APP_PACKAGE}.layoutcapture.LayoutCaptureTest"
DEVICE_FOLDER = f"/sdcard/Android/data/{APP_PACKAGE}/files/layout-capture"
DEFAULT_OUT = REPO_ROOT / "android" / "app" / "build" / "layout-capture"


def instrument_command(adb: str) -> list[str]:
    return [
        adb, "-s", EMULATOR, "shell", "am", "instrument", "-w", "-r",
        "-e", "layoutCapture", "true", "-e", "class", TEST_CLASS, android_suite_loop.RUNNER,
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="where the frame folders are written")
    args = parser.parse_args(argv)

    adb = android_release.default_adb()
    devices = android_release.connected_devices(adb=adb)
    if EMULATOR not in devices:
        print(f"{EMULATOR} is not attached (found: {', '.join(devices) or 'nothing'}); start the emulator first.")
        return 2

    # ANDROID_SERIAL keeps Gradle's install tasks off any other attached device (the owner's phone).
    env = {**os.environ, "ANDROID_SERIAL": EMULATOR}
    build = subprocess.run(
        [android_suite_loop.GRADLEW, "-p", "android", ":app:installDebug", ":app:installDebugAndroidTest"],
        cwd=REPO_ROOT, env=env,
    )
    if build.returncode != 0:
        return 2

    adb_run = lambda *a: subprocess.run([adb, "-s", EMULATOR, *a], capture_output=True, text=True, errors="replace")  # noqa: E731
    adb_run("shell", "rm", "-rf", DEVICE_FOLDER)
    run = subprocess.run(instrument_command(adb), capture_output=True, text=True, errors="replace", cwd=REPO_ROOT)
    output = (run.stdout or "") + (run.stderr or "")
    # The test puts the display back itself; this is for a run that died before it could.
    adb_run("shell", "wm", "size", "reset")
    adb_run("shell", "wm", "density", "reset")

    outcome = android_suite_loop.classify_run(output, run.returncode)
    args.out.mkdir(parents=True, exist_ok=True)
    pull = adb_run("pull", f"{DEVICE_FOLDER}/.", str(args.out))
    if pull.returncode != 0:
        print(f"nothing pulled from {DEVICE_FOLDER}: {pull.stderr.strip()}")
    for frame in sorted(p for p in args.out.iterdir() if p.is_dir()):
        print(f"{frame.name}: {len(list(frame.glob('*.png')))} PNGs, {len(list(frame.glob('*.json')))} bounds files")

    if outcome.kind != android_suite_loop.PASSED:
        print(output[-6000:])
        print(f"layout capture: {outcome.kind}: {outcome.reason}")
        return 1 if outcome.kind == android_suite_loop.TEST_FAILED else 2
    print(f"layout capture done: {args.out}\nnext: uv run scripts/ui_inventory.py --merge-bounds {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
