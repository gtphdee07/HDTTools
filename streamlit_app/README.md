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
