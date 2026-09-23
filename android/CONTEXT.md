# Android

The native Kotlin/Compose app: manual-entry-first, with an optional paid Claude-vision Scan (see Scan Proxy's `CONTEXT.md`) for any of the three documents.

Android's `Rig`/`Breakdown`/`Item`/`Tone`/`Verdict` model mirrors Core/Web's shape exactly (`RecentRig.kt`, `BreakdownItem.kt`, `Tone.kt`, `VerdictInfo.kt`) but is its own independent implementation, not a shared library — see `CONTEXT-MAP.md`'s Relationships and ADR-0001. Definitions for those terms live in `src/hdttools/CONTEXT.md`; this file only covers what's genuinely Android-specific.

## Language

**Disclaimer**:
A blocking, once-per-app-session acknowledgment ("Experimental Tool — Not for Safety Decisions") shown before the first Results screen. Session/process-scoped only — never persisted, so it re-appears every app launch. Android's wording is deliberately its own, not shared with Web/Streamlit (see `CONTEXT-MAP.md`'s Relationships — each platform independently implements this gate), because the original text assumed OCR'd photos and Android defaults to manual entry.

**Entry Module**:
Which of the three documents (Truck Tag, Trailer Tag, or Scale Ticket) a given screen is currently collecting data for — the app's own routing/UI concept, not a Core concept.

## Open question, not yet a term

`ANDROID_DESIGN_BRIEF.md` describes a future two-tier purchase model (a "lifetime unlock" with preset credits, plus separate consumable "credit packs"), but `PaywallScreen.kt` today just lists whatever RevenueCat's current `Offering` returns, with no such distinction in code. Don't treat "lifetime unlock"/"credit pack" as established vocabulary until that's actually built — pricing/packaging is explicitly still undecided.
