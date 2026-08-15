# RigCheck scan-proxy (Cloudflare Worker)

Server-side proxy for the Android app's paid "scan instead of type" feature.
Holds `ANTHROPIC_API_KEY` (which can never ship inside the app) and charges
one RevenueCat virtual-currency credit per scan before calling Claude
vision. See `NEXT_STEPS.md` at the repo root for the full monetization
design thread this implements.

## What it does

`POST /v1/scan` with a photo of a truck tag, trailer tag, or scale ticket
returns the same structured fields the desktop app's OCR path produces
(`src/hdttools/truck_tag.py` / `trailer_tag.py` / `scale_ticket.py`) — this
Worker ports those exact prompts/schemas to TypeScript
(`src/docTypes.ts`) so both extraction paths agree on field names.

**Request:**
```json
{
  "app_user_id": "the RevenueCat customer id (anonymous UUID the app generates)",
  "doc_type": "truck_tag" | "trailer_tag" | "scale_ticket",
  "image_base64": "...",
  "media_type": "image/jpeg"
}
```

**Success (200):** `{ "ok": true, "doc_type": "...", "fields": { ... } }`

**Errors:**
- `402` `insufficient_credits` — no credits left, nothing was charged
- `502` `extraction_failed` — Claude couldn't read the image; the credit was refunded
- `502` `billing_error` — couldn't reach RevenueCat
- `400` `bad_request` — malformed request

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
refunds the same user exactly once, and a failed refund attempt doesn't
crash the request.

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
- **v1 auth is intentionally light.** The Worker trusts whatever
  `app_user_id` the client sends — no signed token verifying the request
  actually came from that account. Accepted trade-off for now: someone
  who obtained another user's anonymous UUID could spend their credits,
  but there's no way to *discover* another user's UUID short of device
  compromise. Upgrade path if this ever matters: add Firebase
  Authentication and verify a signed ID token before touching RevenueCat.
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

See `NEXT_STEPS.md` at the repo root — its "🧪 Tests still outstanding"
section is the maintained list of what testing is still missing here and
what unlocks each item; this README doesn't duplicate it. Source code
only, nothing is deployed yet, and the Android app has no code calling
this endpoint.
