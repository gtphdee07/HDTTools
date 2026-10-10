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
| Core library, tests, tooling | `src/hdttools/`, `scripts/`, `tests/` | Your machine | Not deployed. The FastAPI app in `src/hdttools/api/` is no longer deployed (ADR-0007). |

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
git config core.hooksPath .githooks         # pre-commit hook that refreshes dashboard.svg (never blocks)
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
| Supabase URL + publishable key (Android) | same public values | **committed** in `SupabaseAccountBackend.kt` | Android app |
| `SUPABASE_URL` (Worker) | same public project URL | **committed** in `workers/scan-proxy/wrangler.toml` `[vars]` | Worker |
| RevenueCat *public* SDK key | The Android SDK key. Public by design. | **committed** in `RigCheckApplication.kt`. **Currently the Test Store key**, see section 8. | Android app |
| Google OAuth **Web client ID** | Public | **committed** in `GoogleSignIn.kt` (`GOOGLE_WEB_CLIENT_ID`) | Android app |
| Google OAuth **Web client secret** | Secret | **Supabase dashboard only**: Authentication, Providers, Google. Never in the repo or the app. Re-obtain it from the Google Cloud console if lost (create a new secret there). | Supabase |
| Supabase **service-role / secret key** | Full database access | **Not used anywhere. Do not put it anywhere in this repo.** The Web External test of the deployed site flags one if it ever ends up in the bundle. | nothing |
| Cloudflare login | Account access | Interactive: `npx wrangler login`. For non-interactive use: the standard `CLOUDFLARE_API_TOKEN` (and `CLOUDFLARE_ACCOUNT_ID`) environment variables. The repo doesn't use these itself. | Worker deploy |
| GitHub login | Issues, push | `gh auth login` and your normal git credentials | everything |
| Android upload/release keystore and its passwords | Signs a Play Store build | **Not set up yet.** When it is, keep the keystore file and passwords outside the repo (see section 8). | Play release |
| Apple client secret, Services ID, key | Sign in with Apple | **Not set up.** Deferred to #77 with the iOS app. | future |

There are no GitHub Actions secrets: the repo has no CI workflows. The one
`gh secret set` helper in the wizard library is unused by the current wizards.

If you lose a secret, you can't read it back from Cloudflare or Supabase. Create
a new one at the source (Anthropic console, RevenueCat dashboard, Google Cloud
console) and set it again.

## 4. Build and test each piece

Run these from a clean clone to prove the machine works. Everything below the
"free" label makes no paid or live calls.

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
  directory `dist`. Which branch is the **production branch** is a dashboard
  setting I could not see from the repo; confirm it, because `MPSkills` is the
  working branch and `main` is not used. Other branches get preview URLs, which
  is why preview hosts appear in Supabase's Redirect URLs.

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

Anything in `[vars]` (`wrangler.toml`) is plain config and is committed. If you
use a different RevenueCat project, Supabase project or currency, change those
values there.

**Web:** push to the production branch and Cloudflare Pages builds and
publishes. Local build check: `cd web && npm run build`. Anything the
production bundle needs at build time must be committed in `web/.env.production`
(public values only).

**Android debug build:** `cd android && .\gradlew.bat installDebug` with a
device or emulator attached.

**Streamlit:** merge to `main`; Community Cloud redeploys. First deploy takes a
few minutes (apt packages, then pip).

## 7. Moving to a new Supabase or Cloudflare account (checklist)

1. New Supabase project: set Email and Google providers, Site URL and Redirect
   URLs (section 5). Update the project URL in `web/.env.production`,
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

- **No Play Store release pipeline.** `android/app/build.gradle.kts` has no
  `signingConfigs`, and release builds are not set up. A Play release needs: a
  Google Play Console developer account (paid, one time), an upload keystore
  that you generate and keep **outside the repo** (with its passwords recorded
  somewhere safe), a signing config that reads it from untracked properties, the
  app listing, and the Play app-signing SHA-1 added to the Google Android OAuth
  client.
- **RevenueCat is on the Test Store.** `RigCheckApplication.kt` holds the Test
  Store public SDK key. A real release needs the production (Google Play) SDK
  key and Play products connected in RevenueCat. Do not ship the Test Store key.
- **Apple sign-in:** #77. Needs a paid Apple Developer account and the iOS app.
- **No CI.** Nothing runs automatically on push except the Pages and Streamlit
  deploys. The test suites are run by hand.
- **Web photo scanning:** `web/src/api.ts` still posts to `/api/extract/*`,
  endpoints that belonged to the retired FastAPI deploy, and Web is not yet
  calling the shared Worker. I did not verify this against the live site.
- **Android External suite:** #75.

## 9. Where to read more

- `docs/adr/0003` to `0007`: why RevenueCat everywhere, Supabase accounts,
  synced Garage/History, Free vs Pro, static Web.
- `workers/scan-proxy/README.md` and `CONTEXT.md`: the Worker's contract.
- `android/TESTING.md`, `web/TESTING.md`, `workers/scan-proxy/TESTING.md`,
  root `TESTING.md`: each suite and its commands.
- `docs/test-audit/rules.md`: which tests to run for which change.
- `scripts/wizard_*.sh`: the guided setup helpers.
