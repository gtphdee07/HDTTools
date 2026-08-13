# RigCheck (Streamlit)

Self-contained alternative to the `web/` React/FastAPI app: same wizard
flow (rig → truck tag → trailer tag → scale ticket → results), but a
single Python process — no separate backend, no HTTP hop. Imports
`hdttools`'s OCR-parsing and breakdown logic directly.

## Setup

From the repo root (this is part of the `hdttools` project, installed via
an optional dependency group so the core CLI package doesn't require it
by default):

```
uv sync --extra streamlit
```

Also requires the Tesseract OCR engine installed separately — see the
root `README.md`'s Tesseract section (works cross-platform: Windows,
macOS via Homebrew, or Linux's system package).

## Run

```
uv run --extra streamlit streamlit run streamlit_app/app.py
```

Opens at `http://localhost:8501`.

## Notes

- Remembers up to 5 recent rigs (nickname + reviewed truck/trailer data)
  in `~/.rigcheck/recent_rigs.json` — local to the machine, won't survive
  a redeploy on an ephemeral host (e.g. Streamlit Community Cloud).
- Check history is session-only (shown in the sidebar), same as the web
  app — nothing is persisted to a database.
- `fields.py` mirrors `web/src/mockData.ts`'s `MODULES` so both frontends
  review the same fields.
- `app.py` adds `../src` to `sys.path` at import time rather than relying
  on `hdttools` being pip-installed, since a relative local-package path
  in `requirements.txt` resolves against pip's working directory (which
  isn't reliably the same as this file's location on every host) — this
  way it works regardless of where the process is launched from.

## Deploying to Streamlit Community Cloud

This app is set up to deploy as-is — `packages.txt` (installs the
Tesseract OCR system package) and `requirements.txt` (Python
dependencies) live in this directory, which is where Community Cloud
looks first when your main file isn't at the repo root.

1. Go to https://share.streamlit.io and sign in with GitHub.
2. Click **New app** (or **Create app**).
3. Pick this repository (`gtphdee07/HDTTools`), branch `main`.
4. Set **Main file path** to `streamlit_app/app.py`.
5. Click **Deploy**.

The first deploy will take a few minutes (installing `tesseract-ocr` via
`apt-get`, then the Python dependencies). If it fails to find
`packages.txt`/`requirements.txt` in this directory for any reason, the
documented fallback is a copy of both files at the repo root instead.

**Known limitation on this platform**: the recent-rigs JSON file
(`~/.rigcheck/recent_rigs.json`) won't survive a redeploy or container
restart — Community Cloud's filesystem is ephemeral. Each fresh deploy
starts with an empty recent-rigs list. This is an accepted tradeoff, not
a bug to fix.
