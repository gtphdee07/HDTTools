# External API tests are per surface, run only when stale, and gate releases

Decided 2026-10-02 (grilling session on the External test suite). Extends the External category in the root `TESTING.md` (category 5), which already says nothing internal can prove a provider's behaviour is unchanged, but gave no way to know *when* to re-check, no coverage for Web, and no enforcement.

RigCheck depends on several remote interfaces: Anthropic, RevenueCat (REST, Android SDK, later Web Billing), Google Play Billing, Supabase Auth (later tables), the deployed scan Worker, and the deployed Pages site. The goal is to detect that a remote interface changed, and look at our code, before it breaks on an edge case. This is not mission-critical software, so the signal for "the remote changed" is deliberately cheap and imperfect: **package-registry release dates** (npm, PyPI, Maven). A provider that changes its web API without publishing a library release is out of scope.

## Decision

- **Unit of freshness is a surface**, not a platform+suite. A surface is one provider interface (e.g. `anthropic`, `revenuecat-rest`, `supabase-auth`, `pages-site`). Each has its own last-pass record.
- **One shared script and manifest.** `scripts/external_freshness.py` (run with `uv`) reads a JSON manifest mapping each surface to its boundary files, its dependency pins, the registry packages to watch, its maximum paid calls, and the surfaces each releasable platform depends on. Platform wrappers call it; the logic exists once.
- **A surface is stale** when either (a) a commit since its last pass touched its boundary files or dependency pins, or (b) any watched package has a stable (non-pre-release) version published after its last pass, whether or not we upgraded. If a registry cannot be reached, the surface is treated as stale.
- **Tests carry a surface tag** (name tag for `node --test`, marker for pytest, annotation for Android). The script prints the stale surfaces; each wrapper passes the list to its runner's native filter. Each platform keeps owning its own External suite; there is no cross-platform orchestrator.
- **Depth, per surface:** reachable and authenticated; response shape matches our contract; error contracts; full user journeys, all with real calls and dedicated test accounts.
- **Missing secrets, accounts or devices fail the run.** An explicit skip flag records `skipped`, never advances the surface's timestamp, and leaves it stale.
- **Cost control.** Each paid surface declares a maximum call count in the manifest and a shared counter aborts the run when exceeded. Anthropic tests use a dedicated API key in a spend-capped workspace. Target under $0.50 per full run.
- **Recording.** `scripts/record_external_result.py` records, per surface: pass or fail, timestamp, the registry versions seen, and our commit SHA. The old `platform/suite` entries are kept as history but ignored by the gate, so every surface starts stale until a real run.
- **Gate.** A git pre-push hook on `MPSkills` (Pages' production branch), the Worker deploy wrapper and the Android release step each run the freshness check. A release requires every surface in its dependency chain to be fresh, so Android's gate includes the Worker's surfaces. The hook only reads recorded status and the registries; it never runs live tests. It only gates a push whose diff touches `web/`, `workers/scan-proxy/` or `android/`. An unreachable registry blocks. `--force` requires a reason, which is logged and shown on the dashboard as an overridden gate until the next real pass.
- **Planned surfaces** (Web Billing SDK, Supabase Garage/History tables, Worker token verification) are listed in the manifest as `planned`: shown on the dashboard as not covered, never blocking. Each feature ticket adds its surface's tests and flips it to active as part of its acceptance.
- **Supabase test user** is created once by hand through `scripts/wizard_web_external_test_user.sh`; its credentials live in the gitignored `web/.env.local`.

## Considered options

- **One orchestrated cross-platform suite**: rejected. Each platform already owns its External tests and tooling (node, pytest, Android instrumentation); a new orchestrator would duplicate them.
- **Scraping provider changelog pages** for server-side API changes: rejected. It would catch more, but there is no stable API, so it needs a brittle parser per provider, which is more upkeep than this project warrants.
- **A fixed age limit (re-run every N days)**: rejected in favour of event-based freshness, consistent with the "Event-based tiers, not time-cadence tiers" rule in `TESTING.md`.
- **Only releases newer than our pinned version count as a remote change**: rejected. It would ignore drift behind versions we adopted without a re-test.
- **Skip-and-record-pass on missing secrets**: rejected. The dashboard would show green for surfaces never exercised.
- **Cost cap by convention only, or by measured token spend**: rejected. Convention allows a silent retry-loop overspend; price tables are themselves a drift risk.

## Consequences

- `TESTING.md` category 5 and `scripts/dashboard_data/external_status.json`'s shape change when this is built; the dashboard gains per-surface rows.
- Existing scan-proxy and Android External suites need surface tags added, and each must be reviewed against the four depths above.
- A package-registry release is only a proxy: a server-side change with no library release goes undetected, by design.
- The pre-push hook is bypassable with `--no-verify`. That is a deliberate act, not an accident.
- Registry data must be cached or rate-aware if the hook runs on every qualifying push.
