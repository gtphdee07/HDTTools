# Context Map

## Contexts

- [Core](./src/hdttools/CONTEXT.md): shared OCR extraction and breakdown/verdict computation (the tow-rig safety-check math), plus the FastAPI backend that serves it to Web
- [Android](./android/CONTEXT.md): native Kotlin/Compose app — the Disclaimer gate; shares Core/Web's Rig/Breakdown/Verdict shape independently, see Relationships below
- [Web](./web/CONTEXT.md): React + Vite + TS frontend — the guided Wizard flow, Rig/History/Dashboard concepts
- [Streamlit](./streamlit_app/CONTEXT.md): free public-service demo, permanently Tesseract-only (ADR-0002) — no accounts, credits, or paywall
- [Scan Proxy](./workers/scan-proxy/CONTEXT.md): Cloudflare Worker gating paid Claude-vision scans — Scan/Scan Credit/Spend/Refund vocabulary, and the reserved meaning of "Entitlement"

## Relationships

- **Core ↔ Android**: Android hand-ports Core's breakdown/verdict math into Kotlin (Python is the source of truth); both are tested against the same shared golden-vector fixture, `test-vectors/breakdown_cases.json`.
- **Core ↔ Web**: Web's FastAPI backend lives inside Core (`src/hdttools/api/`) and calls Core's OCR/breakdown logic directly.
- **Core ↔ Streamlit**: Streamlit imports Core's OCR modules directly in-process; no network boundary between them.
- **Scan Proxy ↔ Android**: Scan Proxy gates Android's paid Claude-vision scans behind a RevenueCat purchase check.
- **Web ↔ Android (Rig)**: both maintain their own independent "Rig" concept (a saved, named truck+trailer pairing) — not a Core concept, and not (yet) shared/synced between the two platforms.
- **Web ↔ Android ↔ Streamlit (Disclaimer)**: all three independently implement a session-scoped "Disclaimer" acknowledgment gate before showing results, each with its own wording and no shared implementation or synced acknowledgment state.
