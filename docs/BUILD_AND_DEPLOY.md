# Building and deploying from a new machine

How to build, test and deploy RigCheck's pieces from a machine that has never
run this project. Written 2026-10-09, after Android sign-in (#22) landed.

**This document contains no secrets.** It says which secret goes where. The
values live in the owner's own record. Never commit a value, and never paste one
into an issue, a PR or a chat.

`DEV_ENVIRONMENT.md` is the other half: it lists this one Windows machine's
exact tool paths. Use it as an example, not as truth for a new machine.

## 1. What the pieces are

| Piece | Where | Runs on | Deployed how |
|---|---|---|---|
| Android app | `android/` | Android devices | Debug APK from Gradle today. Play Store release is **not set up in the repo** (see section 8). |
| Scan service (Worker) | `workers/scan-proxy/` | Cloudflare Workers | `npm run deploy` (wrangler) |
| Web app | `web/` | Browser (static) | Cloudflare Pages, push-to-deploy from GitHub |
| Streamlit demo | `streamlit_app/` | Streamlit Community Cloud | Push-to-deploy from GitHub (branch `main`) |
| Core library, tests, tooling | `src/hdttools/`, `scripts/`, `tests/` | Your machine | Not deployed. The FastAPI app that was in the `api` package was removed (ADR-0007, #135). |

Outside services the pieces depend on (each has dashboard settings that live
**outside git**, see section 5): Supabase (accounts), RevenueCat (purchases and
the scan balance), Anthropic (Claude vision), Cloudflare (Worker and Pages),
Google Cloud (Google sign-in), GitHub (code, issues, Pages and Streamlit deploy
triggers).

## 2. Tools to install on a new machine

Ask before installing anything system-wide, and choose the install drive
deliberately: the primary machine's C: drive is space-constrained (see
`CLAUDE.md`, "System Tool Installs").

| Tool | Needed for | Notes |
|---|---|---|
| Git, and the GitHub CLI `gh` (`gh auth login`) | everything; issues | `gh` is how issues and the wizards talk to GitHub |
| `uv` | Python, tests, scripts | Never use bare `pip` or a global `python`. `.python-version` is 3.14, and `uv` fetches it. |
| Node.js 24 | Web, Worker, tests | Worker tests run `.ts` files directly with `node --test`, which needs a recent Node. This project uses v24. |
| Android Studio (bundles the JDK and SDK manager) | Android | Install the SDK platform for API 37 (`compileSdk 37`, `minSdk 26`) and the emulator |
| Tesseract OCR | Streamlit and the Python OCR tests | Windows: UB-Mannheim build. Auto-detected at `C:\Program Files\Tesseract-OCR`. |
| Windows PowerShell 5.1 | the `*.ps1` scripts (`release.ps1`, `test-weekly.ps1`, `test-external.ps1`) | On macOS or Linux these scripts need `pwsh` or have to be run by hand |
| Bash (Git Bash on Windows) | the wizard scripts in `scripts/wizard_*.sh` | |

One-time per clone:

```
git clone https://github.com/gtphdee07/HDTTools.git
cd HDTTools
git checkout MPSkills                       # all work happens on MPSkills; never commit to main
git config core.hooksPath .githooks         # pre-commit refreshes dashboard.svg (never blocks); pre-push is the External release gate (TESTING.md)
uv sync                                     # Python deps into .venv
cd web && npm install && cd ..
cd workers/scan-proxy && npm install && cd ../..
```

Android specifics:

- Open `android/` in Android Studio once. It writes `android/local.properties`
  (gitignored) with `sdk.dir`. Or set the `ANDROID_SDK_ROOT` environment
  variable.
- `JAVA_HOME` should point at Android Studio's bundled JDK (`.../jbr`) so
  `gradlew` can start. Gradle's own daemon JVM is pinned to JDK 21 by the
  committed `android/gradle/gradle-daemon-jvm.properties` and downloads itself
  on first use (needs internet). It exists because detekt breaks on newer JDKs.
- `adb` is not on PATH by default: use `<sdk>/platform-tools/adb`.
- Create an emulator with a **Google Play** system image (not plain "Google
  APIs") if you want to test Google sign-in, because only Play images can add a
  Google account.

Streamlit needs two small files in the user's home on a fresh machine, or its
first run can hang on an interactive prompt: `~/.streamlit/credentials.toml`
(`email = ""`) and `~/.streamlit/config.toml` (`gatherUsageStats = false`,
`server.headless = true`).

## 3. Secrets: what exists, where each goes

**Rule:** a value in the "committed" column is public by design and is already
in the repo. Everything else is a real secret and must only ever live in the
place listed.

| Name | What it is | Goes where | Needed by |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Anthropic console API key (not a Claude.ai subscription) | **Cloudflare**, as a Worker secret: `cd workers/scan-proxy && npx wrangler secret put ANTHROPIC_API_KEY`. Also your **shell environment**, only when running paid live tests. | Worker (production); live and paid tests |
| `REVENUECAT_SECRET_KEY` | RevenueCat *secret* API key with Read & Write on "Customer Purchases Configuration" and "Customer Configuration" | **Cloudflare**, as a Worker secret: `npx wrangler secret put REVENUECAT_SECRET_KEY`. Also your **shell environment** for live tests. | Worker (production); live tests |
| `WEB_EXTERNAL_TEST_EMAIL`, `WEB_EXTERNAL_TEST_PASSWORD` | A real Supabase email+password test user, with a funded RevenueCat customer | `web/.env.local` (gitignored by `*.local`) | Web External suite; Worker live suites (they sign this user in) |
| `WEB_EXTERNAL_TEST_NOCREDITS_EMAIL`, `WEB_EXTERNAL_TEST_NOCREDITS_PASSWORD` | A second Supabase test user whose RevenueCat customer has no balance | `web/.env.local` | Worker live suites |
| `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY` | The Supabase project URL and publishable key. Public by design. | **committed** in `web/.env.production` (the production build needs them baked in; Cloudflare Pages did not pass dashboard variables into the build). Also copy them into `web/.env.local` so local runs and live tests see them. | Web build; live tests |
| `VITE_REVENUECAT_WEB_PUBLIC_API_KEY`, `VITE_REVENUECAT_WEB_OFFERING_ID` | The RevenueCat **Web Billing** public API key and the offering id the Web paywall reads. Public by design. Without both, the Web app hides purchases (the free calculator is unaffected). Optional: `VITE_REVENUECAT_PRO_ENTITLEMENT_ID` (default `pro`) and `VITE_REVENUECAT_PRO_PACKAGE_ID` (default: the offering's lifetime package) and `VITE_REVENUECAT_SCAN_PACK_PACKAGE_IDS` (default: every other web-purchasable consumable package in the offering). | **committed** in `web/.env.production`, like the Supabase values. Also copy into `web/.env.local` for local runs. | Web build |
| `VITE_SCAN_SERVICE_URL` | The scan-proxy Worker's address (no path), which the Web app posts scans to. Public by design. Without it the Web app says scanning is unavailable. | **committed** in `web/.env.production`. Also copy into `web/.env.local` to scan from `npm run dev`. | Web build |
| Supabase URL + publishable key (Android) | same public values | **committed** in `SupabaseAccountBackend.kt` | Android app |
| `SUPABASE_URL` (Worker) | same public project URL | **committed** in `workers/scan-proxy/wrangler.toml` `[vars]` | Worker |
| RevenueCat *public* SDK key | The Android SDK key. Public by design. | **committed** in `RigCheckApplication.kt`. **Currently the Test Store key**, see section 8. | Android app |
| Google OAuth **Web client ID** | Public | **committed** in `GoogleSignIn.kt` (`GOOGLE_WEB_CLIENT_ID`) | Android app |
| Google OAuth **Web client secret** | Secret | **Supabase dashboard only**: Authentication, Providers, Google. Never in the repo or the app. Re-obtain it from the Google Cloud console if lost (create a new secret there). | Supabase |
| Supabase **service-role / secret key** | Full database access | **Not used anywhere. Do not put it anywhere in this repo.** The Web External test of the deployed site flags one if it ever ends up in the bundle. | nothing |
| Cloudflare login | Account access | Interactive: `npx wrangler login`. For non-interactive use: the standard `CLOUDFLARE_API_TOKEN` (and `CLOUDFLARE_ACCOUNT_ID`) environment variables. The repo doesn't use these itself. | Worker deploy |
| GitHub login | Issues, push | `gh auth login` and your normal git credentials | everything |
| Android upload/release keystore and its password | Signs a beta APK, and later a Play Store build | Create it with `bash scripts/wizard_android_upload_key.sh` (from the repo root). The file lives in a folder **outside the repo**, the password in your password manager, a second copy of the file somewhere separate. Never commit either. See section 8. | Beta APK; Play release |
| `betaKeystoreFile`, `betaKeyAlias`, `betaKeystorePassword` (or `BETA_KEYSTORE_FILE`, `BETA_KEY_ALIAS`, `BETA_KEYSTORE_PASSWORD`) | The three values the `beta` build type signs with: the keystore's full path, its key alias, and its one password | Your **user-level Gradle properties file** (`gradle.properties` in your Gradle user home (the `GRADLE_USER_HOME` folder; on this machine `G:\GradleUserHome\gradle.properties`, not `C:\Users\Angela\.gradle`), outside the repo) or the environment variables. No defaults: a beta build without all three fails and names the missing one. | Beta APK (`assembleBeta`) |
| `appVersionCode` | The beta APK's `versionCode` (default 1) | Raise it by hand, in the same properties file or with `-PappVersionCode=<n>`, before each APK you send | Beta APK |
| Apple client secret, Services ID, key | Sign in with Apple | **Not set up.** Deferred to #77 with the iOS app. | future |

There are no GitHub Actions secrets: the repo has no CI workflows. The one
`gh secret set` helper in the wizard library is unused by the current wizards.

If you lose a secret, you can't read it back from Cloudflare or Supabase. Create
a new one at the source (Anthropic console, RevenueCat dashboard, Google Cloud
console) and set it again.

## 4. Build and test each piece

Run these from a clean clone to prove the machine works. Everything below the
"free" label makes no paid or live calls. In a new git worktree on a machine that
is already set up, run `uv run scripts/worktree_setup.py` first instead of
installing by hand (`docs/agents/worktree-setup.md`).

**Free, offline:**

```
uv run pytest -q                                   # Python (paid and live tests are excluded by default)
cd web && npm test && npm run build                # Web unit tests, then tsc + vite build (output: web/dist)
cd workers/scan-proxy && npm test && npm run typecheck
cd android && .\gradlew.bat testDebugUnitTest detekt   # JVM tests + static analysis; first run downloads JDK 21 and dependencies
cd android && .\gradlew.bat assembleDebug               # debug APK at android/app/build/outputs/apk/debug/
```

On macOS or Linux use `./gradlew`.

**Needs an emulator or device (free):** boot an emulator, then
`cd android && .\gradlew.bat connectedDebugAndroidTest`. It runs fully offline
(`CustomTestRunner` swaps in a plain `Application`). All 77 tests pass. Reboot
a long-running emulator first: under heavy load, tests fail on timing.

**Paid or live. Never run these without deciding to spend money.**
`ANTHROPIC_API_KEY` and `REVENUECAT_SECRET_KEY` may already be set in your shell
(they are on the primary machine), so a careless command can bill you:

- `workers/scan-proxy`: `npm run test:weekly` (redeploys the Worker first and
  makes two real Claude calls), `test-release.ps1`, `release.ps1`
- `android/`: `test-weekly.ps1` (redeploys the Worker, two real Claude calls),
  `release.ps1` (needs an emulator; asks you to confirm each paid step)
- `test-external.ps1`, `web/test-external.ps1`: per-surface External suites; the
  Anthropic surface is paid and asks first

The release scripts count paid calls against a budget declared with
`-MaxPaidCalls`. Don't append a test-name filter to `npm run test:weekly`: it is
ignored and runs everything.

Note: the Android External suite can't currently authenticate its real scans
(#75), and `release.ps1` can't go green until #75 is fixed.

## 5. Service configuration that lives outside git

None of this is visible from a clone. If you rebuild an environment, or point
the apps at a new project, all of it must be recreated or re-verified.

### Supabase (accounts), project `lifginpapkevreyrzzex`

- Authentication, Providers: **Email** on (email confirmation required);
  **Google** on, with the Web client ID and Web client secret; **Apple** off
  (#77).
- Authentication, URL Configuration: **Site URL** is
  `https://rigcheck-web.pages.dev`. This matters: the sign-up confirmation link
  ends at the Site URL. Left at the default `http://localhost:3000`, new users
  see a "refused to connect" page after confirming (this was #78).
  **Redirect URLs** should include `https://rigcheck-web.pages.dev/**` (the
  password-reset redirect from Web and Android), plus `http://localhost:5173/**`
  for local Web dev and any Pages preview host you use.
- Check what's enabled without a login:
  `curl -H "apikey: <publishable key>" https://<project>.supabase.co/auth/v1/settings`
  and look for `"email"`, `"google"`, `"apple"` as true or false.
- **Garage table (#28).** Run `supabase/migrations/20261010000000_garage_rigs.sql`
  once: Dashboard, SQL Editor, paste the file, Run. It creates `garage_rigs`
  (row-level security on), the `add_rig` function that enforces the cap and
  idempotent retry, and the grants. Without it a signed-in Web user's Rigs
  fail to save and the `supabase-tables` External suite fails. Check it with
  `cd web && EXTERNAL_SURFACES=supabase-tables npx vitest run --config vitest.external.config.ts`.
  A new Supabase project needs the same step (section 7). The cap itself is in
  `plan_caps` (below), not in this migration.
- **History table (#29).** Run `supabase/migrations/20261022000000_history_entries.sql`
  once, the same way (it is independent of the Garage one). It creates
  `history_entries` (row-level security on, read-only to the owning account), the
  `add_history_entry` function that keeps the newest checks per account (the
  plan's cap), dropping the oldest, and makes a retried add count once, and the
  grants. Without it a signed-in Web user's checks are not saved to the
  account (the app says so) and the History half of the `supabase-tables`
  External suite fails. Check it with the same command as above.
- **Plan caps (#30).** Run `supabase/migrations/20261023000000_plan_caps.sql`
  once, the same way, **after** the two above. It creates `plan_caps`, the one
  place the Garage and History caps for Free and Pro are written, and replaces
  `add_rig` and `add_history_entry` with versions that read it. The numbers in it
  are placeholders until launch pricing (#33). To change one, edit its row in the
  SQL Editor, for example `update public.plan_caps set garage_cap = 30 where plan = 'pro';`
  (no new migration, no redeploy). The app tells the functions whether the account
  is Pro, so the cap is only as honest as the app (owner's decision on #30; a
  server-verified plan would be a later ticket). **Run it before the Web build
  that sends the plan is deployed** (Pages deploys on every push to `MPSkills`):
  that build calls the two functions with a `p_pro` argument the old ones do not
  have, so every Rig and History save fails until the migration is applied. The
  other order is safe: an older Web build omits `p_pro` and is treated as Free.
  Check it with the same command as above.
- Free tier: pauses after 7 idle days and has no automatic backups (accepted
  for now, ADR-0005). If sign-in suddenly stops working, check whether the
  project is paused.
- Test users: the two Web/Worker test users above live here, as do any manual
  test accounts. Create them with `scripts/wizard_web_external_test_user.sh`
  and `scripts/wizard_scan_proxy_live_accounts.sh` (they write
  `web/.env.local`).

### Google Cloud (Google sign-in)

- An **OAuth consent screen**. If it is in "Testing" mode, only accounts listed
  as test users can sign in; publish it before real users arrive.
- A **Web application** OAuth client. Authorized redirect URI is
  `https://<project>.supabase.co/auth/v1/callback`. Its client ID goes in
  `GoogleSignIn.kt` and its client ID and secret go in Supabase.
- An **Android** OAuth client for package `com.rigcheck.app`, with the signing
  certificate's **SHA-1**. **Every signing key needs its SHA-1 registered**:
  each developer machine's debug keystore (`~/.android/debug.keystore`;
  `keytool -list -v -keystore <path> -alias androiddebugkey -storepass android`),
  and the Play app-signing certificate for release builds. A missing SHA-1 shows
  up as Google sign-in failing on that machine only.
- `scripts/wizard_android_sign_in.sh` walks through the Google parts, run from
  the repo root.

### RevenueCat

- One project (id in `workers/scan-proxy/wrangler.toml`). A **virtual currency**
  with code `SCAN` (the code must match `wrangler.toml`'s
  `REVENUECAT_CURRENCY_CODE`). An **offering** whose packages the paywall lists;
  today two products (`lifetime`, `consumable`) on the **Test Store**.
- RevenueCat creates a customer automatically for each Supabase account id the
  first time the app logs it in. The app never sets a user id by itself, so a
  fresh install starts anonymous.
- `scripts/wizard_web_revenuecat_dashboard.sh` (run from the repo root) walks
  through the RevenueCat dashboard side of Web "Buy Pro": the Pro product, the
  `pro` entitlement, the starter `SCAN` bundle and the offering package. It
  offers to run the next wizard, then creates the External test's Pro customer
  `external-suite-pro` and walks through granting it `pro` (#105).
- `scripts/wizard_web_revenuecat.sh` (run from the repo root) walks through
  collecting the Web Billing public key and offering id and writes the
  `VITE_REVENUECAT_*` values into `web/.env.local` and, if you choose,
  `web/.env.production`.
- Web "Buy Pro" needs, on the RevenueCat side: a **Web Billing** app (its public
  API key is the Web key above), a lifetime Pro product with a package in the
  Web offering, a `pro` entitlement that product unlocks, and the product set
  to grant the starter `SCAN` bundle. The Web app reads the entitlement and the
  `SCAN` balance; it does not grant scans itself. Before shipping, run the real
  sandbox cancel test in #11.
- Web "Buy scan packs" needs, on the RevenueCat side, one **consumable** Web
  Billing product per pack, each in a package of the same Web offering and set
  to grant its number of `SCAN`. Pack sizes and prices are launch decisions
  (ADR-0006). The Web app lists every web-purchasable **consumable** package in
  the offering except Pro as a pack (a subscription or non-consumable is never
  listed), or only the packs you name in `VITE_REVENUECAT_SCAN_PACK_PACKAGE_IDS` (comma-separated package
  identifiers; optional, public). No pack packages means no "Buy more scans"
  card. Run a sandbox pack purchase (and its cancel) with #11's.
- Real money needs a Google Play app, store products, and the Play credentials
  connected in RevenueCat. That's not configured (section 8).

### Cloudflare

- **Worker** `rigcheck-scan-proxy` (see `wrangler.toml`): deployed to a
  `workers.dev` address under the owner's account. **That full URL is hardcoded
  in `ScanApiClient.kt` (`SCAN_ENDPOINT`)**, so deploying the Worker from a
  different Cloudflare account, or renaming it, means changing that constant and
  rebuilding the app.
- **Pages** project `rigcheck-web`, Git integration to `gtphdee07/HDTTools`.
  Settings: root directory `web`, build command `npm run build`, build output
  directory `dist`. The **production branch is `MPSkills`** (confirmed in the
  Cloudflare dashboard, 2026-10-15, with automatic deployments on), so **every
  push to `MPSkills` publishes the Web app to https://rigcheck-web.pages.dev/**.
  A Web change that depends on a Worker change must wait to be pushed until
  the Worker is redeployed. Other branches get preview URLs, which is why
  preview hosts appear in Supabase's Redirect URLs.

### GitHub

- Issues are the tracker (`docs/agents/issue-tracker.md`), with labels
  `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`,
  `wontfix`.
- **Streamlit Community Cloud**: per `streamlit_app/README.md` it deploys from
  branch **`main`** (file `streamlit_app/app.py`; `packages.txt` at the repo root
  installs `tesseract-ocr`). I could not see the live app's settings, so confirm
  it. If that is right, since all work is on `MPSkills`, the Streamlit deploy
  only changes when `main` does.

## 6. Deploying

**Worker** (from `workers/scan-proxy/`):

```
npx wrangler login                     # once per machine
npx wrangler secret put ANTHROPIC_API_KEY
npx wrangler secret put REVENUECAT_SECRET_KEY
npm run typecheck && npm run deploy
```

`npm run deploy` runs the External release gate first and refuses while a
scan-proxy surface is stale; see "External release gate" in `TESTING.md` for how
to unlock it and for `npm run deploy -- --force --reason "..."`.

Anything in `[vars]` (`wrangler.toml`) is plain config and is committed. If you
use a different RevenueCat project, Supabase project or currency, change those
values there.

**Web:** push to `MPSkills` (the production branch) and Cloudflare Pages builds
and publishes within a few minutes. The pre-push hook gates that push when it touches `web/`
(External release gate, `TESTING.md`). Local build check: `cd web && npm run build`. Anything the
production bundle needs at build time must be committed in `web/.env.production`
(public values only).

**Android debug build:** `cd android && .\gradlew.bat installDebug` with a
device or emulator attached.

**Streamlit:** merge to `main`; Community Cloud redeploys. First deploy takes a
few minutes (apt packages, then pip).

## 7. Moving to a new Supabase or Cloudflare account (checklist)

1. New Supabase project: set Email and Google providers, Site URL and Redirect
   URLs (section 5), and run every file in `supabase/migrations/` in order. Update the project URL in `web/.env.production`,
   `SupabaseAccountBackend.kt` and `workers/scan-proxy/wrangler.toml`, and the
   publishable key in the first two.
2. Google Cloud: the Web client's redirect URI must be the new project's
   `.../auth/v1/callback`. The new project needs the Web client ID and secret.
3. New Cloudflare account: redeploy the Worker (secrets are per Worker and don't
   transfer), update `SCAN_ENDPOINT`, reconnect Pages to GitHub.
4. Recreate the test users and `web/.env.local` with the two wizards.
5. Re-run section 4's free checks, then a manual email and Google sign-in on an
   emulator.

## 8. Not done yet, so a new machine can't do it

Be explicit about these so nobody assumes they work:

- **The beta APK (#174) is built; the Play Store release is not.** The
  `beta` build type signs with your upload keystore, is not debuggable, keeps
  the package `com.rigcheck.app`, and may use the RevenueCat Test Store key
  (test payments only). Put the three signing values from section 3 in
  `gradle.properties` in your Gradle user home (the `GRADLE_USER_HOME` folder; on this machine `G:\GradleUserHome\gradle.properties`, not `C:\Users\Angela\.gradle`), raise `appVersionCode`, then from `android/`
  run `.\gradlew.bat assembleBeta`; the APK is
  `app/build/outputs/apk/beta/app-beta.apk`. Check
  `keytool -printcert -jarfile <apk>` shows the SHA-1 recorded when you made
  the keystore. Send that file to testers; `versionCode` must rise for each
  one or they cannot update in place. **A beta APK cannot update a debug
  build** (different signing key): testers, and you, uninstall any debug build
  first. A missing signing value fails the build and names the property.
- **No Play Store release pipeline.** `release` builds are not set up (the
  `release` type has no signing config). A Play release needs: a Google Play
  Console developer account (paid, one time), the upload keystore (the one
  above), a release signing config that reads it from the same untracked
  properties, the app listing, and the Play app-signing SHA-1 added to the
  Google Android OAuth client.
- **RevenueCat is on the Test Store.** `RigCheckApplication.kt` holds the Test
  Store public SDK key. A real release needs the production (Google Play) SDK
  key and Play products connected in RevenueCat. Do not ship the Test Store key.
- **Apple sign-in:** #77. Needs a paid Apple Developer account and the iOS app.
- **No CI.** Nothing runs automatically on push except the Pages and Streamlit
  deploys. The test suites are run by hand.
- **Web photo scanning (#26):** `web/src/api.ts` posts to the shared Worker at
  `VITE_SCAN_SERVICE_URL`. A browser calls the Worker from another origin, so
  the Worker now answers CORS (any origin; the account token is a bearer header,
  not a cookie). **Redeploy the Worker (`npm run deploy`) before the Web build
  that sets that address goes live**, or the browser blocks every scan. Not yet
  tried against the live Worker.
- **Android External suite:** #75.

## 9. Where to read more

- `docs/adr/0003` to `0007`: why RevenueCat everywhere, Supabase accounts,
  synced Garage/History, Free vs Pro, static Web.
- `workers/scan-proxy/README.md` and `CONTEXT.md`: the Worker's contract.
- `android/TESTING.md`, `web/TESTING.md`, `workers/scan-proxy/TESTING.md`,
  root `TESTING.md`: each suite and its commands.
- `docs/test-audit/rules.md`: which tests to run for which change.
- `scripts/wizard_*.sh`: the guided setup helpers.
