# RigCheck scan-proxy (Cloudflare Worker)

Server-side proxy for the Android app's paid "scan instead of type" feature.
Holds `ANTHROPIC_API_KEY` (which can never ship inside the app) and charges
one RevenueCat virtual-currency credit per scan before calling Claude
vision. See `ARCHIVE_MONETIZATION.md` at the repo root for the full
monetization design thread this implements.

## What it does

`POST /v1/scan` with a photo of a truck tag, trailer tag, or scale ticket
returns the same structured fields the desktop app's OCR path produces
(`src/hdttools/truck_tag.py` / `trailer_tag.py` / `scale_ticket.py`) — this
Worker ports those exact prompts/schemas to TypeScript
(`src/docTypes.ts`) so both extraction paths agree on field names.

**Request:**
Header: `Authorization: Bearer <account token>` (a signed-in user's Supabase
access token — see **Auth** below). Any `app_user_id` in the body is ignored.

```json
{
  "doc_type": "truck_tag" | "trailer_tag" | "scale_ticket",
  "image_base64": "...",
  "media_type": "image/jpeg",
  "client_request_id": "optional - see Idempotency below"
}
```

**Success (200):** `{ "ok": true, "doc_type": "...", "fields": { ... } }`

**Errors:**
- `401` `unauthorized` — missing, malformed, expired or wrongly-signed account
  token (or an anonymous Supabase user); nothing was charged
- `503` `auth_unavailable` — couldn't load Supabase's signing keys; retry later
- `402` `insufficient_credits` — no credits left, nothing was charged
- `502` `extraction_failed` — Claude couldn't read the image (including a
  timed-out call); the credit was refunded
- `502` `billing_error` — couldn't reach RevenueCat, including a timed-out
  request (spending never happened, so nothing to refund)
- `400` `bad_request` — malformed request

**CORS.** The Web app calls this endpoint from the browser, from another
origin. `OPTIONS /v1/scan` is answered `204` without authentication, and every
response (errors included, so the page can read them) carries
`Access-Control-Allow-Origin: *`. Any origin is fine because the account token
is a bearer header the browser never attaches by itself (no cookies); the token,
not the origin, is what authorises a scan. Android is unaffected.

**Timeouts.** Both outbound calls are bounded so a hung upstream returns a
clean error instead of tying up the Worker until Cloudflare's platform
execution limit kills it: the Anthropic call (`src/claude.ts`) times out at
20s (`ANTHROPIC_TIMEOUT_MS`) — shorter than the Android client's own 60s
read timeout, or a Worker-side timeout would never fire first. The
RevenueCat call (`src/revenuecat.ts`) times out at 10s
(`REVENUECAT_TIMEOUT_MS`), tighter since it's a simple ledger write.

**Idempotency.** `client_request_id` is an optional, client-generated id,
stable across retries of the same logical scan attempt (the Android app
generates one UUID per user-initiated tap), at most 128 characters of
letters, digits, `-`, `_`, `.` or `:` (anything else is a `400`). The
RevenueCat `Idempotency-Key` is never the raw id: the Worker takes a SHA-256
of the verified account id, document type, media type, a hash of the image
and the id (`src/idempotencyKey.ts`), so one id sent with a different image,
document type or account is a separate charge, and the refund's key (that
hash plus `-refund`) can't equal any other request's spend key. A retry of
the same request after a lost/timed-out response still spends the credit at
most once — verified hands-on against the real deployed Worker and real
RevenueCat (two identical scans with the same `client_request_id` moved the
balance by exactly 1). Omitting the id falls back to a fresh random one per
request, the original behavior, so any already-shipped app build stays
compatible.
**Known gap (follow-up ticket)**: the key protects the credit balance, but
the Worker is deliberately stateless (see "No database" below) and
RevenueCat tells it nothing about a replayed key, so resending the exact
same request (same account, type, image and id) is answered as paid and
re-runs Claude each time. A direct API caller with one credit can use that
to buy repeated billed extractions of one image, and if a repeat's
extraction fails, the refund credits back a scan that was delivered. The
mirror case also holds: if the first attempt's extraction fails and is
refunded, an honest retry replays the Spend and is extracted at no net
credit. The
shipped clients send a fresh id per tap, so only a hostile direct caller
reaches it. Closing it needs a server-side record of completed scans
(Workers KV, or a single-use scan token); that decision is tracked in
#96 rather than made here.

## Testing

Unit tests for the request validation, RevenueCat request-shaping, doc-type
schema integrity, and — most importantly — the charge/extract/refund
control flow all run with **nothing installed**, via Node's built-in test
runner:

```bash
npm test          # or: node --test
```

