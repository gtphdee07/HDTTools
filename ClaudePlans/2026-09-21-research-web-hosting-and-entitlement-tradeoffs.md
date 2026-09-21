# Research: Web hosting options + entitlement source-of-truth tradeoffs

**Status: research only — no decision made, no code changed.** This document
feeds the open "where does the web app live, and what does that imply for
the entitlement system" question from `NEXT_STEPS.md` item #20. It does not
resolve item #20's central open question (RevenueCat vs. Stripe vs. a
unified system of record) — that's explicitly left to the user.

## 1. What's actually being decided

Two related but separable questions:

1. **Near-term**: how to get `web/` (React+Vite+TS) + `src/hdttools/api/`
   (FastAPI, stateless, Tesseract-only today) online and linkable from the
   existing site, with push-to-deploy automation, at near-zero cost. No
   custom subdomain — a provider-issued URL is fine and will simply be
   linked to.
2. **Medium-term**: where the future shared-accounts system (item #20 in
   `NEXT_STEPS.md`) lives — a real users/credit-balance/session database,
   auth (email+password and Google/Apple), and two payment-provider
   webhook sources (Stripe for Web, RevenueCat for Android) — and whether
   the hosting choice makes it easier or harder to eventually answer the
   entitlement source-of-truth question one way or the other.

