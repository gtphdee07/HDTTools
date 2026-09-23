# Streamlit

A free, public-service demo of the same tow-rig safety check as Web/Android — self-contained, no separate backend process, no accounts or credits. Permanently scoped to Tesseract OCR rather than Claude vision; see ADR-0002.

Streamlit's own `Rig` and `Disclaimer` concepts mirror Web/Android's shape but are independently implemented (own session-state persistence, own disclaimer wording) — see `CONTEXT-MAP.md`'s Relationships and `web/CONTEXT.md`/`android/CONTEXT.md` for the fuller definitions. Nothing Streamlit-specific to add beyond that: it has no Wizard/History/Dashboard split, no Scan/Scan Credit/Entitlement concepts, and no paywall — it's a single self-contained flow with no paid features anywhere in it.
