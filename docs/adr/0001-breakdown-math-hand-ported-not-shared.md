# Hand-port breakdown/verdict math to Kotlin instead of sharing the Python implementation

**Status: amended by [ADR-0007](0007-static-web-on-cloudflare-pages-with-typescript-breakdown-port.md) (2026-10-02)** — the golden-vector fixture, not Python, is now the source of truth, and Web gets a TypeScript port too.

Android needs to compute the same weight-breakdown/verdict math as Core (`compute_breakdown`/`verdict_for`). Embedding a Python runtime in the Android app (e.g. via Chaquopy) was considered and rejected for app size, build complexity, and native-toolchain risk. Instead, the logic is hand-ported into Kotlin (`BreakdownTest.kt`/`VerdictTest.kt` and their implementations), accepting duplicate-maintenance risk in exchange for a normal native app. That risk is mitigated by `test-vectors/breakdown_cases.json`, a shared golden-vector fixture both platforms test against, so the two implementations can't silently drift apart undetected.
