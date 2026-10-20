# Context Map

## Contexts

- [Core](./src/hdttools/CONTEXT.md): shared OCR extraction and breakdown/verdict computation (the tow-rig safety-check math; `src/hdttools/breakdown.py` is the Python reference for it)
- [Android](./android/CONTEXT.md): native Kotlin/Compose app — the Disclaimer gate; shares Core/Web's Rig/Breakdown/Verdict shape independently, see Relationships below
- [Web](./web/CONTEXT.md): React + Vite + TS frontend — the guided Wizard flow, Rig/History/Dashboard concepts
- [Streamlit](./streamlit_app/CONTEXT.md): free public-service demo, permanently Tesseract-only (ADR-0002) — no accounts, credits, or paywall
- [Scan Proxy](./workers/scan-proxy/CONTEXT.md): Cloudflare Worker gating paid Claude-vision scans — Scan/Scan Credit/Spend/Refund vocabulary, and the reserved meaning of "Entitlement"

## Relationships

- **Core ↔ Android**: Android hand-ports Core's breakdown/verdict math into Kotlin (Python is the source of truth); both are tested against the same shared golden-vector fixture, `test-vectors/breakdown_cases.json`.
- **Core ↔ Web**: no runtime link. Web is a static app on Cloudflare Pages with its own TypeScript port of the breakdown math, tested against the same golden-vector fixture (`test-vectors/breakdown_cases.json`); the FastAPI app that once served it was removed (ADR-0007, #135).
- **Core ↔ Streamlit**: Streamlit imports Core's OCR modules directly in-process; no network boundary between them.
- **Scan Proxy ↔ Android**: Scan Proxy gates Android's paid Claude-vision scans behind a RevenueCat purchase check.
- **Scan Proxy ↔ Web ↔ Android (Scan outcomes)**: what each client tells the user when a Scan does not deliver, and its retry rules, are defined once in Scan Proxy's "Scan outcomes" entry and pinned by the shared fixture `test-vectors/scan_outcomes.json`, which Web (`web/src/scanOutcomes.test.ts`) and Android (`ScanOutcomesFixtureTest.kt`) each check; each client keeps its own strings.
- **Web ↔ Android (Rig)**: both maintain their own independent "Rig" concept (a saved, named truck+trailer pairing) — not a Core concept. Web's signed-in Garage is account-synced via Supabase (ADR-0005); Android's sync is not built yet.
- **Web ↔ Android ↔ Streamlit (Disclaimer)**: all three independently implement a session-scoped "Disclaimer" acknowledgment gate before showing results, each with its own wording and no shared implementation or synced acknowledgment state.
