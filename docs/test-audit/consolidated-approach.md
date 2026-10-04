# Consolidated test approach, per application

As of 2026-10-04, branch `MPSkills`, after #50, #60 and #61. Sources: `docs/test-audit/` (audit run the same day), `TESTING.md` and the per-context testing documents, ADR-0008, the planner, and the open GitHub issues. Test counts and coverage figures come from the audit; only the Python count (699 in a default run) was re-collected for this report.

**Legend.** *Today* means it exists and works now. *Planned #N* means an open ticket will add it; it does not exist yet. *No ticket* means a gap nobody has filed.

## The short answer

- **Nothing runs by itself today.** There is no CI, no GitHub workflow and no installed git hook (only `.sample` files). Every test run is started by you or by an agent working a ticket.
- **Yes, you currently have to run some tests by hand**, and the paid or device-dependent ones need you specifically: the Android device suite, the old Worker and Android live suites, and the coverage gate with refresh. These also deploy or spend, with no confirmation prompt yet (#62, #63).
- **Offline suites are cheap enough to be agent-run on every ticket**: Python about 35 s, Web about 7 s, Android JVM about 21 s, Scan Proxy under 1 s. The planner tells an agent which of these to run, but nothing makes an agent consult it (see gap U2).
- **The biggest holes:** a Web push deploys with no gate (#43), Android's logic is mostly covered only by device tests (#58), the golden-vector fixture can't catch a port that drifts (#55), and the first paid surface (Anthropic, #37) doesn't exist yet.

## Test types

| Type | What it checks | Needs |
|---|---|---|
| **Minor** (categories 1, 2) | One function, or functions sharing state inside one file. Fast, offline, faked collaborators. | nothing |
| **Major** (categories 3, 4) | A file's public interface and the interfaces between modules. Everything offline; unmarked tests count as Major. | nothing |
| **External** (category 5) | Real calls to a provider: Supabase, RevenueCat, Anthropic, the deployed Worker. Per-surface, run only when the surface is stale (a boundary file, pinned dependency or watched registry release changed since its last pass). | network, keys; some paid |
| **Old live suites** | Android weekly and Worker weekly/release. These sit alongside the External suites and keep their own scripts. They deploy the Worker and make paid scans. | network, keys, a device for Android |
| **Android instrumented** | UI and navigation on a device, offline (`connectedDebugAndroidTest`). | device or emulator |
| **Shared contract** | `test-vectors/breakdown_cases.json` drives the Python, Kotlin and TypeScript breakdown math from one fixture. | nothing |
| **Coverage gate** | Reports coverage per platform; fails below a baseline floor for Android, Python and Scan Proxy. | `--refresh` re-runs every suite, including Android's on a device |
| **Planner** | Prints which tests to run for a diff at the issue, session-end and release levels. Advisory, always exits 0. | nothing |

## Per application

"Who" is **Agent** (an agent can run it unprompted on a ticket), **You** (needs you: a device, a secret, a spend or a deploy decision) or **Auto** (fires with no one asking).

### Core (Python, `src/hdttools`)

| Test | Command | When | Who | Status |
|---|---|---|---|---|
| Minor | `uv run pytest -m "minor and core"` | every ticket | Agent | Today (marker split from #50) |
| Major | `uv run pytest -m core` | public interface or dependency changed | Agent | Today |
| Whole offline run | `uv run pytest` (about 699 tests, about 35 s; excludes live tests by default) | session end | Agent | Today |
| Live Anthropic test | `uv run pytest -m external` (3 tests, billed) | when you decide | You | Today; not yet in the surface manifest (#37) |
| Coverage | `uv run scripts/coverage_gate.py` (86%, floor 79%) | release time | You | Today, manual |

Core has no release of its own; it is covered through Streamlit, Android and Web.

### Streamlit

| Test | Command | When | Who | Status |
|---|---|---|---|---|
| Minor / Major | `-m "minor and streamlit"` (8) / `-m streamlit` | every ticket / interface change | Agent | Today |
| App tests (`AppTest`) | in the shared Python suite | session end | Agent | Today; the Disclaimer gate is not tested (#56) |

No release event, no External surface and no deploy check. The README describes running it locally; I did not find a documented deploy step.

### Web (`web/`)

| Test | Command | When | Who | Status |
|---|---|---|---|---|
| Offline suite (Minor and Major are not split) | `npm --prefix web test` (about 107 tests, 7 s, 95% lines) | every ticket | Agent | Today |
| File-level run | `npm --prefix web test -- <file>` | red-green loop | Agent | Today, but not yet a documented command (#52) |
| External: `supabase-auth` | `web/test-external.ps1` | when stale | You | Today |
| External: deployed site, Web billing, others | none | n/a | n/a | Planned #42 (Pages site); the Web billing surface appears only as a planned manifest entry (#53) |
| Freshness gate on push | pre-push hook | push that touches `web/` | Auto | **Planned #43; nothing today** |

Web deploys on push through Cloudflare's Git integration (`web/README.md`), so today a push deploys with no gate. Planned test additions: History, Disclaimer, Dashboard (#57).

### Android

| Test | Command | When | Who | Status |
|---|---|---|---|---|
| JVM tests | `android/gradlew -p android test` (38 tests, 21 s, 6.9% coverage) | every ticket and session end | Agent | Today, but shallow (#58 decides how to raise it) |
| Instrumented offline | `connectedDebugAndroidTest` | the diff touches `ui/` code, or at release | You (needs a device; you say one is usually available) | Today; the planner decides when |
| Old weekly suite | `android/test-weekly.ps1` | before a Play Store push | You | Today; **deploys the Worker and makes paid scans with no confirmation or call limit**. Guard planned in #63 |
| External: RevenueCat SDK, Play Billing | none | n/a | n/a | Planned #39, #40 |
| One-command release run | none | Play Store push | n/a | Planned #63 |
| Coverage gate | `coverage_gate.py` (gated 71% is device-only) | release | You | Today |

### Scan Proxy (Cloudflare Worker)

| Test | Command | When | Who | Status |
|---|---|---|---|---|
| Minor | `npm --prefix workers/scan-proxy run test:sanity` | every ticket | Agent | Today |
| Major | `npm --prefix workers/scan-proxy test` (57 tests, under 1 s, 100% lines) | interface change, session end | Agent | Today |
| External: `revenuecat-rest` | `workers/scan-proxy/test-external.ps1` | when stale | You | Today; free |
| Old weekly and release suites | `test-weekly.ps1`, `test-release.ps1` | before a Worker deploy | You | Today; **deploy, then spend, with no confirmation or call counter**. Guard and one-command run planned in #62 |
| External: Anthropic, deployed Worker | none | n/a | n/a | Planned #37, #41 |
| Freshness gate on deploy | none | `wrangler deploy` | n/a | Planned #43 |
| Account-token tests | none | n/a | n/a | Planned with #21 and #23 |

The non-Python commands in the table are the planner's provisional choices until #52 documents the real ones.

## Do you need to run tests manually?

**Today, yes, for:**
1. The External suites (`web/test-external.ps1`, `workers/scan-proxy/test-external.ps1`), whenever the planner or freshness script says a surface is stale.
2. Android instrumented tests and the old Android weekly suite before a Play Store push.
3. The old Worker weekly/release suites before a deploy.
4. The coverage gate with `--refresh`.
5. The planner itself, or telling an agent to run it. The pre-push freshness gate (#43) is the only planned automation.

**Not needed by hand today:** the offline suites for all five contexts. An agent can run them on every ticket.

**After the planned tickets:** the Web gate is automatic on push (#43). Everything else stays on-request, but release becomes one command per releasable context with a confirmation and a call limit (#62, #63).

## Gaps

### Planned (open tickets)

| Gap | Ticket |
|---|---|
| Per-context file/context commands for Web, Scan Proxy, Android | #52 |
| Missing providers and watched packages in the manifest | #53, #54 |
| Golden vector over-limit cases and text assertions; unknown capability fails loudly | #55 |
| Streamlit Disclaimer gate and other app paths | #56 |
| Web History, Disclaimer, Dashboard tests | #57 |
| Android JVM coverage (decision), dead dependencies and undeployed API tests (decision) | #58, #59 |
| Paid-call counter and confirmation; Worker and Android release commands | #62, #63 |
| Pre-push freshness gate; Worker deploy and Android release checks | #43 |
| Per-surface External suites: Anthropic, RevenueCat REST, RevenueCat SDK, Play Billing, Worker, Pages | #37 to #42 |
| Per-surface dashboard | #44 |
| Stale testing documents | #64 |
| Tests for new features: GCWR (#45 to #47), pin-weight wording (#48), account token verification (#21, #23) | feature tickets |
| Web Billing cancel/dismiss pre-ship check (a human checklist) | #11 |

### Not planned (no ticket)

| # | Gap | Why it matters |
|---|---|---|
| U1 | **No automatic offline run anywhere.** #43 gates only the External freshness check on a push. Nothing runs the offline suites on commit or push, and nothing runs in CI. | A broken offline suite is found only if someone runs it. |
| U2 | **Nothing makes agents use the planner.** `CLAUDE.md` does not tell agents to run it or what to do with its output. #64 only adds links in the documents. | The planner is advisory, so unused it changes nothing. |
| U3 | **The #43 gate is bypassable and covers only some pushes.** `--no-verify` skips it by design; it is local, so a push from another machine or an edit made on GitHub deploys Web unchecked. | Web's deploy path is a plain git push. |
| U4 | **Streamlit has no release or deploy check** and no External surface. | Nothing verifies the app as shipped. |
| U5 | **The stale-paid-surface rule is untested against real data** until #37 lands, and the old paid suites are hard-coded as confirm-only in the planner config. | If #37's manifest entry is wrong, the planner prints the wrong action. |
| U6 | **No end-to-end test of the deployed apps on real hardware** (Play Store internal track, a browser against production). #42 only checks the Pages site loads and has the right environment values. | Real purchase, sign-in and scan flows are only checked by hand. |
| U7 | **No cross-platform contract test for synced Garage/History or the account flow** (#20 to #32 each carry their own tests; I found none that guards the shared shape across Web and Android, as the golden vectors do for the math). Judgement call. | Two ports of the same data model can drift. |
| U8 | **No numeric coverage targets** (rule 9: you set them after seeing numbers). | The gate floors are baselines, not goals. |
| U9 | **Release timing is manual.** Nothing reminds you to run the Android or Worker release set. | A Play Store push can happen without it, until #63 and #43. |

## Questions for you

1. Which branch does Cloudflare Pages deploy from? If it is not `MPSkills`, the planned hook only matters when you push that branch (#43 targets `MPSkills`).
2. Is Streamlit hosted anywhere (a public URL) or run only locally? That decides whether U4 matters.
3. Do you want a small ticket for U2 (agent instruction to run the planner) and one for U1 (an offline-suite hook or CI)?
