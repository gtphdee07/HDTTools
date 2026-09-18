# Web app beta deployment (React + FastAPI)

## Context

Business need: get the web app online for a public beta soon. Of the
three RigCheck platforms, Streamlit already has a public URL
(`https://hdttools-ynfeq8py78ghmeyulo2grr.streamlit.app`) and Android is
mid-build and explicitly out of scope for this work. The React (`web/`)
+ FastAPI (`src/hdttools/api/`) combination is the one platform still
`localhost`-only — this plan gets it deployed without touching anything
Android or `workers/scan-proxy/` depend on.

Decisions locked in during planning:
- **Scope**: React + FastAPI only (not Streamlit, not Android).
- **Hosting shape**: one combined service — FastAPI serves the built
  React static files itself, single URL, single deploy.
- **OCR backend for beta**: Tesseract only (the existing default).
  Confirmed during exploration: `main.py` has zero rate-limiting or
  request throttling anywhere, and `workers/scan-proxy/`'s cost-gating
  pattern (RevenueCat credits) is tightly coupled to Android's purchase
  flow and not reusable here. Turning on `HDTTOOLS_OCR_BACKEND=claude`
  publicly would expose real, unmetered Anthropic billing to anyone who
  finds the URL — out of scope for this beta. Revisit only alongside a
  real cost-gating mechanism.
