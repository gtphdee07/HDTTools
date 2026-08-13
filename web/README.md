# RigCheck (web)

React + Vite front-end recreating the "RigCheck" design handoff (RV weight
safety check wizard) at pixel fidelity to the "Wandering Trails, Wagging
Tails" design system. This is **npm-managed**, separate from the Python
package in `../src/` (which uses `uv` — see `../Claude.md`).

Currently running on **mocked data** (`src/mockData.ts`) — no backend yet.
Field names in `src/types.ts` mirror `../src/hdttools/models.py` so a future
API integration is a drop-in.

## Setup

```
npm install
npm run dev
```

## Build

```
npm run build
```
