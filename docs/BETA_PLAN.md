# Release plan: Alpha, fixes and audits, Beta, production

Drafted 2026-10-22 as a beta plan; restructured 2026-10-23 into four stages after the owner added an Alpha round. The file keeps its name because tickets #174 to #178 link to it. Ticket numbers are GitHub issues in `gtphdee07/HDTTools`. Check ticket state with `gh issue list` before relying on this page, because tickets change faster than this file.

## The stages

| Stage | Who tests | Goal | Starts when | Ends when |
|---|---|---|---|---|
| **1. Alpha** | up to 5 tech-savvy people | Get Web and Android into testable shape and collect rough feedback | the Alpha tickets below are merged and pushed, the APK is built, testers are invited | the owner calls it (open-ended) |
| **2. Fix and audit** | nobody new | Fix what Alpha found, then run the refactor analysis and the security audit, fix what they find, and finish the Beta prep tickets | Alpha ends | Beta-ready checklist is done |
| **3. Beta** | a larger invited group (under 20 unless the owner changes it) | Check the fixed product with more people and more devices | stage 2 is done | the owner decides to release |
| **4. Release** | the public | Real payments, store listing, legal, production keys | Beta ends | live |

Rule (owner, 2026-10-23): tickets labelled `enhancement` or `future` wait until after the production release.

## Decisions behind the plan (owner)

