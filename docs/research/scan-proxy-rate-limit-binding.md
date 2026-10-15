# Scan service rate limiting: effort to add Cloudflare's Workers Rate Limiting binding

Findings for ticket #98 (follow-up to #96 and #97). Research only: no code was changed, no endpoint was called, nothing was deployed or spent.

Cloudflare claims are cited to the primary page and marked **Confirmed**, **Indirect** (only in first-party source code or a PR description) or **UNCONFIRMED**. The full evidence table, with every URL and the date each page was read (2026-10-14), is in [scan-proxy-rate-limit-binding-cloudflare-facts.md](scan-proxy-rate-limit-binding-cloudflare-facts.md); section numbers below point into it as "facts §N". Claims about this repo cite the file read.

## Recommendation (short)

**Build it, small. The `workers.dev` question is settled: the throwaway test ran on 2026-10-15 and the binding limits requests on a `workers.dev`-only Worker (see Q1), though loosely.** One limiter, keyed on the verified account id, checked after token verification and before the body is read, returning `429 rate_limited`. Roughly one day of work, no dashboard steps, no cost documented.

It bounds how fast one funded account can repeat `POST /v1/scan` (so it bounds how fast an abuser can burn the Anthropic budget). It does **not** replace the #97 spend cap, and it does not close the #96 replay gap (a replay inside the limit still runs a billed extraction). The dashboard WAF rule is not a workable substitute here. Details and the comparison table are in Q8.

## Q1. Availability and cost

| Question | Answer | Status |
| --- | --- | --- |
| Is the binding stable? | GA since 2025-09-19; the older `unsafe` form keeps working. https://developers.cloudflare.com/changelog/post/2025-09-19-ratelimit-workers-ga/ | Confirmed (facts §1) |
| Works for a Worker served only from `workers.dev`? | **Yes, observed 2026-10-15** (see "Test result" below). No Cloudflare page says so; the docs describe it as a Worker-runtime API with no zone or hostname prerequisite (https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/). | Confirmed by test; **UNCONFIRMED** in Cloudflare's docs |
| Plans that include it | Not stated on the binding page, the Workers pricing or limits pages, or the GA changelog. | **UNCONFIRMED** |
| Usage charge | None documented. The Worker invocation is billed as a normal Workers request whether or not the limiter rejects it. | **UNCONFIRMED** (no charge listed anywhere) |
| Limit on namespaces or bindings per Worker | None documented; the docs only say you can configure "multiple rate limiting configurations per Worker". | **UNCONFIRMED** |
| Visible in the dashboard? | No: "Rate limiting bindings are not currently visible in the Cloudflare dashboard." Use Workers Logs or Analytics Engine to see rejections. | Confirmed |

