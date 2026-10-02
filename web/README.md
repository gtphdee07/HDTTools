# RigCheck (web)

React + Vite front-end recreating the "RigCheck" design handoff (RV weight
safety check wizard) at pixel fidelity to the "Wandering Trails, Wagging
Tails" design system. This is **npm-managed**, separate from the Python
package in `../src/` (which uses `uv` — see `../Claude.md`).

Fully static: the breakdown math is a TypeScript port (`src/breakdown.ts`)
run in the browser, so there is no hosted backend. Field names in `src/types.ts`
mirror `../src/hdttools/models.py`. Remembers up to 5 recent rigs in
browser `localStorage`; check history is session-only.

## Build

```
npm run build
```

## Setup

```
npm install
npm run dev
```

Runs on `http://localhost:5173`. Optionally set `VITE_API_BASE_URL` (e.g. in
`.env.local`) to point the scan calls at another host; unset means same-origin.


## Deploy (Cloudflare Pages)

Live at https://rigcheck-web.pages.dev/. Push-to-deploy via Cloudflare Pages' Git integration (ADR-0007). One-time
dashboard setup: Workers & Pages → Create → Pages → connect the GitHub repo,
then set **Root directory** `web`, **Build command** `npm run build`,
**Build output directory** `dist`, and the production branch. `wrangler.toml`
records the same output directory.