This works because `src/scan.ts` (the charge → extract → refund logic)
takes its `spendCredit`/`refundCredit`/`extractFields` as injectable deps
and only loads `claude.ts` (and the Anthropic SDK it needs) lazily, on
first real use — so the tests can swap in fakes and never touch the SDK,
RevenueCat, or the network. See `src/scan.test.ts` for the cases that
matter most: a zero-credit user never reaches Claude, a failed extraction
refunds the same user exactly once, a failed refund attempt doesn't
crash the request, a `spendCredit` rejection (what a real timeout
eventually produces) maps to a clean `billing_error` instead of a hang,
and two calls sharing one `client_request_id` reuse the same idempotency
key, while a different image, document type or account under that id gets
its own.

What these tests *don't* cover: the real Anthropic SDK call shape, the real
RevenueCat API response shape (only the request side is asserted — the
mocked responses are hand-written, not verified against the live API), and
anything Workers-runtime-specific (KV, Durable Objects, etc. — this Worker
doesn't use any, so that gap doesn't currently matter). Full
runtime-accurate integration testing would use
`@cloudflare/vitest-pool-workers`, which does need `npm install` — worth
adding once this is closer to shipping, not before.

## Design notes

- **Charge first, refund on failure.** The Worker spends the credit via
  RevenueCat *before* calling Claude. RevenueCat returns `422` if the
  balance is insufficient, which doubles as the entitlement check — a
  user with 0 credits never triggers a (costly) Claude call. If Claude
  then fails to extract anything, the Worker refunds the credit so the
  user isn't billed for a failure that wasn't their fault.
- **No database.** RevenueCat's Virtual Currency feature holds the credit
  balance; this Worker is fully stateless.
- **Auth (#21).** Every scan must carry a Supabase access token (the
  **account token**). The Worker verifies its ES256 signature against the
  project's public JWKS (`<SUPABASE_URL>/auth/v1/.well-known/jwks.json`,
  cached per isolate; see "JWKS caching" below), then checks
  `exp`, `iss`, `aud` and that the user isn't anonymous, before the body is
  read or any credit is spent. The token's `sub` — the account id, which is
  also the RevenueCat app user id (spec #15) — is the customer that gets
  charged; `app_user_id` in the body is never read. There is no legacy
  path: the shipped Android build, which still sends `app_user_id`, is
  rejected until #22/#23 land. `SUPABASE_URL` is a public `[vars]` entry in
  `wrangler.toml`.
- **JWKS caching (#73).** Each isolate keeps the last key set per Supabase
  project (`src/auth.ts`):
  - **Max age: 10 minutes** (`JWKS_MAX_AGE_SECONDS`). Older keys are never
    trusted, so a key Supabase withdraws stops working within that time even
    in a long-lived isolate. If the re-fetch then fails, the request is
    `503 auth_unavailable`, not verified against stale keys.
  - **Re-fetch cooldown: 30 seconds** (`JWKS_REFETCH_COOLDOWN_SECONDS`). A
    token with an unknown `kid` makes the Worker re-fetch (Supabase may have
    rotated keys), but at most one fetch is *started* per project per
    window — failed fetches count — and requests arriving during a fetch
    share it. Inside the window an unknown `kid` is a plain `401`, so a
    token signed with a key published in the last 30 seconds can be refused
    until the window ends. With no trusted keys at all (a cold isolate whose
    fetch just failed) it is `503 auth_unavailable` instead.
  - The state is per isolate, so a caller spread across many isolates or
    locations still costs one fetch per window *per isolate*. This bounds the
    cost of random-`kid` requests; it is not a request rate limit (#98).
- **Model:** Haiku 4.5 (`src/claude.ts`) — structured extraction from a
  printed label is squarely its use case, and it's the cheapest tier.

## Setup

You'll need accounts on these services — creating them, agreeing to their
terms, and setting prices are business decisions only you can make:

1. **Cloudflare** — free tier is enough at this volume.
2. **RevenueCat** — create a project, define a virtual currency (this repo
   assumes the code `SCAN`, configurable in `wrangler.toml`), and create a
   secret API key with Read & Write on Customer Purchases
   Configuration + Customer Configuration.
3. **Anthropic** — an API key from the Anthropic Console (separate from
   any Claude.ai subscription).

Then, locally:

```bash
# 1. Install dependencies (wrangler + the Anthropic SDK). This is a
#    real install — confirm with yourself it's wanted before running it
#    on a space-constrained machine.
npm install

# 2. Authenticate the Cloudflare CLI (interactive browser login).
npx wrangler login

# 3. Store secrets (never commit these — wrangler stores them on
#    Cloudflare's side, not in this repo).
npx wrangler secret put ANTHROPIC_API_KEY
npx wrangler secret put REVENUECAT_SECRET_KEY

# 4. Edit wrangler.toml's [vars] with your actual REVENUECAT_PROJECT_ID.

# 5. Run locally against real secrets.
npm run dev

# 6. Ship it.
npm run deploy
```

## Not done yet

See `NEXT_STEPS.md` at the repo root — its roadmap and "🧪 Tests still
outstanding" sections are the maintained list of what testing is still
missing here and what unlocks each item; this README doesn't duplicate
it. Source code
only, nothing is deployed yet, and the Android app has no code calling
this endpoint.