**Test result (run 2026-10-15 with the owner's approval).** A throwaway Worker `rl-throwaway-98` (`limit = 1`, `period = 60`, `namespace_id = "98980001"`, no routes, `workers.dev` only) was deployed to the owner's account on the same `workers.dev` subdomain as the Scan service, called, and deleted (the deployment was checked first and the delete confirmed). Wrangler 4.123.0 accepted the stanza and the deploy succeeded, which settles that the account's current plan can use the binding (the plan itself was not checked in the dashboard). Calls were answered by Cloudflare location `MCI`.

| Calls (all to one key, as fast as `curl` ran them) | Result |
| --- | --- |
| Key `t`, calls 1 and 2 | 200, 200 (the second was **not** limited) |
| Key `u`, call 1 | 200 |
| Empty key, calls 1 and 2 | 200, 200 (inconclusive for the empty-key question, given the line above) |
| Fresh key, 12 calls in a row | 200, 200, 200, 429, 429, 429, 200, 429, 429, 429, 429, 429 |

What it shows: 429s do appear, so the binding works on `workers.dev`. But with `limit = 1` it let 4 of 12 requests through within a few seconds, and the first three passed before the count caught up. That matches "permissive, eventually consistent" and means the limit is a deterrent, not a precise count: at N = 10 expect more than 10 in a burst. It does not change the recommendation. It does mean the limiter cannot be relied on to stop a short burst of parallel requests, only to bound the sustained rate. The empty-key and production window-type questions stay unsettled. No billing line was checked; the invocations were a handful of free-tier requests.

**Test the owner can run to settle `workers.dev`, plan and charge** (costs nothing beyond a throwaway Worker; already run, kept here so it can be repeated): deploy a Worker with the stanza from Q7, `limit = 1`, `period = 60`, a unique `namespace_id`, that returns 200 or 429 from `env.RL.limit({ key: "t" })`. Leave `workers_dev` on, no routes. Call its `https://<name>.<subdomain>.workers.dev/` twice within a few seconds. A 200 then a 429 settles that it works on `workers.dev` on the account's current plan; the deploy succeeding settles that the plan includes it. Check Billing > Billable usage a day later for any rate-limit line item. Delete the Worker afterwards.

## Q2. Fit for this abuse

The threat is one funded account, or one IP, repeating `POST /v1/scan`.

- **Counting is local to the Cloudflare location** the Worker runs in, per key, and is "permissive, eventually consistent, and intentionally designed to not be used as an accurate accounting system" (Confirmed, facts §2). Counters are updated asynchronously, so concurrent requests at the same instant can all pass before the count lands.
- **A caller hitting one location** gets roughly N successes per period. If the window is fixed, a burst straddling a boundary could pass up to about 2N. A third-party PR description says production uses a sliding window that skips the increment when over the limit (**Indirect**, facts §2, written by an AI agent; do not rely on it for the maths).
- **A caller spread across L locations** (a VPN, a mobile network, a deliberate attempt) gets up to N x L per period. No page guarantees a client always lands in the same location (**UNCONFIRMED**; test: log `request.cf.colo` from the Worker for a day).
- **Worked ceiling (illustrative).** Taking about $0.01 per Claude call (the `TESTING.md` figure, which #97 notes is unmeasured): N = 10 per 60 s lets one account at one location run about 600 extractions an hour, about $6 an hour. N = 10 per 10 s would allow 6 times that rate, so the 60 s period gives the tighter sustained ceiling for the same N; the 10 s period only suits a short-burst limit. Without a limit the only bound is how many parallel connections the attacker opens, because each scan holds the Worker for several seconds: 50 parallel loops (an arbitrary example) is on the order of 50 times a single loop. The limiter's value is capping that parallelism, not making abuse impossible.
- **The cost still lands.** The #97 Anthropic spend cap is the real backstop; the limiter makes reaching it slower, which buys time for the usage alert to fire.

## Q3. Key choice

| Key | Stops | Does not stop | Collateral risk |
| --- | --- | --- | --- |
| Verified account id (`sub` from the token) | The stated attack: one funded account repeating scans, including the #96 replay loop. Cannot be dodged by changing IP. | Many accounts (each needs a funded RevenueCat balance, so each costs the attacker a credit). Unauthenticated floods (they never reach the limiter). | A real user scanning several documents in a row; 10 per minute leaves room (a truck tag, trailer tag and scale ticket is 3). |
| Client IP (`CF-Connecting-IP`) | A single address flooding, before or after verification. | A botnet or rotating IPs. | Cloudflare's own docs advise **against** IP or location keys because many users share one (carrier-grade NAT, offices). A shared IP would throttle innocent users. |
| Both, as two limiters | Both of the above. | Same gaps. | Same IP collateral, and two bindings to tune. |

**Recommendation: account id only.** What an unauthenticated flood costs is Worker invocations (billed even when rejected), signature checks, and JWKS fetches. The JWKS fetches are already bounded by the 30 s per-isolate cooldown (README "JWKS caching (#73)"), and unauthenticated requests are refused with 401 before any credit or Claude call. An IP limiter would not reduce the invocation bill and adds the shared-IP collateral, so it is not worth a second binding. Flood protection at the edge is Cloudflare's DDoS layer's job.

**Never key on an unverified value.** Keying on the token's `sub` before the signature is checked, or on `app_user_id` or `client_request_id` from the body, would let anyone burn another user's bucket (a targeted denial of service). The key must come from `auth.userId` after `verifyAccountToken` succeeds.

## Q4. Where it sits in the request flow

Current flow (`workers/scan-proxy/src/index.ts`, `scan.ts`): `verifyAccountToken` (JWKS fetch, ES256 verify) -> `request.json()` -> `parseScanRequest` -> `runScan`: `spendCredit` (RevenueCat) -> `extractFields` (Claude) -> refund on failure.

| Placement | Protects | Verdict |
| --- | --- | --- |
| Before token verification | JWKS fetches and signature checks, but only with an IP key (no verified account yet). | Rejected: JWKS is already cooldown-bounded and the IP key has collateral (Q3). |
| **After verification, before the body is read** | Body parsing, RevenueCat Spend and refund calls, Claude calls. Keyed by the verified account. | **Recommended.** Cheapest rejection that has a trustworthy key. |
| After parsing, before the Spend | Same as above. | Works, but wastes parsing a multi-megabyte base64 body on a request that will be rejected. |

A rejected request never spends a credit: the check runs before `runScan`, so `spendCredit` is not reached. Add a test that asserts exactly that (Q6).

One design decision for the implementation: if `limit()` itself throws, fail **open** (log and allow) so a limiter fault cannot take scanning down. The binding is local, so this should be rare.

## Q5. Response contract

Proposed: `429` with `{ "ok": false, "code": "rate_limited", "message": "Too many scans in a short time. Wait a minute and try again." }` and a `Retry-After: 60` header (the period; the binding does not report time remaining). The existing `json()` helper in `http.ts` and `withCors` in `index.ts` carry the CORS header on it. `Retry-After` is not exposed to browser scripts without `Access-Control-Expose-Headers`; the Web client does not need to read it, so leave that out.

How the clients handle an unrecognised `429` today:

- **Android** (`ScanApiClient.kt`): reads `code` and `message` from any JSON error body and returns them as `ScanResult.Failure`; `RigCheckViewModel` shows the message verbatim. A well-formed `rate_limited` body therefore already shows the right text with **no Android change**. (It also calls `refreshCreditBalance()` for any code other than `insufficient_credits`; harmless.) A non-JSON 429, such as an HTML page from the Cloudflare edge, becomes `parse_error` "Could not parse the server's response."
- **Web** (`web/src/api.ts`, `scanError.ts`): only codes in the `MESSAGES` table (plus `bad_request`) get their own message. Any other code, including `rate_limited`, becomes `ScanError('unknown', NO_ANSWER, lostResponse = true)`: "We didn't get a usable answer ... a retry is not charged twice." That is misleading (nothing was charged and the request was refused), and it marks the attempt as a lost response. **Web needs a change**: add `rate_limited` to `ScanErrorCode` and `MESSAGES`, with `lostResponse = false`, and a test in `web/src/api.test.ts`.

Docs that list the error table and need a row: `workers/scan-proxy/README.md` ("Errors", the only full table). Docs that name individual codes and are worth a look: `workers/scan-proxy/CONTEXT.md` (the Entitlement entry, line 24, names `insufficient_credits`; a rate limit is not an entitlement, so it probably needs no change), `workers/scan-proxy/TESTING.md` (its case lists, for example the weekly 402 case around line 345, and a new case for the limiter) and `web/TESTING.md` (the `api.test.ts` row, around line 298). The Web `MESSAGES` table in `api.ts` cites the README "Errors" list as its source.

The Web app's `scan` wrapper in `App.tsx` only special-cases `insufficient_credits` and rethrows every other `ScanError`, so a new code needs no change there. `docs/test-audit/scan-proxy.md` is a generated audit report; leave it to the next audit run.

## Q6. Testing

- **Unit tests** use `node --test` against `worker.fetch(request, env)` with a plain `Env` object (`src/index.test.ts` line 17). The ticket suggests the injectable-deps pattern of `scan.ts`; `index.ts` has no deps parameter (only `runScan` and `verifyAccountToken` take one), and a binding already arrives on `env`, so this departs from that pattern on purpose. The limiter is an `Env` member, not a new dependency parameter, so the fake is `{ limit: async () => ({ success }) }` on the test `env`; no new injection pattern is needed. The existing `env` fixture and any other `Env` literal must gain the field (required in the type, so a missing binding fails typecheck).
- **`wrangler dev` simulates the binding** locally; Miniflare has had a first-party plugin since 2024-03 (Confirmed, facts §4). Counters now survive dev restarts within a window. The pinned wrangler (4.123.0) and miniflare in `package-lock.json` already include the later fixes. But `wrangler dev` here uses the real secrets and a real account token to get past verification, so a local run is a smoke check for the owner, not the proof.
- **`@cloudflare/vitest-pool-workers`** could exercise the real binding (`reset()` clears counters since 0.18.1), but the Worker's tests deliberately avoid a runtime pool today (README "Testing"). Not worth introducing for this.
- **No official docs page on testing the binding** (**UNCONFIRMED**); the only first-party examples are workers-sdk fixtures (facts §4).
- **Weekly and release suites.** `src/weekly/scan.weekly.test.ts` sends four sequential scans through the deployed Worker (one as the no-credits account, three as the funded one), each taking seconds; `src/release/scan.release.test.ts` calls RevenueCat and Anthropic directly and never goes through the Worker; the worker-token-verification External suite sends a few free requests. At 10 per 60 s per account none of them trips the limiter; a limit of 3 or less would. Keep N at 10 or more, and say so in the implementation ticket's acceptance criteria.
- **An optional live check** (not needed for the proof): as the no-credits account, where each request is a free 402, send 30 rapid requests and assert at least one `429`. The counter is eventually consistent, so assert "some 429 appears", never an exact request number.

## Q7. Tooling and deploy

- **Wrangler**: the stable `[[ratelimits]]` stanza needs 4.36.0 or later (Confirmed, facts §3). The lockfile already resolves 4.123.0. Raise the `package.json` range from `^4.0.0` to `^4.36.0` so the requirement is written down. This edits `workers/scan-proxy/package.json`, which is a dependency pin for the `worker-token-verification` External surface (`scripts/external_manifest/surfaces/worker-token-verification.json`), so that surface goes stale and the merge step must run its free suite. The planned (not yet active) `scan-proxy-worker` surface also lists `package.json`, `wrangler.toml` and `src/index.ts` as pins or boundary files, so it will matter once that surface is built.
- **`wrangler.toml`** (syntax Confirmed from the binding page):

  ```toml
  [[ratelimits]]
  name = "SCAN_RATE_LIMITER"
  namespace_id = "9801"        # string holding a positive integer, unique in the account

    [ratelimits.simple]
    limit = 10
    period = 60
  ```

  `namespace_id` is just a number you choose; there is no dashboard creation step (Indirect: Wrangler sends it inline in the upload). Two bindings with the same `namespace_id`, even in different Workers, share counters, so pick one unlikely to collide. `ratelimits` is not inherited by `[env.*]` blocks; this repo defines no environments.
- **`Env` type** (`src/types.ts`): add `SCAN_RATE_LIMITER: RateLimit;`. The `RateLimit` global comes from `@cloudflare/workers-types`, already a dev dependency (version 5.20260817.1 in the lockfile).
- **Owner dashboard steps**: none documented. The API token used by `wrangler deploy` is not known to need extra permission (**UNCONFIRMED**; a single deploy settles it, and an error would name the missing permission).
- **Deploys**: bindings are re-sent from `wrangler.toml` on every deploy, so `npm run deploy`, `pretest:weekly` and `release.ps1` need no change. Removing the stanza removes the binding.

## Q8. Alternatives side by side

| Option | What it stops | What it cannot stop | Owner effort | Code effort | Running cost |
| --- | --- | --- | --- | --- | --- |
| **Rate Limiting binding** | Per-account (or per-key) bursts at a location, before any RevenueCat or Claude call | A global ceiling (per-location counts, N x L across locations); exact accounting; replays inside the limit (#96) | Throwaway `workers.dev` test; no dashboard step documented | About 1 day (below) | None documented (**UNCONFIRMED**); invocation billed as usual |
| **Dashboard WAF rate limiting rule** (https://developers.cloudflare.com/waf/rate-limiting-rules/) | Per-IP bursts on a path, before the Worker runs, if a zone applies | Per-account limits; multi-IP abuse. Free plan: 1 rule, 10 s period, IP only, path and bot match only. Also counted per data center | Needs a domain on Cloudflare and a Worker route or custom domain; whether a rule can apply to `workers.dev` is **UNCONFIRMED** (inference: no, there is no zone) | None | Domain cost; no rule charge documented on Free |
| **Workers KV counter** (#96's option) | Coarse, slow limits | Bursts: reads up to 60 s or more stale elsewhere, no atomic increment, writes to one key limited to 1 per second; Free plan 1,000 writes a day | Create a namespace | Moderate | Free tier tiny; Paid $5 per million writes |
| **Durable Object per key** | Exact, global per-account limit; also a store for #96 dedupe | Floods before the Worker (each check is a billed DO request) | Add binding and a migration | Highest: class, migration, window logic, cleanup | Free plan allows SQLite-backed only (100k requests a day); Paid $0.15 per million requests |
| **Do nothing** | n/a | Everything; relies on #97 alone | None | None | Spend cap exhausted faster, hitting all users |

Sources: facts §5. Relationship to the other tickets:

- **#97 spend cap**: still the release gate and the only hard bound. The limiter slows spend, it does not cap it. Neither replaces the other.
- **#96 replay dedupe**: the limiter bounds the rate at which an account can replay, not the count. If the owner later wants replays closed, that needs a stored record (KV or a Durable Object); a Durable Object counter would serve both, so if both are wanted it may be cheaper to build one DO than the binding plus a KV record. That is a separate decision.

## Effort estimate for building the binding

Size: **about one day** including review (half a day of code and tests, half for docs, the Web change and the owner's smoke checks). The throwaway Worker test in Q1 has already been run.

| Area | Files |
| --- | --- |
| Worker code | `workers/scan-proxy/wrangler.toml`, `src/types.ts`, `src/index.ts` (check after `verifyAccountToken`); optionally a small `src/rateLimit.ts` and a `rateLimited()` helper in `src/http.ts` |
| Tooling | `workers/scan-proxy/package.json` and `package-lock.json` (`wrangler` range) |
| Web client | `web/src/scanError.ts`, `web/src/api.ts` |
| Tests | `workers/scan-proxy/src/index.test.ts` (new cases and the `env` fixture), `web/src/api.test.ts` (new case) |
| Docs | `workers/scan-proxy/README.md` (Errors, the "not a request rate limit (#98)" note in "JWKS caching", Design notes), `workers/scan-proxy/CONTEXT.md`, `workers/scan-proxy/TESTING.md`, `web/TESTING.md` |

Tests to add (write red first):

1. A limiter that returns `{ success: false }` gives `429`, `code: "rate_limited"`, a `Retry-After` header and the CORS header, and neither RevenueCat nor Anthropic is called (fakes record zero calls).
2. The key passed to `limit()` is the verified token's `sub`, even when the body names a different `app_user_id`.
3. A request with a bad or missing token gets `401` and the limiter is never called.
4. A request within the limit proceeds as today, with the limiter called once.
5. A limiter that throws lets the request through (if fail-open is chosen).
6. Web: a `429` body with `code: "rate_limited"` becomes a `ScanError` with that code, `lostResponse` false and the new message.

Owner steps: approve the deploy; choose N (the draft uses 10 per 60 s); after deploy, watch Workers Logs for rejections, since the dashboard shows none.

Main risks: counting is per location and eventually consistent, and the throwaway test showed it admitting 4 of 12 rapid requests at `limit = 1`, so the limit is a deterrent not a guarantee; N too low would throttle a legitimate burst or trip the weekly suite; the binding is invisible in the dashboard; a shared `namespace_id` would silently share counters.

## Questions left open, and why they do not block the build

Two questions stayed unsettled after the 2026-10-15 throwaway test. No other ticket tracks them (searched open and closed issues on 2026-10-15; only #98 and #114 mention rate limiting). They are recorded here with the reasoning and the conditions that would make them matter, so someone can re-examine them if the design changes.

### 1. Behaviour of an empty key in production

- **What is unknown.** Whether `limit({ key: "" })` is counted as one shared bucket or rejected. Locally (Miniflare) `""` is a valid, shared key; no production source says. The throwaway test's two empty-key calls both returned 200, which settles nothing because the second call on a normal key also passed.
- **Why it does not matter for the build.** The design keys on `auth.userId`, the token's `sub`. `claimsViolation` in `workers/scan-proxy/src/accountTokenContract.ts` (line 100) refuses a token whose `sub` is not a string or is blank, and the limiter runs only after `verifyAccountToken` succeeds, so `limit()` is never called with an empty key.
- **Re-examine if:** the key changes to something that can be empty (for example `CF-Connecting-IP` as a fallback, a header, or an optional body field), or the token check stops rejecting a blank `sub`. Then run the empty-key test: `limit = 1`, two calls with `?empty=1`, wait for the counters to settle (the first throwaway attempt shows two quick calls prove nothing), repeat several times, and see whether any call is refused.

### 2. Fixed or sliding window in production

- **What is unknown.** Whether production counts a fixed wall-clock window or a sliding one, and whether a rejected call still increments the counter. The only statement is in a workers-sdk PR description (**Indirect**, written by an AI agent): sliding, with no increment when over the limit. Local `wrangler dev` uses a fixed window.
- **Why it does not matter for the build.** It only changes the ceiling arithmetic: a fixed window can pass up to about 2N in a burst that straddles a boundary, a sliding window less. The observed looseness is larger than that. At `limit = 1`, 4 of 12 rapid requests got through, and the first three passed before the count caught up. The design already treats the limit as a deterrent on the sustained rate, not a precise count, and its numbers (10 per 60 s) come from the weekly suite's headroom (four sequential scans) and the cost ceiling in Q2, neither of which depends on the window type. Settling it would need a purpose-built measurement, and the answer would not change the code, the key, the placement or the value of N.
- **Re-examine if:** someone proposes relying on an exact count (for example a hard cap of N scans a minute per account, a quota, or billing-related enforcement), or a limit small enough that a 2N boundary burst matters (N of about 3 or less). Then measure it against the deployed limiter: call a fresh key at a steady rate for several windows and compare accepted counts across a window boundary; a count of N followed by an immediate burst of N after the boundary shows a fixed window. If an exact count is needed, use a Durable Object (Q8) instead of tuning the binding.

## Draft implementation ticket

**Title:** Scan service: per-account rate limit on `POST /v1/scan` (Workers Rate Limiting binding)

**Source.** Follow-up to #98 (findings in `docs/research/scan-proxy-rate-limit-binding.md`). Bounds how fast one funded account can repeat `POST /v1/scan`. Not a replacement for the #97 spend cap, and it does not close #96.

**Blocked by.** None. The throwaway `workers.dev` test (findings file, Q1) was run on 2026-10-15 and the binding limited requests on a `workers.dev`-only Worker.

**Acceptance criteria**

- [ ] `wrangler.toml` declares one `[[ratelimits]]` binding `SCAN_RATE_LIMITER` (`limit = 10`, `period = 60`, a `namespace_id` not used by any other Worker in the account); `Env` has `SCAN_RATE_LIMITER: RateLimit`; `package.json` asks for `wrangler ^4.36.0`
- [ ] After a successful `verifyAccountToken` and before the body is read, the Worker calls `limit({ key: auth.userId })`; a rejected call returns `429` with `{ ok: false, code: "rate_limited", message }`, a `Retry-After: 60` header and the CORS header
- [ ] A test shows a rejected request makes no RevenueCat call and no Claude call, so no credit is spent
- [ ] A test shows the key is the verified `sub`, not a body-supplied id, and that a `401` request never reaches the limiter
- [ ] If `limit()` throws, the request proceeds and the error is logged (or the ticket records the owner's choice of fail-closed, with a test)
- [ ] Web shows a dedicated message for `rate_limited` and treats it as not a lost response (test in `web/src/api.test.ts`)
- [ ] The `workers/scan-proxy/README.md` Errors list has a `429 rate_limited` entry and its "not a request rate limit" note no longer says so; `TESTING.md` lists the new cases
- [ ] `npm test` and `npm run typecheck` in `workers/scan-proxy` and the Web suite pass; the weekly suite's sequential scans are not rate limited after deploy (owner-approved run)
- [ ] The `worker-token-verification` External surface is re-run if the freshness script marks it stale (its pin `package.json` changed)

**Notes.** Android needs no code change (`ScanApiClient.kt` shows the server's `message` for any code); `web/TESTING.md` gets a line for the new `api.test.ts` case.

**Out of scope.** An IP-keyed limiter; WAF rules; any replay dedupe (#96); the Anthropic spend cap (#97).
