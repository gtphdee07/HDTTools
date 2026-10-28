"""Paths and tools for the design generator. Everything is derived from this file's place in the repo,
so the folder works from any checkout. Override with environment variables when needed:
  RIGCHECK_DESIGN_OUT  where frames, boards and measurements are written (default: <TEMP>/rigcheck_design_out)
  CHROME_PATH          a Chrome or Chromium executable (default: Playwright's cached Chromium under %LOCALAPPDATA%, else Playwright's own)
"""
import glob
import os
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
ANDROID_REDESIGN = REPO / 'docs' / 'android-redesign'
INVENTORY = ANDROID_REDESIGN / 'ui-inventory.json'
RETURN = ANDROID_REDESIGN / 'design-return'
LOGO_FILE = (REPO / 'web' / 'public' / 'logo.png').as_uri()
OUT = pathlib.Path(os.environ.get('RIGCHECK_DESIGN_OUT') or (pathlib.Path(os.environ.get('TEMP') or os.environ.get('TMPDIR') or '.') / 'rigcheck_design_out'))


def chrome_path():
    """A Chromium executable for headless rendering, or None to let Playwright use its own."""
    if os.environ.get('CHROME_PATH'):
        return os.environ['CHROME_PATH']
    local = os.environ.get('LOCALAPPDATA')
    if local:
        found = sorted(glob.glob(os.path.join(local, 'ms-playwright', 'chromium-*', 'chrome-win64', 'chrome.exe')))
        if found:
            return found[-1]
    return None
