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
- **Core ↔ Scan Proxy (Claude vision)**: the Python readers and the Worker's `docTypes.ts` call Claude separately, so they are two External surfaces (`anthropic-python`, `anthropic`) checked against the same golden data: `test-vectors/vision_external_cases.json` (which photo per doc type, and which `ExampleDocs/golden_fields.json` entry holds its expected values) and `test-vectors/vision_tool_schemas.json` (tool name and schema property names per doc type), each side's free offline test pinning its own half. A third shared file, `test-vectors/scan_form_fields.json`, sits beside `vision_tool_schemas.json`: per doc type, the fields every surface's review form shows (`scanned` ones a Scan can fill, `manual_only` ones it never returns) with a `text` or `number` type each; Streamlit, Web and Android each check their own form against it.
- **Scan Proxy ↔ Web ↔ Android (Scan outcomes)**: what each client tells the user when a Scan does not deliver, and its retry rules, are defined once in Scan Proxy's "Scan outcomes" entry and pinned by the shared fixture `test-vectors/scan_outcomes.json`, which Web (`web/src/scanOutcomes.test.ts`) and Android (`ScanOutcomesFixtureTest.kt`) each check; each client keeps its own strings.
- **Web ↔ Android (Rig)**: both maintain their own independent "Rig" concept (a saved, named truck+trailer pairing) — not a Core concept. The signed-in Garage is account-synced via Supabase (ADR-0005) on both: Web's and Android's read and write the same `garage_rigs` table, so a Rig added on one appears on the other. Android keeps a Rig's truck and trailer in its own field names, mapped to Web's in `GarageWire.kt`.
- **Web ↔ Android ↔ Streamlit (Disclaimer)**: all three independently implement a session-scoped "Disclaimer" acknowledgment gate before showing results, each with its own wording and no shared implementation or synced acknowledgment state.