- **Payments in Alpha and Beta:** test payments only. Web uses RevenueCat Web Billing sandbox and Android uses RevenueCat's Test Store. No real money moves, so Google Play Console, final pricing (#33) and the full legal review (#34) gate the Release, not Alpha or Beta.
- **Android install:** a signed APK file sent to testers. No Play Store listing before Release.
- **Alpha size:** at most 5 tech-savvy testers. **Beta size:** under 20 invited people.
- **Alpha scope (2026-10-23):** #174, #176 and #178 (split into #180 to #184) plus the small fixes #169 and #179 (from #172). #175 and #177 move to the Beta prep.
- **Alpha end:** open-ended; the owner calls it.
- **Audits:** the refactor analysis and the security audit both run after Alpha as read-only reports first; findings become tickets. Only high and medium security findings, and refactors that reduce risk or block the Beta, are done before Beta.
- **Supabase:** stay on the Free plan for Alpha; upgrade to Pro ($25 a month: no inactivity pause, daily backups kept 7 days) before the Beta widens, and before Release.
- **Anthropic spend:** $30 a month limit with an alarm at $15 (#97, closed 2026-10-23). Five Alpha testers at 20 scans each cost under $2 in the worst case.

## Status on 2026-10-23

- **The shared-accounts build chain is finished.** #146, #29, #30, #20, #27, #101, #31 and #32 are closed and pushed. The Supabase migrations for History (#29) and plan caps (#30) are applied and their live External suites passed.
- **Done by you:** the Android upload keystore (files and notes in `G:\Secrets\rigcheck`, backed up, SHA-1 registered in Google Cloud), the first testers listed as Google test users, the sandbox Web key committed and live (Pro bought with a fresh test account on the live site), the Supabase Redirect URLs checked, the Supabase plan decided, and the Anthropic spend limit set.
- **Filed, not started:** #174 Android beta build, #175 Web release branch, #176 tester kit, #177 privacy notice and terms, #178 visibility (Worker logs and Android crashes). Their titles say "beta"; they serve both rounds.
- **Not run yet:** the refactor analysis and the security audit.
- **`MPSkills`** is pushed up to the shared-accounts chain (04490db). On 2026-10-23 #176 and #178 were split by surface and #172's first item became #179, so two worker sessions can run the Alpha tickets in parallel; see the run sheet.

## Stage 1: Alpha

### Tickets to finish before inviting anyone

| Round | Lane A: Android (one emulator, serial) | Lane B: Web, Worker, tooling |
|---|---|---|
| 1 | **#174** signed `beta` APK build | **#179** Web dates in the viewer's local time (from #172) |
| 2 | **#169** delete a Rig on Android | **#181** Web feedback link, "Beta: test payments" label and tester guide (from #176) |
| 3 | **#182** Android feedback link and label (from #176; waits for #174 and #181) | **#180** grant tool (from #176) |
| 4 | **#184** Android crash capture (from #178; waits for #182) | **#183** Worker log lines (from #178) |
| 5 | **#188** a test tag on every Android UI element (redesign epic #187, test tooling; after #169, #182 and #184 so their controls are tagged) | |
| 6 | **#189** baseline screenshots and measured bounds (redesign epic #187; needs the emulator alone) | |

Owner decision, 2026-10-27: #188 and #189 are in the Alpha round and the first tester APK is built after #189 has merged. The re-skin children of #187 (#191 to #197) stay `future` and wait until after production; #190 (the design round) is the owner's to start whenever they choose.

#176 and #178 are now containers; #172 stays open for later Web items. The decisions (build type `beta`, `versionCode` by hand, feedback by email to WTIAppDev@gmail.com, Pro plus 20 scans, crash report saved and sent on the next launch only if the tester agrees, no account id in Worker logs) are recorded on the tickets.

Android tickets run one at a time because there is one emulator; lane B has no Gradle and runs beside lane A. The Worker change in #183 means the owner redeploys the Worker (`npm run deploy`) and the External run described in `TESTING.md` precedes the push. Run each ticket with the steps on the run sheet ([agents/test-round-handoff.md](agents/test-round-handoff.md)); `/ticket-merge` reviews each.

### Owner steps for Alpha

- [x] Feedback goes to WTIAppDev@gmail.com (an email address, not a form), so there is no form to create.
- [ ] Add each Alpha tester's Gmail as a Google test user (consent screen in Testing mode), up to 5.
- [ ] Build the APK on your machine with the signing values in `gradle.properties` in your Gradle user home (the `GRADLE_USER_HOME` folder; on this machine `G:\GradleUserHome\gradle.properties`, not `C:\Users\Angela\.gradle`) (#174) and confirm its SHA-1 matches `G:\Secrets\rigcheck\rigcheck-upload-keystore-NOTES.txt`.
- [ ] Run the grant tool for each tester. Leave one tester on Free (no Pro grant) so someone tests buying Pro, because Pro cannot be bought twice on one account.
- [ ] Send the APK and the guide to the testers. Tell them to expect Web to change under them whenever you push (see "Not in Alpha").
- [ ] During Alpha, glance at the Anthropic Console usage page and the Supabase dashboard once a week. If sign-in or scans suddenly fail, a Supabase pause (click Resume) is the first thing to check.

### What testers should try

Sign up with email (and one with Google), confirm the email, reset a password, a manual check without an account, a manual check signed in, save and reuse a Rig, a scan of each document type (Pro testers), a Pro purchase and a cancelled checkout with a test card ([CreditCardTest.md](CreditCardTest.md)), a scan-pack purchase (Pro testers), the same Garage and History on Web and Android, the over-limit and within-limit verdicts, sign-out, and anything that looks wrong.

### Alpha ends

When the owner calls it. Each distinct problem from the feedback becomes a GitHub ticket that I triage with you; fixes go into stage 2.

## Not in Alpha

Alpha testers should be told all of this up front (the tester guide lists it).

**Payments and prices**
- **No real money, anywhere.** Web buys with the sandbox checkout (test cards only). Android uses RevenueCat's Test Store, so no Google Play billing exists yet (#40 needs a Play Console account).
- **Prices, pack sizes and the Garage and History caps are placeholders** (Free 5 Rigs and 10 checks, Pro 25 and 50) until launch pricing is set (#33).
- **No refund or legal terms** (#34).

**Distribution**
- **Android comes as an APK file**, not from the Play Store. No automatic updates: you send a new APK, and a tester who has a debug build must uninstall it first.
- **Web updates on every push of `MPSkills`**, so the site can change under a tester (#175 is Beta prep).
- **No iOS app and no Sign in with Apple** (#77).

**Product features held back**
- **Import of Rigs saved on the phone before sign-in (#170, `enhancement`):** a Rig saved on Android while signed out is hidden once you sign in, and is not copied to the account. Web already does this.
- **History filters on Android (#173, `enhancement`, `future`).** Web has them.
- **Bumper-pull (tongue weight) trailers (#2, `enhancement`):** the app is for fifth-wheel and gooseneck trailers only.
- **Garage capacity upsell (#13) and fleet management (#14).**
- **The Streamlit demo** is unchanged and not part of Alpha.

**Safeguards and policies (the Beta prep covers these)**
- **No privacy notice or terms pages** (#177). The Alpha guide carries one paragraph: the photos you scan are sent to Anthropic to be read, and deleting an account is by request.
- **No in-app account deletion.**
- **No per-account scan rate limit** (#114) and no replay protection (#96, accepted). The $30 monthly spend limit is the only brake on scan cost.
- **Supabase Free:** no backups, and it pauses after a week of low activity.
- **No refactor or security audit yet.** Alpha runs on the code as it stands.

## Stage 2: Fix and audit

1. **Alpha fixes.** Every bug from the feedback, in the order the owner picks.
2. **#171** External test covering the Android Garage client (test tooling, free, no paid calls).
3. **Refactor analysis (read-only).** One pass per surface (Android, Web, Worker, Python and tooling), then one report. Look for oversized files and screens (the Android ViewModel and nav host), duplicated logic, dead code, and root clutter (`junit-*.xml`, `coverage.json`, the legacy `ARCHIVE_*.md`, `NEXT_STEPS.md` and `ClaudePlans/`). Every finding becomes a ticket with a severity. Only refactors that reduce security risk or block the Beta are done before it. Because it only reads, it could start during Alpha without disturbing testers; the owner decides.
4. **Security audit.** A full `standard` run with the security-audit skill across every surface, reading the run-1 and run-2 ledgers as prior coverage (run-2 output is in `C:\Users\Angela\security-audit-skill\HDTTools\`). This host cannot enforce the skill's sandbox, so it is source review, not live attack testing. Include the dashboard checklist: Supabase redirects and providers, Google consent screen, Cloudflare Worker and Pages settings, RevenueCat key permissions, Anthropic key scope. Run-2 leads already fixed: lead 2 (retries, #112), lead 5 (Test Store key in a release build, #166), lead 7 (ticket scripts trusting any STATUS author, #167). Still open as far as I can see: the Android `rigcheck://login` deep link and the Pages-site External test using the full environment. The audit also covers the code added since run-2: the History and plan-caps migrations, Google sign-in on Web, the Android Garage and History clients, and the new tester grant tool. Fix every high and medium finding before Beta; lows go to the backlog.
5. **Beta prep tickets:**
   - **#175** Web release branch, so a push no longer publishes (a promote command and a moved release gate).
   - **#177** Privacy notice and beta terms, linked from sign-up on both apps (wording approved by the owner).
   - **#114** per-account rate limit on scans (should).
6. **Owner steps:** upgrade Supabase to Pro, add each Beta tester as a Google test user, raise the Anthropic limit if needed, create the Beta tester list.

## Stage 3: Beta

- [ ] Clean-device smoke test: a fresh Android install and a fresh Web account. Cover sign-up and email confirmation, password reset, manual check, a scan, a sandbox Pro purchase and a cancel, Garage and History sync between the two platforms, and sign-out.
- [ ] `uv run scripts/external_freshness.py`, then run the stale External suites (paid calls only up to your ceiling; `anthropic-python` is stale as of 2026-10-23).
- [ ] Promote Web to the release branch, build the APK, send the APK and the guide, and invite the testers.
- [ ] Record on #99 that #96 and #100 do not block the Beta.

## Stage 4: Release (production)

| Area | Work |
|---|---|
| Money | #33 launch pricing (use the per-scan cost measured in Alpha and Beta), #34 full legal, terms and refund review |
| Android store release | Play Console account, production RevenueCat key, Play products and listing, the Play app-signing SHA-1 in the Google OAuth client, **#40** Play Billing External tests |
| Play requirements (check the current policy) | a privacy-policy URL, the data-safety form, an in-app account-deletion path |
| Scan service safety | #114 if not done earlier, revisit #96 with the #100 findings, then close #99 |
| Web | replace the sandbox Web key with the production one (`scripts/wizard_web_revenuecat.sh`); publish the Google consent screen |
| Accounts and data | Supabase on a paid plan |
| Audit | repeat the security audit on the release build |
| Operations | #72 scheduled drift canary, #138 Worker preview deploy, #145 fresh-clone setup check |

## After production

- **Product, per the owner's rule (`enhancement` or `future`):** #2 bumper-pull support, #13 Garage capacity upsell, #14 fleet management (needs its own wayfinder effort), #170 import phone Rigs on first sign-in, #173 Android History filters.
- **Later platforms:** #77 Sign in with Apple, with the iOS app.
- **Tooling backlog, any time:** #68, #69, #70 (epic close gate), #139, #144, #155 to #159 (static-check gaps), #165, #132. Spec #35 is labelled `enhancement` but is the External-tests spec, whose tickets are done: it stays a container.
- **Containers stay as they are:** #3, #15, #35, #49, #51, #99.

## Rough sizing

Estimates, in build sessions, not promises. Stage 1: about 5 sessions (the Android tickets are serial, #172 runs beside them), then the APK build and invitations. Stage 2: about 1 to 2 weeks for the audit and fix pass, plus however many tickets Alpha produces, and 3 small Beta-prep sessions. Stage 3: about 3 days to set up. The Android chain finished faster than I guessed, so these may be high. Re-estimate after the Alpha feedback and the refactor analysis report, which are the first real unknowns.