- **Domain**: keep the GoDaddy registration as-is (DNS only — GoDaddy's
  basic/shared hosting can't run this app, it never needs to). Add a
  subdomain (e.g. `rigcheck.yourdomain.com`) pointed at the new host;
  the existing root-domain page stays untouched.

## Goal

A real, public beta URL serving the React frontend + FastAPI backend
together, safely (bounded resource risk, no crash-prone deploy, no
surprise billing exposure), with zero changes to `android/` or
`workers/scan-proxy/`.

## Real gaps found during exploration (why each step below exists)

- `web/src/api.ts:3` hardcodes `API_BASE_URL = 'http://localhost:8000'`
  — the only thing wiring frontend to backend; must become
  environment-aware.
- `src/hdttools/api/main.py:35` CORS only allows
  `http://localhost:5173`; no `/health` endpoint exists anywhere; no
  upload size limit on `UploadFile.read()` (`main.py:56`, `:94`) — a
  public endpoint reading arbitrary uploads fully into memory with no
  cap is a real resource-exhaustion risk once this is public.
- `pyproject.toml`'s base `dependencies` list `easyocr`,
  `opencv-python-headless`, and `pyzbar` — confirmed zero imports of any
  of them anywhere in `src/hdttools`, `streamlit_app`, or `tests` (dead
  weight left over from the closed BoundOCR experiment, see
  `ARCHIVE_WEB_STREAMLIT.md`). These are large (PyTorch-backed) and
  would bloat and slow every build of the deploy image for no reason.
- No `Dockerfile`/`render.yaml`/equivalent exists anywhere in the repo —
  deploy config is being built from scratch.
- `web/package.json` has no `react-router` dependency — the app is a
  single-page wizard with in-memory step state, not URL-based routing,
  so serving it is just "serve `index.html` + static assets," no
  catch-all routing logic needed.
- The tkinter-import crash fixed earlier this session
  (`858d829`) already protects `main.py` too, since it imports the same
  `scale_ticket`/`trailer_tag`/`truck_tag` modules — confirmed no
  further action needed there.

## Steps

1. **Trim dead dependencies.** Remove `easyocr`, `opencv-python-headless`,
   `pyzbar` from `pyproject.toml`'s `dependencies`. Run `uv sync` then
   the full `uv run pytest -q` suite to confirm this is a true no-op
   functionally (it should be — nothing imports them).

2. **Make the frontend's API base URL environment-aware.**
   `web/src/api.ts:3`: change the hardcoded
   `http://localhost:8000` to resolve to the same origin in a
   production build and keep the current localhost value only for
   `npm run dev` — e.g. `const API_BASE_URL = import.meta.env.DEV ?
   'http://localhost:8000' : '';` (relative paths then hit whatever
   origin actually served the page, which is exactly right for a
   combined single-service deploy). Update `web/src/api.test.ts`'s
   hardcoded-URL assertions only if they actually break under this
   change (Vitest runs in dev-like mode by default) — confirm for real
   rather than assuming.

3. **Add production-safety guards to `main.py`** (TDD: failing test
   first for each):
   - `GET /health` returning a simple `{"status": "ok"}` — needed by
     the host's readiness checks and for your own uptime checks.
   - A max upload size check in `_ocr_upload`/`_extract_fields`'s shared
     upload-reading path (e.g. reject anything over ~10MB with a 413)
     — currently unbounded.
   - Leave CORS as-is; a same-origin combined deploy won't exercise it
     in production, and the existing `localhost:5173` entry keeps local
     dev working.

4. **Dockerize the combined service** (root-level `Dockerfile`, matches
   `requires-python = ">=3.14"`):
   - Stage 1 (`node`): `cd web && npm ci && npm run build` → `web/dist`.
   - Stage 2 (`python`): install `tesseract-ocr` via `apt-get`, install
     `uv`, `uv sync --no-dev --frozen`, copy `src/`, copy `web/dist`
     from stage 1.
   - In `main.py`, after all `@app.post("/api/...")` routes are
     registered, add `app.mount("/", StaticFiles(directory=..., html=True))`
     so `/` serves the built SPA while `/api/*` keeps routing to the
     existing handlers (Starlette matches routes in registration order,
     so this is safe as long as the mount is added last).
   - `CMD` runs `uvicorn hdttools.api.main:app --host 0.0.0.0 --port
     ${PORT:-8000}` — no `--reload` in production.

5. **Add deploy config.** A `render.yaml` (Docker-runtime web service,
   health check path `/health`, no `ANTHROPIC_API_KEY` needed since this
   beta is Tesseract-only) so the setup is reproducible and documented
   in-repo rather than only living in a dashboard. Render is the
   concrete recommendation (native Docker web services, free automatic
   TLS + custom domains, no separate database/persistence need since
   this backend is stateless) — the same Dockerfile would work
   unchanged on Fly.io or Railway if you'd rather use one of those.

6. **You point the domain** (manual, external — I can't touch GoDaddy or
   the hosting dashboard): add a CNAME record for the subdomain (e.g.
   `rigcheck`) at GoDaddy pointing to the host-issued hostname, then add
   the custom domain in the host's dashboard for that service and wait
   for the TLS certificate to auto-issue. I'll give you the exact record
   to add once the service exists and its hostname is known.

7. **Update docs.** `README.md`'s "Web" section gets a "Live demo" line
   once the URL is known (matching Streamlit's existing one);
   `web/README.md` gets a short deployment section (Docker build, the
   `API_BASE_URL` behavior); `NEXT_STEPS.md`'s "Known limitations" /
   "Natural next steps" updated to reflect the web app is now hosted
   (mirroring how the Streamlit deployment note was added 2026-09-18);
   any real bug/decision found along the way gets a writeup in
   `ARCHIVE_WEB_STREAMLIT.md` per this project's archive convention.

## Definition of Done

- A real public URL serves the built React frontend, backed by the live
  FastAPI backend, on Tesseract only.
- Uploading a real `ExampleDocs/` photo through that public URL produces
  a real extraction → review → breakdown verdict, hand-verified against
  golden data.
- `/health` returns 200; an oversized upload is rejected cleanly, not a
  crash/hang.
- Full `uv run pytest -q` and `cd web && npm test` both pass.
- The custom subdomain resolves over HTTPS once DNS propagates, and the
  existing root-domain page is untouched.
- Zero code changes under `android/` or `workers/scan-proxy/`;
  `src/hdttools/api/breakdown.py` (the Kotlin golden-vector contract) is
  untouched.
- `README.md`/`web/README.md`/`NEXT_STEPS.md` reflect the deployed state.

## Verification

- Build and run the Docker image locally; `curl localhost:PORT/health`;
  upload a real `ExampleDocs/` photo via the running container and
  confirm the extraction/verdict matches golden data.
- Deploy to the chosen host; repeat the same manual check against the
  live `*.onrender.com`-style URL before touching DNS.
- After the CNAME is added, confirm the custom subdomain serves the app
  over HTTPS and the root domain's existing page is unaffected.
- Run `uv run pytest -q` and `cd web && npm test` — both green, matching
  this project's standing TDD/real-verification norms.