Both questions are addressed together for each option below, because the
near-term hosting choice constrains (or doesn't) the medium-term one.

## 2. Architectural facts that constrain every option

Read directly from the repo before researching anything external:

- **`web/src/api.ts:3`** hardcodes `API_BASE_URL = 'http://localhost:8000'`.
  Per `ClaudePlans/2026-09-18-web-beta-deployment.md`, the fix is to make
  this environment-aware (empty string / same-origin in production) — that
  change is orthogonal to which host is chosen and would be needed under
  every option below except the ones that keep frontend and backend on two
  different origins (Options D and, partially, E), which instead need a
  real `API_BASE_URL` pointed at the backend's own origin plus CORS opened
  for it.
- **`src/hdttools/api/main.py`** is completely stateless today — no
  database, no auth, CORS locked to `localhost:5173` — and it shells out to
  the **Tesseract OCR engine** (`ensure_tesseract_configured`, `ocr_text`)
  as a native binary dependency (installed via `apt-get install
  tesseract-ocr` in the drafted Dockerfile). **This is the single most
  important constraint on hosting choice**: it rules out pure V8-isolate /
  edge-function runtimes (Cloudflare Workers, Vercel Edge Functions, Deno
  Deploy, Netlify Edge Functions) for the backend as it exists today,
  because those runtimes cannot exec a native OS binary. Any option that
  wants to run today's FastAPI+Tesseract backend as-is needs a real Linux
  container (Docker) or a container-capable serverless product (Cloud Run,
  App Runner, Fly Machines, Render, Railway) — not a JS-isolate edge
  function. The alternative is dropping Tesseract from the public web
  deploy and running Claude-vision-only there, but that reopens the
  unmetered-billing risk `ClaudePlans/2026-09-18-web-beta-deployment.md`
  already flagged and explicitly deferred until real cost-gating exists.
- **`workers/scan-proxy/`** (Cloudflare Worker, already deployed, live at
  `rigcheck-scan-proxy.wanderingtrailswaggingtails.workers.dev`) is the only
  piece of this system that already does charge-before-call cost-gating. It
  holds **no database of its own** — RevenueCat's Virtual Currency API is
  the ledger — and `request.ts` accepts `app_user_id` as a bare
  caller-supplied string with **no signed-token verification**
  (`ARCHIVE_MONETIZATION.md`'s "Known v1 gap, accepted on purpose"). This is
  a real constraint on the future shared system: whatever backend ends up
  authenticating Web+Android users needs to issue and verify real
  session/JWT tokens, not accept an asserted ID — otherwise the same
  spoofable-identity gap just gets inherited by a bigger, real-money
  surface (Stripe + shared credit balances) instead of staying contained to
  Android's smaller blast radius.
- **The future system** (per `NEXT_STEPS.md` item #20 and
  `DESIGN_BRIEF.md`) needs, concretely: user accounts (email+password +
  Google/Apple OAuth), a credit-balance/subscription store, sessions, and
  two independent payment webhook sources (Stripe for Web, RevenueCat for
  Android) landing in one place that both platforms' clients can query for
  "what does this user currently have."
- Streamlit (`streamlit_app/`) and Android/`scan-proxy` are explicitly
  out of scope — nothing below touches them, though Options touching
  Cloudflare note the existing Worker for context only, per the
  instruction not to weight Cloudflare higher just because it's already in
  use there.

## 3. Options at a glance

| Option | Label | Automation axis | ~Monthly cost today | Backend fit |
|---|---|---|---|---|
| A. Render | **Fastest-to-market** | CI/CD + managed compute | $0 (free web service) | Docker, native Tesseract — direct fit |
| B. Google Cloud Run + Neon | **Lowest-cost** | CI/CD (via Cloud Build/GitHub Action) + fully serverless | $0 (real always-free tier) | Docker container — direct fit |
| C. Railway Pro | **~$25/month tier** | CI/CD + managed compute | ~$20-25/mo (usage-credit model) | Docker/Nixpacks — direct fit |
| D. Supabase (BaaS) + a container host | Differentiated: DB/auth-first | CI/CD (frontend) + managed compute (backend) | $0 to start | Decouples DB/auth from compute entirely |
| E. Cloudflare Pages + Workers + D1 | Differentiated: edge/serverless-native | CI/CD + fully serverless (edge) | $0 to start | **Does not fit Tesseract as-is** — real constraint, not just a footnote |

All pricing below was checked live in September 2026 (sources cited inline)
against a January 2026 knowledge cutoff, per the instruction to verify
rather than recall — vendor free tiers move fast and at least two vendors
here (Fly.io, Render) have changed their free-tier terms materially within
the last two years.

---

## Option A — Render (Fastest-to-market)

**What it is.** A PaaS that runs your own `Dockerfile` (or native
buildpacks) as a managed "web service," plus optional managed
Postgres/Redis, with push-to-deploy from a connected GitHub branch built
in from day one.

**Current pricing (checked Sept 2026).** Free web services get 750
instance-hours/month, 512 MB RAM, 0.1 CPU, 100 GB outbound bandwidth, and
500 build-pipeline minutes — no credit card required. Free services spin
down after 15 minutes idle and cold-start in 30-60 seconds on the next
request. Paid "Starter" is $7/month (0.5 vCPU / 512 MB, always-on, no
spin-down); "Standard" is $25/month (1 vCPU / 2 GB RAM) — this is the
option used for the $25/month comparison point (Option C) rather than
double-counting Render at two tiers. **Real gotcha for the future DB**:
Render's free managed Postgres **expires 30 days after creation**, with a
14-day grace period to upgrade before Render deletes it and all its data —
this is not a permanent free database, only a 30-44 day trial of one.
(Sources: [Render pricing](https://render.com/pricing), [Render free-tier
deploy docs](https://render.com/docs/free), [Render changelog: free
Postgres now expires after 30 days](https://render.com/changelog/free-postgresql-instances-now-expire-after-30-days-previously-90),
[Render compute plans](https://render.com/docs/compute-plans).)

**Automation axis.** Both: GitHub-connected push-to-deploy, and no server
to patch/provision — Render manages the VM underneath the container.

**How the current app deploys.** This is exactly the shape
`ClaudePlans/2026-09-18-web-beta-deployment.md` already drafted (Dockerfile
with a Node build stage for `web/dist` + a Python stage installing
`tesseract-ocr` via `apt-get`, `main.py` mounting the built SPA as static
files, a `render.yaml` describing one Docker web service with health check
`/health`). That plan's Docker/Render technical content is still directly
usable; only its subdomain-pointing step (step 6) is now explicitly not
wanted — the `*.onrender.com` URL itself becomes the thing that's linked
from the existing site, and steps 1-5 and 7 stand unchanged. This is the
single least-new-work path to a live URL today, which is why it's the
fastest-to-market pick.

**Where the future DB lives.** Render's own managed Postgres is fine for
early development, but its 30-day free expiry means it's not a place to
put real user data before paying $7-19/month for a persistent Postgres
instance — otherwise use an external managed Postgres (Neon, Supabase) and
just point the same FastAPI app at it via `DATABASE_URL`, which works
identically on Render.

**Entitlement source-of-truth angle.** Render is a plain compute host —
it has no opinion on auth or payments. That's a feature here: it doesn't
bias the answer either way. A FastAPI backend running on Render can equally
well (a) call out to RevenueCat's API as the source of truth and treat
Stripe webhooks as just another writer into a thin reconciliation table, or
(b) own a real `entitlements` table in its own Postgres and treat both
RevenueCat and Stripe webhooks as payment rails feeding into it. Because
the backend code is a normal FastAPI app you fully control (not a vendor's
opinionated backend framework), **both answers to the entitlement question
are equally easy to build here** — Render doesn't push you toward either.
The cost is that you build both the webhook-receiving endpoints and
whatever reconciliation logic you choose yourself; nothing is bundled.

---

## Option B — Google Cloud Run + Neon Postgres (Lowest-cost)

**What it is.** Cloud Run is Google Cloud's fully serverless container
platform — you push a container image (from your own `Dockerfile`), it
scales to zero when idle and back up on request, and you're billed only
for actual request-handling time. Because it runs arbitrary Linux
containers (not a JS isolate), it can install and exec Tesseract exactly
like Render can.

**Current pricing (checked Sept 2026).** Cloud Run's "always free" tier
(not a time-limited trial) includes 2 million requests/month, 360,000
GiB-seconds of memory, 180,000 vCPU-seconds of compute, and some free
egress, every month, indefinitely. At RigCheck's beta traffic level this
is very likely to cost **$0/month indefinitely**, not just during a trial
window — a materially different guarantee than Render's spin-down free
tier or Railway's credit-based free tier. (Source: [Cloud Run
pricing](https://cloud.google.com/run/pricing).) The real friction: Cloud
Run requires a GCP **billing account with a credit card on file** even to
use the free allocation (unlike Render's card-free free tier) — you won't
be charged while under the free thresholds, but the account setup itself
has more steps. Cloud Run has **no bundled free database** — Cloud SQL
(Google's managed Postgres) has no meaningful free tier, so the
lowest-cost pairing is Cloud Run for compute + an external free Postgres.
**Neon** fits well here: free tier gives 0.5 GB storage per project, up to
100 projects, 10 branches/project, and 100 compute-hours/month with
autoscale-to-zero after 5 minutes idle (source: [Neon
plans](https://neon.com/docs/introduction/plans)) — genuinely free at this
scale, no expiry clock like Render's free Postgres.

**Automation axis.** Both: Cloud Build or a GitHub Action can push-to-deploy
on every commit, and Cloud Run itself is the "no server to provision or
patch" definition of managed serverless compute.

**How the current app deploys.** Same Dockerfile as Option A (Node build
stage → `web/dist`, Python stage with `apt-get install tesseract-ocr`,
`uvicorn` as the entrypoint) — `gcloud run deploy` or a GitHub Action
builds and pushes it. No code change beyond what Option A already needs.

**Where the future DB lives.** External (Neon or Supabase Postgres, both
have durable free tiers), reached over its connection string — Cloud Run
containers are stateless and short-lived by design, so the database was
always going to live somewhere else regardless of compute host.

**Entitlement source-of-truth angle.** Structurally identical to Option A
for this question — Cloud Run is also just a container host with no
opinion on auth/payments, so it's equally compatible with "RevenueCat stays
source-of-truth + Stripe reconciled in" or "one owned Postgres becomes
source-of-truth for both rails." The main practical difference from Render
is operational: GCP's IAM/service-account model and Cloud Console add real
learning-curve overhead for solo/small-team ops that Render's simpler
dashboard avoids — worth weighing against the stronger, indefinite free
tier. If minimizing new platform surface area matters more than saving the
last few dollars, this is the tradeoff to have consciously.

---

## Option C — Railway Pro (~$25/month tier)

**What it is.** A PaaS similar in shape to Render (Docker or Nixpacks
build, push-to-deploy from GitHub, "Pro" workspace plan), but priced as a
monthly **usage-credit allowance** rather than fixed per-service tiers —
you get a pool of credit each month and pay per-second for actual
CPU/RAM/egress consumption beyond it.

**Current pricing (checked Sept 2026).** A no-card "Free Trial" grants a
one-time $5 credit (30 days); after that, a bare "Free" plan exists at
$0/month with a $1/month credit (enough only for a minimal always-idle
service); "Hobby" is $5/month including $5 of usage credit; **"Pro" is
$20/month including $20 of monthly usage credit**, with per-second charges
beyond that (~$10/GB-month memory, ~$20/vCPU-month, $0.05/GB egress) —
close enough to the requested ~$25/month range once a real workload and a
small Postgres add-on are running, since the included credit is consumed
by actual usage rather than being a flat allowance on top of a fixed fee.
(Source: [Railway pricing](https://railway.com/pricing).) Unlike Render,
Railway's plan fee is a **spending floor, not a flat rate** — if usage is
lighter than $20/month, you still pay $20; if heavier, you pay more. This
makes it a genuinely different cost *shape* from Render's Standard tier
(fixed $25 regardless of usage) even though the sticker price lands in the
same neighborhood, which is the actual point of including this option
alongside the free ones: it shows what "always-on, real headroom, plus a
first-party database in the same billing relationship" costs in practice.

**Automation axis.** Both — GitHub push-to-deploy plus fully managed
compute, same shape as Render.

**How the current app deploys.** Same Dockerfile as Options A/B; Railway
also auto-detects and builds many stacks without a Dockerfile via
Nixpacks, but the existing Dockerfile (once written per the 2026-09-18
plan) works unmodified. A first-party Postgres plugin can be added from
Railway's own dashboard in the same project, billed from the same $20
credit pool.

**Where the future DB lives.** Railway's own Postgres plugin, in the same
project/workspace as the backend — this is the practical advantage of the
$25/month tier over the free options: one bill, one dashboard, a database
with no 30-day free-tier expiry clock (Render's free-Postgres gotcha) and
headroom the free options' RAM/CPU/storage caps don't give.

**Entitlement source-of-truth angle.** Same underlying answer as Options A
and B — Railway is a compute+DB host, not an auth/payments product, so it
doesn't push the entitlement decision either way. What the extra budget
buys specifically for *this* question is operational headroom for the
reconciliation logic itself: a real always-on Postgres (not a 30-day free
one) is where a "webhooks-in, one entitlements table" design would live if
that's the direction chosen, and $20-25/month of guaranteed compute means
that reconciliation job (whatever polls/listens for both Stripe and
RevenueCat webhooks) isn't competing for cold-start-prone free-tier
resources at the exact moment a real payment event needs to be processed
correctly. If the answer to the source-of-truth question ends up being
"build our own," this tier is closer to what that actually requires
day-to-day than any of the free options.

---

## Option D — Supabase (BaaS) + a container host for the FastAPI backend (Differentiated: DB/auth-first)

**What it is.** A fundamentally different shape from A-C: instead of
picking a compute host and bolting on a database later, you start from a
backend-as-a-service that bundles Postgres + Auth + Storage + (Deno-based)
Edge Functions in one project, and put your own compute (Render, Cloud
Run, or Railway from above, or Fly.io) in front of or alongside it only for
the parts Supabase doesn't do — namely, running the existing Python/Tesseract
FastAPI app, since Supabase Edge Functions are Deno/TypeScript, not Python.

**Current pricing (checked Sept 2026).** Free tier: 500 MB database
storage, 1 GB file storage, 5 GB egress, up to 2 active projects, 50,000
monthly active users on Auth, 500,000 Edge Function invocations, unlimited
API requests — but **free projects pause after 7 days of inactivity** and
there are no automatic backups on the free plan. Pro is $25/month per
project, adding backups, higher MAU limits, and removing the pause-on-idle
behavior. (Source: [Supabase pricing](https://supabase.com/pricing).)
Frontend hosting (Vercel, Netlify, or Cloudflare Pages, any of which are
free for a static Vite build) is a separate, essentially free add-on to
this option, so it's the FastAPI compute host — not Supabase itself — that
carries whatever cost Option A/B/C already established.

**Automation axis.** Push-to-deploy for both halves (Supabase migrations
can be scripted/CI'd; the frontend host and the FastAPI host both deploy
on push), and Supabase's own pieces (Auth, Postgres, Storage) are fully
managed with zero servers to provision — but the FastAPI/Tesseract half
still needs one of Options A/B/C's container hosts underneath it, so this
option doesn't reduce the number of moving parts, it reallocates them.

**How the current app deploys.** React frontend → any static host, calling
a `VITE_API_BASE_URL` environment variable pointed at wherever FastAPI
runs (Cloudflare Pages/Vercel/Netlify all support this same pattern) —
this is the CORS-opening path `main.py:35`'s current
`http://localhost:5173`-only origin list would need to grow to accommodate.
FastAPI itself still deploys exactly as in Option A/B/C (same Dockerfile),
but now talks to Supabase's Postgres via `DATABASE_URL` and verifies
Supabase-issued JWTs for auth instead of managing sessions itself.

**Where the future DB lives.** This is the point of the option: the future
users/credit-balances/sessions database *is* Supabase Postgres from day
one, and Supabase Auth (which already supports email+password plus Google
and Apple OAuth out of the box — exactly the methods `DESIGN_BRIEF.md`
specifies) replaces the "hand-roll sessions, password reset, email
verification" ~1-2 week estimate in `NEXT_STEPS.md` item #20 with
integration work instead of from-scratch build work.

**Entitlement source-of-truth angle.** This is the strongest option for
**deliberately choosing "unified system, not RevenueCat" early**, because
the schema and auth already exist in one place before payments are even
wired up: Stripe webhooks and a RevenueCat webhook (RevenueCat supports
outbound webhooks on entitlement/purchase events) both become Supabase
Edge Functions (or a FastAPI endpoint, since the backend already exists)
that write into one `entitlements`/`credit_balances` table keyed by the
same Supabase user ID for both platforms — directly matching
`DESIGN_BRIEF.md`'s "one account works on both platforms" framing and
giving both Android and Web a single place to read "what does this user
currently have" instead of asking two different vendors and reconciling
client-side. The tradeoff: this *is* the harder path the item #20 writeup
already flagged as the harder-but-chosen direction for the account system
overall — Supabase gives you the storage and auth primitives, but you
still write and own the reconciliation logic for two independent webhook
sources that can race, retry, and disagree (a duplicate Stripe webhook
delivery and a delayed RevenueCat one both landing near-simultaneously,
for instance) — Supabase does not solve that for you, it just gives you a
good place to build it. If the answer instead ends up being "keep
RevenueCat as source of truth, treat Stripe as a thinner rail reporting
into it," Supabase still works fine as the users/sessions store, but its
Postgres becomes a read cache of RevenueCat's ledger rather than the
ledger itself — also workable, just a different design center than the
one this option makes easiest.

---

## Option E — Cloudflare Pages + Workers + D1 (Differentiated: fully edge-native)

**What it is.** The single-vendor, fully serverless/edge model: static
frontend on Pages, API logic in Workers (V8 isolates, not containers), and
D1 (Cloudflare's SQLite-based serverless database) for storage — the same
platform family `workers/scan-proxy/` already runs on, evaluated here on
equal footing per the instruction not to weight it higher for that reason.

**Current pricing (checked Sept 2026).** Pages free tier: 500 builds/month,
unlimited bandwidth for static assets, free custom domains. Workers free
tier: 100,000 requests/day, 10ms CPU time per invocation. D1 free tier: 5
GB storage, 5 million rows read/day, 100,000 rows written/day — and as of
September 2026 D1 queries that exceed the daily row limits **fail outright
rather than degrading gracefully**, a recent tightening worth knowing about
before relying on it for a production entitlement store. Workers Paid plan
(needed once request/CPU-time limits are exceeded, or for Durable Objects)
has a $5/month minimum. (Sources: [Cloudflare Workers
pricing](https://developers.cloudflare.com/workers/platform/pricing/),
[Cloudflare D1 pricing](https://developers.cloudflare.com/d1/platform/pricing/).)

**Automation axis.** Both — GitHub-connected push-to-deploy for both Pages
and Workers, and there is no server concept at all, only edge functions.

**How the current app deploys — the real limitation.** The React frontend
maps cleanly onto Pages (a straightforward static Vite build, same as any
static host). **The FastAPI + Tesseract backend does not map onto Workers
as it exists today** — Workers run in a V8 isolate sandbox with no ability
to exec a native `tesseract` binary or run a CPython/FastAPI process (there
is a Python-on-Workers offering via Pyodide, but it runs pure-Python code
inside the isolate, not arbitrary OS binaries, and does not currently
support the OCR C library `pytesseract` shells out to). Making this option
work for real would mean either (a) rewriting the OCR extraction logic in
TypeScript inside a Worker against a different OCR approach entirely, (b)
dropping Tesseract from the web path and using Claude-vision-only inside
the Worker (structurally close to what `scan-proxy` already does for
Android, but reopens the same unmetered-billing risk the 2026-09-18 plan
deferred), or (c) keeping this option's Pages+Workers+D1 stack for the
*frontend and future accounts system* while the OCR backend stays on one
of Options A/B/C's container hosts — a hybrid, not a pure single-vendor
deploy. This is a materially bigger lift than any other option here, which
is exactly why it's presented as a differentiated architecture rather than
a peer cost comparison.

**Where the future DB lives.** D1, colocated with the Workers that would
handle auth/webhooks — genuinely convenient if the OCR-backend problem
above is solved by keeping OCR elsewhere and using this stack only for
accounts/payments/edge API routes.

**Entitlement source-of-truth angle.** If the OCR question above is solved
(most realistically via hybrid option (c)), this stack is a strong fit for
a **unified, owned entitlement store** for the same reason Option D is:
Stripe and RevenueCat webhooks both terminate in Workers functions writing
into one D1 table, with Workers' low latency making it a genuinely good
fit for the "check entitlement before every scan" gating pattern
`scan-proxy` already proves out for Android — this option could plausibly
absorb `scan-proxy`'s own logic directly, since both would live on the
same platform, which is an operational simplification the other options
don't offer (one fewer vendor overall, since Cloudflare is already in the
stack for Android). Against that: D1's newly-strict daily row-limit
cutoffs (noted above) are a real risk to evaluate carefully before trusting
it with money-adjacent data at any scale beyond a small beta, and the OCR
backend problem means this can never be a clean single-vendor answer for
the *whole* app the way Options A-C are — only for the accounts/payments
slice of it.

---

## 4. Direct comparison on the entitlement question

Across all five options, the hosting choice itself is close to neutral on
*whether* to unify entitlement into one owned store versus keeping
RevenueCat as source-of-truth with Stripe reconciled in — that's a design
decision the team makes regardless of host. Where hosting choice actually
matters is in **how much scaffolding already exists toward each answer**:

- **Options A, B, C** (Render / Cloud Run / Railway) are blank compute —
  equally easy to point at either answer, because you write 100% of the
  auth/webhook/reconciliation code yourself either way. Pick based on
  cost/ops preferences, not this question.
- **Option D** (Supabase) actively leans toward the "one unified system"
  answer, because the users table, auth, and a natural home for a
  `credit_balances`/`entitlements` table already exist together before any
  payment code is written — it's the path of least resistance toward
  *not* leaving RevenueCat as the sole source of truth.
- **Option E** (Cloudflare full-stack) leans the same direction as D for
  the same structural reason, with the added incentive of collapsing
  `scan-proxy` into the same platform — but only once/if the OCR-hosting
  problem is solved separately.

If the team already knows it wants to end up with "one database we own is
the real source of truth, RevenueCat and Stripe are just payment rails
feeding it," Options D or E make that the *default*, easy path. If the
team wants to defer that decision and keep options open, Options A/B/C are
equally neutral and cheaper/simpler to start with.

## 5. Recommendation

This is input to the decision, not a decision already made.

**For getting the web app live now**: Option A (Render) is the
recommendation to start with. It requires the least new work (the
Dockerfile/render.yaml plan already drafted in
`ClaudePlans/2026-09-18-web-beta-deployment.md` is still valid, minus its
subdomain step), it's genuinely free at beta scale, and — importantly —
it doesn't foreclose either answer to the entitlement question later,
since it's just a compute host. If the free tier's 30-60s cold starts turn
out to be a real user-experience problem once the beta is being actively
linked to, the $7/month Starter tier removes them without any
architecture change.

**For the future shared-accounts system**: worth seriously evaluating
Option D (Supabase) *specifically because* `NEXT_STEPS.md` item #20
already frames "one shared account system, the harder path" as the
deliberate choice — Supabase's bundled Auth (with Google/Apple already
built in) directly removes the ~1-2 week hand-rolled-auth estimate from
that item's own scope writeup, and its Postgres gives the "one unified
entitlements table" answer to the source-of-truth question a natural home
if that ends up being the preferred design. This doesn't have to be an
either/or with Render — the recommended near-term path (Render for
compute) and the recommended medium-term path (Supabase for auth/DB) can
run side by side, with the FastAPI app on Render calling out to Supabase
for user/entitlement data once that phase starts, which is exactly Option
D's architecture. Cloud Run (Option B) remains worth a look if indefinite
$0 cost matters more than avoiding GCP's extra setup friction — it doesn't
change this recommendation, it's a lower-friction-cost/higher-setup-cost
variant of the same "neutral compute host" shape as Render.

**Not recommended as a starting point**: Option E (Cloudflare full-stack),
specifically because of the Tesseract/Workers mismatch — it's worth
revisiting later if the OCR backend question gets resolved independently
(e.g., if the web tier ever moves to Claude-vision-only with real
cost-gating), at which point it becomes a genuinely strong contender for
the accounts/payments slice given the natural fit with the already-live
`scan-proxy` Worker. **See the addendum below** — this "resolved
independently" condition is exactly the change discussed there.

## 6. Addendum (2026-09-21): dropping Tesseract, Claude-vision-only OCR

A follow-up question after this report: what changes if Tesseract is
removed entirely and Claude-vision (`HDTTOOLS_OCR_BACKEND=claude`, already
a working code path per `NEXT_STEPS.md` item #16) becomes the *only* OCR
backend on both platforms — meaning the free tier drops photo-scanning
altogether and offers manual entry only (0 scan credits by default), with
every scan on either platform going through a paid, gated Claude-vision
call. This is a real product-scope change (free users lose "photograph it
and we'll read it" entirely, not just a cheaper version of it) — that
trade-off is outside this document's scope, which stays focused on what it
changes for hosting and the entitlement question.

**What actually changes technically.** The backend stops shelling out to a
native binary and becomes pure network I/O: receive an image, call
Anthropic's API over HTTPS, parse the response, return fields. Two
consequences:

1. **Section 2's "single most important constraint" goes away.** That
   constraint was specifically Tesseract's native-binary requirement ruling
   out V8-isolate/edge runtimes. Without it, the backend logic is thin
   enough to actually run in a Worker/edge function — no more forced choice
   between "real container" and "no OCR."
2. **Web's scan path becomes the same shape as `workers/scan-proxy`
   already is for Android**: check a credit, call Claude, deduct, return.
   Right now Web (free local Tesseract) and Android (gated paid
   Claude-vision) have two differently-shaped OCR systems; this change
   makes every platform's *scanning* feature identical in structure,
   leaving only manual entry + breakdown math as the genuinely-stateless,
   OCR-free path.

**Effect on each option above:**

- **Options A, B, C (Render / Cloud Run / Railway)**: marginal
  improvement, not a change of verdict. Smaller Docker images (no
  `apt-get install tesseract-ocr` layer), faster cold starts, one fewer
  "wrong binary path on this host" failure class (this project has
  already hit real Tesseract-path gotchas per `DEV_ENVIRONMENT.md`). These
  options were never blocked by Tesseract, so removing it makes them
  slightly nicer, not newly viable.
- **Option D (Supabase)**: no material change — Supabase Edge Functions
  are already Deno/TypeScript regardless of what the Python backend does,
  so this doesn't newly unlock anything there; the FastAPI half still
  needs a container host either way (now an even lighter one).
- **Option E (Cloudflare full-stack) — this is the option that actually
  moves.** The disqualifying constraint from Section 3(E) is gone: without
  Tesseract, there's no native binary a Worker needs to exec. Getting
  there for real still means rewriting the OCR-calling/gating logic in
  TypeScript to run natively on Workers (Cloudflare's Python-on-Workers
  support still doesn't cover arbitrary native deps or a real FastAPI
  process) — so it's "the blocker is removed," not "it's now zero-work" —
  but this changes Option E from "not recommended as a starting point" to
  a genuine single-vendor contender for the *whole* app, not just the
  accounts/payments slice as previously scoped. Practically, this could
  mean **generalizing `scan-proxy` itself** into the one shared
  scan-gating Worker for both platforms, rather than building a second,
  separate cost-gating mechanism for Web as item #20 originally assumed
  would be necessary ("`scan-proxy`'s code isn't reusable as-is").

**Effect on the entitlement source-of-truth question.** This is the more
important shift. Once every scan (both platforms) funnels through one
logical operation — verify identity, check/deduct a credit, call Claude —
that operation becomes the natural place to meter usage regardless of
whether the credit came from RevenueCat or Stripe. That's a real, concrete
argument for **unifying at least the metering/credit-deduction layer**
into one shared service, even before the larger question of subscription
management/billing source-of-truth is settled. It doesn't resolve
Section 4's broader question (Options A/B/C are still neutral hosts for
whatever the team decides), but it does mean the *scanning* slice of the
system stops being two different implementations that both need to agree
with whatever entitlement answer gets chosen, and starts being one
implementation both platforms call into — narrowing the surface area the
eventual reconciliation design has to cover.

**One thing this raises the stakes on, not lowers**: with no free local
OCR fallback, every scan costs real Anthropic money from the first request
on any platform, with no soft-launch option. The credit-check has to be
correct before scanning goes live anywhere, not deferrable the way
`HDTTOOLS_OCR_BACKEND=claude` being technically available but practically
ungated is deferrable today.

**See also**: `ClaudePlans/2026-09-21-entitlement-and-scan-gating-unification-impacts.md`
goes one level more concrete than this addendum — for both the entitlement
source-of-truth question and the scan-gating unification question raised
above, it walks through exactly what changes in Android's code vs. Web's
code under each real option, plus a recommendation.
