# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`CONTEXT-MAP.md`** at the repo root: it points at one `CONTEXT.md` per context. Read each one relevant to the topic.
- **`docs/adr/`**: system-wide/cross-surface decisions. Also check `<context>/docs/adr/` for context-scoped decisions in the surface you're about to work in.

If any of these files don't exist, **proceed silently**. Don't flag their absence; don't suggest creating them upfront. The `/domain-modeling` skill (reached via `/grill-with-docs` and `/improve-codebase-architecture`) creates them lazily when terms or decisions actually get resolved.

## File structure

Multi-context repo (presence of `CONTEXT-MAP.md` at the root). This project is RigCheck/HDTTools: a tow-rig safety-check calculator shipped as several independent product surfaces, each with its own architecture and OCR-backend policy — see `Claude.md` and `NEXT_STEPS.md` for the current state of that split.

```
/
├── CONTEXT-MAP.md
├── docs/adr/                          ← system-wide/cross-surface decisions
├── android/
│   ├── CONTEXT.md                     ← native Kotlin/Compose app
│   └── docs/adr/
├── web/
│   ├── CONTEXT.md                     ← React + Vite + TS frontend
│   └── docs/adr/
├── src/hdttools/
│   ├── CONTEXT.md                     ← shared OCR/breakdown core, plus the FastAPI backend (src/hdttools/api/)
│   └── docs/adr/
├── streamlit_app/
│   ├── CONTEXT.md                     ← free public-service demo (Tesseract-only, permanently)
│   └── docs/adr/
└── workers/scan-proxy/
    ├── CONTEXT.md                     ← Cloudflare Worker gating paid Claude-vision scans
    └── docs/adr/
```

`src/hdttools/` is its own context (not folded into `web/`) because it's shared by both the Web backend and Streamlit — a decision or term recorded there applies to both consumers, not just one.

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in the relevant context's `CONTEXT.md`. Don't drift to synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal: either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/domain-modeling`).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0007 (event-sourced orders), but worth reopening because…_
