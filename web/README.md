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

Runs on `http://localhost:5173`. Photo scanning calls the shared Scan service
(the `workers/scan-proxy` Worker) at `VITE_SCAN_SERVICE_URL`, which
`.env.production` sets for the deployed site; put it in `.env.local` to scan
from `npm run dev`. Unset, the Web app says scanning is unavailable and typing
the numbers in still works. A scan needs a signed-in Pro account with at least
one Scan Credit.


## Deploy (Cloudflare Pages)

Live at https://rigcheck-web.pages.dev/. Push-to-deploy via Cloudflare Pages' Git integration (ADR-0007). One-time
dashboard setup: Workers & Pages → Create → Pages → connect the GitHub repo,
then set **Root directory** `web`, **Build command** `npm run build`,
**Build output directory** `dist`, and the production branch. `wrangler.toml`
records the same output directory.
