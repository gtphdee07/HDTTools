# RigCheck (web)

React + Vite front-end recreating the "RigCheck" design handoff (RV weight
safety check wizard) at pixel fidelity to the "Wandering Trails, Wagging
Tails" design system. This is **npm-managed**, separate from the Python
package in `../src/` (which uses `uv` — see `../Claude.md`).

Talks to the stateless FastAPI backend in `../src/hdttools/api/` (no
database — see the root `README.md`). Field names in `src/types.ts`
mirror `../src/hdttools/models.py`. Remembers up to 5 recent rigs in
browser `localStorage`; check history is session-only.

## Setup

```
# Backend, from the repo root (separate terminal)
uv sync
uv run uvicorn hdttools.api.main:app --reload --port 8000

# Frontend
npm install
npm run dev
```

Runs on `http://localhost:5173`, talking to the backend on
`http://localhost:8000`.

## Build

```
npm run build
```
