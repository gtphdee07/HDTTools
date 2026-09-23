# Context Map

## Contexts

- [Core](./src/hdttools/CONTEXT.md): shared OCR extraction and breakdown/verdict computation (the tow-rig safety-check math), plus the FastAPI backend that serves it to Web
- Android (`./android/`): native Kotlin/Compose app — not yet modeled
- [Web](./web/CONTEXT.md): React + Vite + TS frontend — the guided Wizard flow, Rig/History/Dashboard concepts
- Streamlit (`./streamlit_app/`): free public-service demo — not yet modeled
- [Scan Proxy](./workers/scan-proxy/CONTEXT.md): Cloudflare Worker gating paid Claude-vision scans — Scan/Scan Credit/Spend/Refund vocabulary, and the reserved meaning of "Entitlement"

## Relationships

- **Core ↔ Android**: Android hand-ports Core's breakdown/verdict math into Kotlin (Python is the source of truth); both are tested against the same shared golden-vector fixture, `test-vectors/breakdown_cases.json`.
- **Core ↔ Web**: Web's FastAPI backend lives inside Core (`src/hdttools/api/`) and calls Core's OCR/breakdown logic directly.
- **Core ↔ Streamlit**: Streamlit imports Core's OCR modules directly in-process; no network boundary between them.
- **Scan Proxy ↔ Android**: Scan Proxy gates Android's paid Claude-vision scans behind a RevenueCat purchase check.
- **Web ↔ Android (Rig)**: both maintain their own independent "Rig" concept (a saved, named truck+trailer pairing) — not a Core concept, and not (yet) shared/synced between the two platforms.
