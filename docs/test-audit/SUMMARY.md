# Test audit: cross-product summary

Audit run 2026-10-04 against `docs/test-audit/rules.md` (map issue #49). One report per context: [web](web.md), [android](android.md), [streamlit](streamlit.md), [core](core.md), [scan-proxy](scan-proxy.md). This page compares them; the detail and the suggested tickets are in each report. Figures come from the agents' runs; no live or paid test was run by the agents.

## State at a glance

| Context | Offline suite | Measured coverage | Worst gap |
|---|---|---|---|
| Web | 107 tests, ~7 s | 95% lines, 87% branches | External covers only `supabase-auth`; other Web surfaces not even listed as planned |
| Android | 38 JVM tests, ~21 s (`./gradlew test --offline`) | 6.9% JVM-only; gated 71% is device-only | Most logic is covered only by device tests |
| Streamlit | 8 `AppTest` tests (of 645 in the shared suite) | 81% for `streamlit_app/` | Disclaimer gate never checked for hiding Results |
| Core | 645 passed, 4 xfailed, ~33 s | 86% for `src/hdttools`; gate floor 79% | Golden vectors have no over-limit cases for four rows and assert no text |
| Scan Proxy | 57 tests, ~0.4 s | 100% | No test anticipates account-token verification (#21, #23) |

## Patterns across all five

1. **Minor and Major cannot be run separately in Python.** Core and Streamlit share one suite with no markers or `conftest`, so there is no Minor-only run and no per-context command. Scan Proxy and Web have a context command but no file-level one. Android has one JVM command and no wrapper.
2. **Bare `pytest` spends money.** `ANTHROPIC_API_KEY` is set in the shell, and `tests/test_claude_vision_external.py` skips only when it is unset. `coverage_gate.py` and `generate_dashboard.py` both run bare `pytest`, so a gate run or dashboard regeneration can make billed calls.
3. **The old External suites are ungated and some deploy or spend.** `android/test-weekly.ps1` deploys the Worker and makes paid scans with no confirmation or call counter. `npm run test:weekly` deploys before it runs. Neither feeds the freshness record.
4. **The ADR-0008 gate is not installed.** No pre-push hook exists (only `.sample` files). That is #43.
5. **The watched-dependency manifest is thin.** Only `revenuecat-rest` and `supabase-auth` exist. Missing: Anthropic, Cloudflare tooling (`wrangler`, `workerd`, `@cloudflare/workers-types`), `@revenuecat/purchases-js`, Pillow, Pytesseract, FastAPI, Streamlit, and Android's Maven dependencies. The freshness script fetches npm only; Maven Central has per-version dates for `purchases`, but Google Maven's metadata for `billing` has none.
6. **Shared contracts are weakly guarded.** The golden-vector fixture (14 cases) drives all three ports, but it never exercises several over-limit rows and asserts no note, badge, headline or subline text. Android's runner silently skips any case needing an unknown capability. #45 to #48 change this math and nothing would catch a port left behind.
7. **Documentation has drifted.** `tests/TESTING.md` (says 156 tests, about 649 now), `web/TESTING.md` (says 71, omits three areas), `android/TESTING.md` and `workers/scan-proxy/TESTING.md` (lists three gaps as open that are fixed) are all stale.
8. **Possible dead weight.** `easyocr`, `opencv-python-headless` and `pyzbar` in `pyproject.toml`; `api/main.py`, `schemas.py` and 17 tests guard an undeployed endpoint; `apiShape.test.ts` guards a Web response shape Web no longer calls.

## Incremental complexity today (cheapest to most expensive)

| Step | Command (cost) | Exists as one command? |
|---|---|---|
| Scan Proxy offline | `npm test` in `workers/scan-proxy` (<1 s, free) | yes |
| Web offline | `npm test` in `web` (~7 s, free) | yes |
| Python offline (Core + Streamlit) | `uv run pytest` with the Anthropic key unset and the live file excluded (~35 s, free) | only with manual care |
| Android JVM | `./gradlew test --offline` in `android` (~21 s, free) | yes |
| Per-surface External | `test-external.ps1` in `web` or `workers/scan-proxy` (seconds, free for the two live surfaces) | yes, stale-only |
| Old Worker/RevenueCat live suites | `test-release.ps1`, `test-weekly.ps1` (deploys, paid) | three separate scripts |
| Android device suite | `android/test-weekly.ps1` (device needed, deploys, paid) | yes, no gate or counter |

## Rule fit

| Rule | Status |
|---|---|
| 1. Scope ladder file / context / app | File level exists only for Python and (via `vitest related`) Web; context level is one command only for Web, Scan Proxy and Android JVM; the Python context split does not exist |
| 2. Per-issue Minor/Major | Only Scan Proxy has a Minor tag (`[sanity]`); Python and Web have none; Android has none |
| 3. Session-end whole run | Possible per context except Python's context split; Android JVM is cheap but shallow (6.9%) |
| 4. Release full run | Android and Worker: no single command, no confirmation or call limit |
| 5. Web freshness gate | Not installed |

## Decisions the findings raise

1. **Android coverage meaning.** Either grow JVM coverage by moving logic out of device-only tests, or accept device tests at session end for Android.
2. **Python markers.** Introduce markers (`minor`, `streamlit`, `external`) and a safe default that never runs live tests.
3. **Old suites.** Add confirmation and a call counter to the paid Android and Worker scripts, and decide which become part of a release command.
4. **Docs.** Refresh each `TESTING.md`, or replace them with the approach we agree.
5. **Tickets.** Fold the five reports' suggested tickets into #37 to #44, the feature tickets and a few new ones.
