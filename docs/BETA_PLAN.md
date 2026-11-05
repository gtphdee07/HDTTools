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

## Joint rollout: Web and Android launch the same day (owner, 2026-11-05)

Owner decisions: Web and Android go public **on the same day**; Alpha and Beta use the **same testers on both apps**; the Play listing is under an **organization account** (business verified); Stripe live payments and the business entity are **not started**. The four stages above stay; this section adds what the same-day launch changes. Where it conflicts with a stage below, this section wins.

### What the same-day launch changes

1. **Android is the long pole.** Web can ship the moment its gates pass (a promote command, #175). Android needs a verified Play account, a reviewed listing and a Play-signed build, none of which you control the clock on. So the launch date is set by Android, and Web waits for it.
2. **Start the slow, outside-the-code items now, in parallel with Alpha**, not after Beta. They are all owner or third-party steps, so they cost no build time.
3. **Beta rehearses the real release pipeline.** An APK sent by file (Alpha) never touches Play signing, Play Billing, store review or the live-payment path, so the first time those run would be launch day. Beta must therefore run the Android build through a Play testing track and rehearse Web through the release branch (details under Beta below).
4. **Account deletion and a privacy page become launch gates on both platforms** (Play requires them for an app with accounts; the Web needs the same promise). #177 and a new account-deletion ticket move from "nice to have" to Release gates.

### Long-lead items to start now (owner / third party)

| # | Item | Why it is slow | Needed by | Who |
|---|---|---|---|---|
| L1 | **Business entity and D-U-N-S number** (Dun & Bradstreet) | Play organization accounts require a D-U-N-S; sources give "up to 30 days" (assignment can be quicker), and the legal name and address must match the D-U-N-S record exactly. Country, account type and D-U-N-S cannot be changed on a payments profile later, so get them right the first time | before L2 | owner |
| L2 | **Google Play Console organization account**, verified | Verification follows L1; only the Account Holder can complete it. #40 (Play Billing tests) is blocked until this exists | start of Beta | owner |
| L3 | **Stripe account verified for live mode**, connected to RevenueCat Web Billing | Identity and bank verification; RevenueCat keeps sandbox and production as separate Web Billing configurations, so the live `rcb_` key only appears once the live Stripe account is linked (check both keys show before launch week) | start of Beta (so one real test purchase is possible) | owner |
| L4 | **Legal review #34** (terms, refund policy, privacy wording) and **pricing #33** | Pricing needs the per-scan cost measured in Alpha; legal wording gates #177 | #177 text before Beta, final before Release | owner (+ counsel if you use one) |
| L5 | **Domain decision.** Today Web lives at `rigcheck-web.pages.dev` | The privacy-policy URL that Play and Google sign-in ask for, the Supabase redirect list, the Google OAuth client and RevenueCat all name the Web address. Changing it after launch means touching all of them | before #177 is published | owner |
| L6 | **Play listing content**: icon, feature graphic, phone screenshots, short and long description, content-rating questionnaire, data-safety form, a support email | Pure writing and image work; the screenshots come from the finished re-skin | before Release submission | owner (I can draft the text and the data-safety answers from the code) |

### Plan by stage, both apps together

**Stage 1, Alpha (combined).** Same five testers, one guide, one feedback address.
- Remaining build work: the tester APK. The four-phone check (#198) merged 2026-11-05 and the Android re-skin sign-off is done; #198 found #222 to #225 (all `pre-beta`), and #206 (login first page) is also `pre-beta`. Decide whether #206, #222 and #223 are fixed before the first APK goes out.
- Owner steps: the list under "Owner steps for Alpha" below. Add one Alpha line: every tester uses **both** Web and Android with the same account, so the cross-platform Garage and History sync is exercised from day one.
- Start L1, L3 and L5 this week.
- Exit: the owner calls it. Each problem becomes a ticket, labelled `web`, `android` or `both` so stage 2 can be split across two lanes.

**Stage 2, Fix and audit (both apps).**
1. Alpha fixes, then #171, #206 and the Beta prep tickets #175, #177, #114, as written below.
2. **Launch-gate tickets (filed 2026-11-05):**
   - **#210** in-app account deletion on Web and Android, a public deletion page and the server step (`pre-beta`). Release gate.
   - **#211** production configuration runbook, `docs/PRODUCTION_CONFIG.md` (`pre-beta`): the swap of every sandbox value for a production one.
   - **#212** launch-day runbook, `docs/LAUNCH_RUNBOOK.md` (blocked by #175): order of operations and a rollback for each app.
   - **#213** Play listing pack, `docs/play-listing/`: listing text, data-safety answers, reviewer access, screenshots.
   - **#221** Android Play-uploadable bundle for the Beta track (`pre-beta`): non-debuggable, upload-signed, production RevenueCat key.
   - The owner steps L1 to L6 are explained in [LAUNCH_LONG_LEAD.md](LAUNCH_LONG_LEAD.md) and tracked as **#215 to #220** under the epic **#214** (which also lists #210 to #213, #221, #175, #177 and #40). L1 is a check only: the owner already has a D-U-N-S number.
3. Refactor analysis and the security audit, as written below. Add to the audit scope the live-payment path and account deletion, because both are new code between Alpha and Beta.
4. Owner: Supabase Pro, Anthropic limit raised if needed (the live scan load will exceed Alpha), Beta tester list.
5. L2 should be verified by the end of this stage. If it is not, Beta cannot rehearse Play, and the launch date moves.

**Stage 3, Beta (combined, under 20 testers).**
- **Android through Play, not by file.** Play rejects a debuggable upload (forum reports; no Google page found) and the Alpha `beta` build is debuggable on purpose (#185), so this needs a new non-debuggable, Play-signed bundle that uses the real RevenueCat Android key with Play license testers (the #166 guard refuses the Test Store key in such a build). That means the Play account (L2), one test product and RevenueCat's link to Play must exist before the Beta starts; the build is ticket **#221**. Upload the Play-signed bundle to an internal or closed testing track and invite testers from there. This rehearses Play App Signing (and the new SHA-1 for Google sign-in), Play Billing with license testers (#40 becomes runnable here), the deep link, and Play's pre-launch checks. Keep the APK as a fallback for anyone Play will not take. This replaces "APK file only" for Beta; Alpha stays APK-only.
- **Web through the release branch** (#175), promoted once for the Beta, so the promote step is rehearsed.
- **Payments:** test cards and Test Store stay for testers. The owner makes **one real low-price purchase on each app, then refunds it**, to prove the live path end to end (Stripe live, RevenueCat production, Play Billing).
- Clean-device smoke test and the External runs, as listed below, run against the **release candidate** (the exact build and Web commit that would ship).
- Exit gate: no open high or medium bug; every Release gate in the table below is either done or has an owner and a date.

**Stage 4, Release (same day).**
- **Submit Android about a week ahead.** Submit the production release to Play, with managed publishing turned on if the console offers it (verify in the console: it lets an approved release wait until you press publish). Use a staged rollout percentage rather than 100 percent on day one.
- **Freeze:** from submission, only fixes to blockers go to the release branch. Web changes after the freeze do not get promoted.
- **Launch day, in order:** (1) confirm Android is approved and waiting; (2) confirm Supabase Pro, Anthropic limit and the Cloudflare Worker are healthy; (3) swap the Web production key and promote Web; (4) publish Android; (5) one real purchase and one real scan on each app, refund the purchases; (6) announce.
- **Rollback:** Web, promote the previous release commit; Android, halt the staged rollout and (if needed) un-publish; Worker, redeploy the previous version; payments, switch offerings in RevenueCat without a rebuild.
- Watch the first 48 hours: Anthropic Console spend, Supabase usage, Worker logs (#183), Android crash reports (#184).

### Release gates for a same-day launch (both must be true)

| Gate | Web | Android |
|---|---|---|
| Account deletion in the app | new ticket | new ticket |
| Privacy policy and terms published at the final URL (#177, L5) | yes | yes, the URL entered in Play |
| Live payments proven by one real purchase and refund | Stripe live + `rcb_` production key | Play Billing + production RevenueCat key + Play products |
| Production keys in place, sandbox and Test Store keys out of the shipped build | `web/.env.production` | release build; the #166 guard enforces it |
| Auth redirects for the final domain and the Play App Signing SHA-1 | Supabase redirect list, Google OAuth Web client | Google OAuth Android client |
| Google consent screen published (out of Testing mode) | yes | same project |
| Store listing approved | n/a | Play review passed, release waiting |
| Security audit findings (high, medium) fixed | yes | yes |
| Supabase on a paid plan, Anthropic limit sized for launch | shared | shared |
| Rollback tested at least once in Beta | promote previous | halt rollout |

### Open points to check against current sources (I could not confirm them in one place)

- Whether the Google consent screen needs Google's OAuth verification when published, with only the `openid`, `email` and `profile` scopes. The page I found says testing-mode warnings and the 7-day expiry do not apply to those scopes, but does not say outright that verification is skipped. Read the verification criteria page before launch week.
- Whether the Play Console you will see offers managed publishing and staged rollout as described, and what Play's current review time is. Both are quick checks in the console once L2 exists.
- Whether Play still wants the extra closed-test run for organization accounts. Google's help page says the 12-tester, 14-day rule is for personal accounts created after 13 November 2023; an organization account is exempt, so none is planned. Re-read the page when L2 is open.

Sources: Google Play Help, "Testing requirements for new personal accounts" (support.google.com/googleplay/android-developer/answer/14151465); Google Cloud Help, "Manage App Audience" (support.google.com/cloud/answer/15549945); Android Developers Blog, "Boosting trust and transparency in Google Play" (July 2023, the D-U-N-S requirement); RevenueCat docs and community threads on Web Billing sandbox and production configurations; Stripe, "Go live" checklist (docs.stripe.com/get-started/checklist/go-live). The timing figures for D-U-N-S and organization verification come from third-party help pages, not from Google, so treat them as estimates.

## Ticket sort (owner, 2026-11-05)

Every open ticket carries exactly one bucket label, or none if it is a container. Give a new ticket its bucket when it is filed, and re-sort at the end of Alpha. Check with `gh issue list --label <bucket>`; this table is a snapshot and goes stale first.

| Bucket (label) | Rule | Tickets on 2026-11-05 |
|---|---|---|
| Alpha (`pre-alpha`) | Alpha testers cannot be invited without it | none open (#198 merged 2026-11-05) |
| Before Beta (`pre-beta`) | Beta cannot run, or cannot rehearse the launch, without it; includes test work that shortens runs or widens coverage for the Beta regressions | #175 #177 #114 #171 #170 #206 #210 #211 #221, #222 #223 #224 #225 (found by #198's device matrix; filed 2026-11-05), and #132 #144 #157 #158 #159 #165 |
| Before launch (`pre-release`) | Skipping it risks money, user data, a store rejection or a broken launch | #212 #213 #33 #34 #40 #96 #100 #72 #138 #209, and the owner steps #215 to #220 |
| After launch (`future`) | Enhancement, or tooling that does not protect the launch | #2 #13 #14 #77 #173 #204, and #68 #70 #145 #155 #208 |
| Closed, not doing (`wontfix`) | Not worth building | #69 (epic-close hook), #139 (pre-push registry cache) |
| Containers (no label) | Track their children only | #3 #15 #35 #49 #51 #99 #187 #214 |

Decisions in the sort: #170 (import phone-saved Rigs on first sign-in, an `enhancement`) moved up to before Beta because a Rig saved before sign-in disappears from view and confuses testers; #96 and #100 (scan replay) stay before launch and are decided with the Alpha scan numbers; tooling that shortens or widens the test runs goes before Beta, the rest waits. #172, #176 and #178 were closed because their children are done.

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
| 7 | **#190** the design round (yours, after #189), then **#191** theme and shared components | |
| 8 to 12 | **#192** to **#196** re-skin, one ticket per screen group | |
| 13 | **#197** final pass and your sign-off on the phone | |
| 14 | **#198** (`pre-alpha`) four emulator phone shapes on G: and the screen checks on each. The profiles can be created any time the emulator is idle; run the checks after #197 so they test the re-skinned screens | |

Owner decisions, 2026-10-27: the whole Android re-skin (epic #187) is done before the Alpha starts, so the first tester APK is built after #197 and your sign-off on the phone. The design round (#190) starts when #189 has merged. Pushes are checkpoints (after #189, and at the end), each asked first.

#176 and #178 are now containers; #172 stays open for later Web items. The decisions (build type `beta`, `versionCode` by hand, feedback by email to WTIAppDev@gmail.com, Pro plus 20 scans, crash report saved and sent on the next launch only if the tester agrees, no account id in Worker logs) are recorded on the tickets.

Android tickets run one at a time because there is one emulator; lane B has no Gradle and runs beside lane A. The Worker change in #183 means the owner redeploys the Worker (`npm run deploy`) and the External run described in `TESTING.md` precedes the push. Run each ticket with the steps on the run sheet ([agents/test-round-handoff.md](agents/test-round-handoff.md)); `/ticket-merge` reviews each.

### Owner steps for Alpha

- [x] Feedback goes to WTIAppDev@gmail.com (an email address, not a form), so there is no form to create.
- [ ] Add each Alpha tester's Gmail as a Google test user (consent screen in Testing mode), up to 5.
- [ ] Build the APK on your machine with the signing values in `gradle.properties` in your Gradle user home (the `GRADLE_USER_HOME` folder; on this machine `G:\GradleUserHome\gradle.properties`, not `C:\Users\Angela\.gradle`) (#174) and confirm its SHA-1 matches `G:\Secrets\rigcheck\rigcheck-upload-keystore-NOTES.txt`.
- [ ] Create a Supabase secret key (dashboard, Project Settings, API keys) and set `SUPABASE_SECRET_KEY` and `REVENUECAT_SECRET_KEY` in your shell only, never in the repo (#205).
- [ ] Run `scripts/add_tester.py <email>` for each tester (dry run, then `--apply`): it creates the confirmed account with no password and the RevenueCat customer, then grants Pro and scans, so the tester need not sign in first. Use `--no-pro` for one tester, so someone tests buying Pro, because Pro cannot be bought twice on one account. Tell each tester to use Forgot password and set the password on the Web page.
- [ ] Add each Alpha tester's Gmail as a Google test user (manual, Google Cloud Console; no script does it) if they will use Continue with Google.
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
- **Web updates only when the `release` branch is promoted** (`scripts/promote_release.py`, #175), so the site does not change under a tester by accident; a push of `MPSkills` makes a preview only.
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
