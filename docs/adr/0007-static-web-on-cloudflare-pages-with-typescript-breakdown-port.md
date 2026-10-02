# Web ships as a static app on Cloudflare Pages, with the breakdown math ported to TypeScript

Decided 2026-10-02 (wayfinder ticket [#8](https://github.com/gtphdee07/HDTTools/issues/8), part of map [#3](https://github.com/gtphdee07/HDTTools/issues/3)). Overrides the hosting research's Render recommendation (`ClaudePlans/2026-09-21-research-web-hosting-and-entitlement-tradeoffs.md`, Option A), which assumed a Python backend running Tesseract.

That assumption no longer holds. Web scanning goes through the shared Worker ([ADR-0003](0003-revenuecat-everywhere-plus-unified-scan-gating.md)) and Tesseract leaves the Web path, so the only thing left for a Python backend to do is one stateless endpoint, `/api/breakdown`. The owner also ruled out sleeping free container tiers (30-60s cold start on the first call after a quiet spell). Rather than pay for an always-on container to run one pure function, the math is ported to TypeScript, the same pattern [ADR-0001](0001-breakdown-math-hand-ported-not-shared.md) used for Android. Web becomes fully static, hosted on **Cloudflare Pages** (free, push-to-deploy, same vendor as `scan-proxy`), with no container host, no cold start and no backend CORS to own. The manual-entry free tier can work offline.

**The reference point is redefined.** The language-neutral golden-vector fixture (`test-vectors/*.json`) is the source of truth, not Python. Python, Kotlin and TypeScript (and later Swift for iOS) are all implementations tested against it. The port must add fixture cases for rounding edges, notably Python's round-half-to-even versus JavaScript's `Math.round`.

Python is not removed: Streamlit imports Core's math directly and stays on it (ADR-0002). The FastAPI app is simply no longer part of the Web deployment.

## Considered options

- **Render free tier + Python backend** (the research's recommendation): rejected. It cold-starts after 15 idle minutes, which the owner ruled unacceptable.
- **Always-on container (Render Starter, about $7/month) or Cloud Run**: rejected. Paying for an always-on service to run one stateless function is worse than a one-time port.
- **Netlify, Vercel or GitHub Pages for the static app**: rejected. Equivalent for static files, but Cloudflare Pages shares a vendor with `scan-proxy`.
- **Cloudflare Python Workers for the math**: not pursued. Pyodide-based and unproven for this, and a TypeScript port needs no runtime at all.

## Consequences

- ADR-0001's "Python is the source of truth" wording is superseded by the fixture-as-reference rule above.
- `web/src/api.ts` loses its `/api/breakdown` call and its hardcoded `localhost:8000` base URL; it keeps the call to the shared Worker for scans.
- `CONTEXT-MAP.md`'s "Core <-> Web" relationship (Web's FastAPI backend lives inside Core) becomes stale when this is built, and should be updated then.
- Free-tier Supabase pausing (ADR-0004) is now the only cold-start-like risk on Web, and only affects accounts, not the free calculator.
