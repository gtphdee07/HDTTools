# Beta plan

Drafted 2026-10-22 for the owner to edit; ticket status updated 2026-10-23. It plans the first beta (a small invited group), what must be done before going live, and what can ship later as feature releases. Ticket numbers are GitHub issues in `gtphdee07/HDTTools`. "New" means no ticket exists yet. Check ticket state with `gh issue list` before relying on this page, because tickets change faster than this file.

## Decisions behind the plan (owner, 2026-10-22)

- **Payments in the beta:** test payments only. Web uses RevenueCat Web Billing sandbox and Android uses RevenueCat's Test Store. No real money moves, so Google Play Console, final pricing (#33) and the full legal review (#34) are not beta gates.
- **Android install:** a signed APK file sent to testers. No Play Store listing in the beta.
- **Testers:** fewer than 20 invited people. The Anthropic spend cap (#97) is a must-do; the per-account rate limit (#114) is a should-do.
- **Audits:** the refactor analysis and the security audit both run first as read-only reports. Findings become tickets. Only high and medium security findings, and refactors that block the beta, are fixed before it.

## Status on 2026-10-23

- **The Phase 1 build chain is finished.** All eight tickets are closed and pushed: #146, #29, #30, #20, #27, #101, #31 and #32 (closed 2026-10-22 and 2026-10-23, much faster than the sizing guess). The Supabase migrations for #29 (History) and #30 (plan caps) are applied and their live External suites passed. `supabase-auth`, `revenuecat-web-billing` and `anthropic` were re-run live after the last merges. `MPSkills` carries one unpushed run-sheet commit.
- **Filed 2026-10-23 (all `ready-for-agent`, not started):** the five Phase 1 tickets: #174 Android beta build, #175 Web release branch, #176 tester kit, #177 privacy notice and beta terms, #178 visibility (Worker logs and Android crashes). No audit has run, and #97 (the Anthropic spend cap) is open.
- **Done by you:** the upload keystore exists (wizard run 2026-10-23; file and notes in `G:\Secrets\rigcheck`) and an Android client for it was created in Google Cloud. You confirmed the checks on 2026-10-23: the password is in your password manager, a second copy of the file exists, and the Google client's SHA-1 matches the notes file. You also added the first testers as Google test users; add each new tester's Gmail the same way before inviting them.
- **New open tickets since the plan:** #169, #170, #171, #172, #173 (see "Tickets the chain left behind"). #166, #167 and #168 also closed since the plan was drafted.
- **Next step:** run the five new tickets, and start the read-only refactor analysis (Phase 2) beside them. #174 and #175 first: the tester guide (#176) needs the beta flag and the one Web address.

## What the beta must let a tester do

Sign up (email, and Google if #20 is in), use manual entry without an account, scan a truck tag, trailer tag and scale ticket, buy Pro and scan packs with test cards, and see the same Garage, History, Pro status and scan balance on Android and Web.

## Phase 1: build the beta product

Two lanes. They can build side by side; Android runs one ticket at a time because there is one emulator. Run each ticket with the steps on the run sheet ([agents/test-round-handoff.md](agents/test-round-handoff.md)).

| Lane | Tickets, in order | Beta need | Status |
|---|---|---|---|
| Web and server | #29 History sync on Web, #30 Pro raises the Garage and History caps | must | **done**, closed and pushed |
| Web and server | #20 Continue with Google on Web (Google only) | should | **done**, closed and pushed |
| Android | #146 prove the `pro` entitlement is attached, #27 Pro and credits carry across, #101 scan packs for Pro only, #31 synced Garage, #32 History | must (#101 is marked "do not release Android before it is done") | **done**, closed and pushed |

### Tickets the chain left behind

These were filed by the build sessions (all open, all `needs-triage`). My recommendation for the beta; you decide.

| Ticket | What | Recommendation |
|---|---|---|
| #169 | Android: delete a Rig from the synced Garage | **should.** A Free tester at the 5-Rig cap on Android cannot free a slot except on Web, a dead end. |
| #170 | Android: offer to import the Rigs saved on the phone on first sign-in | **should.** A tester who tries the app signed out, saves a Rig, then signs up sees that Rig vanish. Web already does this (#91). |
| #171 | External: cover Android's Supabase Garage client in the `supabase-tables` surface | **should, or cover it in the Phase 3 smoke test.** It is the only live proof that the Android Garage client agrees with the server. Free, no paid calls. |
| #172 | Web Release Back Log (running list; first item: show dates in the viewer's local time zone, not UTC) | **should.** Today an evening check can read as tomorrow on Web but as today on Android, so the same History entry differs between platforms. The list stays open until release. |
| #173 | Android History: add the filters Web has | **later** (labelled `future`). Not needed for a beta. |

### New tickets for Phase 1 (filed 2026-10-23)

1. **Android beta build (#174).** The release guard (#166) refuses a release build with the Test Store key, so a test-payments APK cannot be a normal release build. Add a signed beta build type that is allowed the test key, is not debuggable, and is clearly labelled. #166 stays for the real release.
2. **Release branch for Web (#175).** Cloudflare Pages publishes on every push to `MPSkills`. During the beta testers would see half-finished work. Decide on a release branch (for example `beta`) that you promote deliberately, and point the Pages production branch at it.
3. **Tester kit (#176).**
   - A script or wizard that grants a tester Pro and a number of scans in RevenueCat (see the #105 wizard for the pattern).
   - A one-page install and report-a-problem guide, built on [CreditCardTest.md](CreditCardTest.md).
   - A feedback link in both apps.
   - A "Beta: test payments" label in both apps.
4. **Privacy notice and beta terms (lightweight) (#177).** Split out of #34. Say what is stored (email, Rigs, History), that scale-ticket photos go to Anthropic, and that manual deletion is on request. The full legal review (#34) stays a pre-live item.
5. **Minimum visibility (#178).** Worker logs you can read and a decision on how to capture Android crashes from testers. The Anthropic usage alert below the cap is part of #97, not #178.

### Owner-only steps in Phase 1

- [ ] **#97:** set the Anthropic spend limit and an alert, and record the figure and date on the ticket.
- [x] Generate the Android **upload keystore**, keep it and its password outside the repo, and register its SHA-1 in the Google OAuth Android client (`bash scripts/wizard_android_upload_key.sh`; run 2026-10-23, files in `G:\Secrets\rigcheck`). Checks confirmed by you on 2026-10-23: the password is in your password manager, a second copy of the file exists, and the Google client `RigCheck-Android-beta` shows the SHA-1 from the notes file.
- [x] If the Google OAuth consent screen is in "Testing" mode, add each tester's Google account as a test user. Done for the first testers (2026-10-23); repeat for each tester added later.
- [ ] Choose how to protect Supabase: the paid tier, or a weekly keep-alive plus a manual export. The free tier pauses after 7 idle days and has no backups.
- [ ] Commit the sandbox Web key and offering id to `web/.env.production` (public values; see [BUILD_AND_DEPLOY.md](BUILD_AND_DEPLOY.md) section 3).
- [ ] Check the Supabase Redirect URLs allow-list (the unspecified "Pages preview hosts" entry from audit lead 3).
- [x] Apply the Supabase migration SQL that #29 and #30 produced (`20261022000000_history_entries.sql`, `20261023000000_plan_caps.sql`). Done; the live `supabase-tables` suite passed.

## Phase 2: refactor analysis and security audit

Start the read-only analysis now. Do the refactor work and the audit after the Phase 1 tickets have merged, so they look at the code testers get and do not collide with tickets in flight.

1. **Refactor analysis (read-only).** One pass per surface (Android, Web, Worker, Python and tooling), then one combined report. Look for oversized files and screens (for example the Android ViewModel and nav host), duplicated logic, dead code, and root clutter (`junit-*.xml`, `coverage.json`, the legacy `ARCHIVE_*.md`, `NEXT_STEPS.md` and `ClaudePlans/`). Every finding becomes a ticket with a severity. Only refactors that reduce security risk or block the beta are done before it.
2. **Security audit.** A full `standard` run with the security-audit skill across every surface, reading the run-1 and run-2 ledgers as prior coverage (notes in the Claude memory for run-2; output folder `C:\Users\Angela\security-audit-skill\HDTTools\`). This host cannot enforce the skill's sandbox, so it is source review, not live attack testing. Include the dashboard checklist: Supabase redirects and providers, Google consent screen, Cloudflare Worker and Pages settings, RevenueCat key permissions, and Anthropic key scope. Run-2 leads already fixed: lead 2 (Anthropic retries, #112), lead 5 (the Test Store key in a release build, #166) and lead 7 (ticket scripts trusting any STATUS author, #167). Leads still open as far as I can see: the Android `rigcheck://login` deep link, the Pages-site External test using the full environment, and the Supabase redirect check. The audit should also cover the code added since run-2: the History and plan-caps migrations, Google sign-in on Web, and the Android Garage and History clients. A hands-on test of the deployed Worker would be an owner-run script against a throwaway Worker.
3. **Fix pass.** All high and medium findings are fixed before the beta. Low findings go to the backlog.

## Phase 3: beta readiness

- [ ] Clean-device smoke test: a fresh Android install and a fresh Web account. Cover sign-up and email confirmation, password reset, manual check, a scan, a sandbox Pro purchase and a cancel, Garage and History sync between the two platforms, and sign-out.
- [ ] Run `uv run scripts/external_freshness.py`, then the stale External suites (paid calls only up to your ceiling).
- [ ] Push to the release branch, send the APK and the guide, and invite the testers.
- [ ] Record on #99 that #96 and #100 do not block the beta, then close #99 when its other children are closed.

## Before going live (after the beta)

| Area | Tickets and work |
|---|---|
| Money | #33 launch pricing (use the per-scan cost measured in the beta), #34 full legal and refund review |
| Android store release | Play Console account, production RevenueCat key, Play products and listing, Play app-signing SHA-1 in the Google OAuth client, **#40** Play Billing External tests |
| Play requirements (check the current policy) | a privacy-policy URL, the data-safety form, an in-app account-deletion path |
| Scan service safety | #114 rate limit (if not done for the beta), revisit #96 with the #100 findings |
| Web | swap the sandbox Web key for the live one; Google consent screen published |
| Accounts and data | Supabase on a paid plan |
| Audit | repeat the security audit on the release build |
| Operations | #72 scheduled drift canary, #138 Worker preview deploy, #145 fresh-clone setup check |

## Feature releases later

- #2 bumper-pull (tongue weight) support
- #13 paid Garage capacity upsell
- #14 fleet management (needs its own wayfinder effort)
- #77 Sign in with Apple, with the iOS app
- #173 Android History filters
- Tooling backlog, any time: #68, #69, #70 (epic close gate), #139, #144, #155 to #159 (static-check gaps), #165, #132

Containers stay as they are: #3, #15, #35, #49, #51, #99.

## Rough sizing

Estimates, in build sessions, not promises. The Android chain I called the long pole finished in about a day, so that guess was too high. What is left before Phase 2 is small: the five new Phase 1 tickets and the "should" tickets above (#169, #170, #171, #172), about 9 small sessions in total, some in parallel. The audit and fix pass are still estimated at about 1 to 2 weeks. Phase 3 is about 3 days. Re-estimate after the refactor analysis report, which is the first real unknown.
