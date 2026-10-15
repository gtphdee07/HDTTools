# Cloudflare Workers Rate Limiting binding: facts for ticket #98

Research only. No recommendation. No endpoint was called, nothing was deployed or spent.

All pages below were read on **2026-10-14** (docs pages fetched as raw Markdown from `developers.cloudflare.com/.../index.md`; GitHub material via the GitHub API). "Page updated" is the "Last updated" stamp on the page when read.

Marker legend: **Confirmed** = stated in a primary source cited beside it. **Indirect** = stated only in a primary-source code comment or PR description by Cloudflare/workers-sdk contributors, not in public docs. **UNCONFIRMED** = no primary source found; a settling test is given.

Primary source URLs used (short names used below):

- [RL-DOC] https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/ (page updated Oct 12, 2026)
- [RL-GA] https://developers.cloudflare.com/changelog/post/2025-09-19-ratelimit-workers-ga/ (dated Sep 19, 2025)
- [DEV-MATRIX] https://developers.cloudflare.com/workers/development-testing/bindings-per-env/
- [WAF-RL] https://developers.cloudflare.com/waf/rate-limiting-rules/ (page updated Aug 25, 2026)
- [WAF-RATE] https://developers.cloudflare.com/waf/rate-limiting-rules/request-rate/ (page updated Apr 16, 2026)
- [WDEV] https://developers.cloudflare.com/workers/configuration/routing/workers-dev/ (page updated Sep 22, 2026)
- [KV-LIM] https://developers.cloudflare.com/kv/platform/limits/ (updated Oct 8, 2026); [KV-PRICE] https://developers.cloudflare.com/kv/platform/pricing/ (Apr 21, 2026); [KV-HOW] https://developers.cloudflare.com/kv/concepts/how-kv-works/
- [DO-PRICE] https://developers.cloudflare.com/durable-objects/platform/pricing/ (Sep 30, 2026); [DO-LIM] https://developers.cloudflare.com/durable-objects/platform/limits/; [DO-CTR] https://developers.cloudflare.com/durable-objects/examples/build-a-counter/ (Oct 12, 2026)
- [WK-PRICE] https://developers.cloudflare.com/workers/platform/pricing/ (Oct 2, 2026); [WK-LIM] https://developers.cloudflare.com/workers/platform/limits/ (Oct 12, 2026)
- [SDK-*] cloudflare/workers-sdk on GitHub (source and PRs), cited by path or PR number.

---

## 1. Availability and cost

| Claim | Status | Source |
| --- | --- | --- |
| The binding is **GA** (stable) since 2025-09-19. The changelog says the `ratelimit` binding "is now stable and recommended for all production workloads"; the older `unsafe` binding keeps working. | **Confirmed** | [RL-GA] |
| It was beta before that (docs carried a "Beta" badge and an "open beta" caution until the GA docs commit). | **Confirmed** | https://github.com/cloudflare/cloudflare-docs/commit/f7b05774 (docs commit "[Workers] Rate Limiting GA", 2025-08-12) |
| The current docs page carries no beta/preview marker. | **Confirmed** | [RL-DOC] |
| The API is "backed by the same infrastructure that serves rate limiting rules" (the WAF product). | **Confirmed** | [RL-DOC] |
| Works for a Worker served only from `workers.dev` (no zone, no route, no custom domain). | **UNCONFIRMED** | No Cloudflare page says either way. The docs describe the binding as a Worker-runtime API invoked from code ("applied after your Worker starts"), with no zone or hostname prerequisite, and `wrangler.toml` carries no zone field. That is an inference, not a statement. |
| Which plans include it (Free / Paid). | **UNCONFIRMED** | [RL-DOC], [WK-PRICE], [WK-LIM] and the GA changelog are all silent on plans. I searched the Workers pricing and limits pages for "rate limit" and found no mention. |
| Usage charge for `limit()` calls or for namespaces. | **UNCONFIRMED** | Same pages: no price listed. The only indirect fact is that the Worker invocation itself is billed as a normal Workers request regardless of the 429 ([WK-PRICE]: Free 100,000 requests/day, Paid 10M/month included then $0.30 per extra million). |
| Account-level limit on namespaces, or on bindings per Worker. | **UNCONFIRMED** | [WK-LIM] has no row for rate limit bindings; [RL-DOC] states none. The docs only say you "can define and configure multiple rate limiting configurations per Worker". |
| Not visible in the dashboard. | **Confirmed** | [RL-DOC] "Monitoring": "Rate limiting bindings are not currently visible in the Cloudflare dashboard." Suggests Workers Logs/Traces for 429s and Workers Analytics Engine for custom `rate_limited` events. |

Settling tests for the unconfirmed items (owner, no spend beyond a throwaway Worker):

- workers.dev + plan + charge: deploy a throwaway Worker (any name, `workers_dev` left on, no routes) containing the binding from section 3 with `limit = 1`, `period = 60`, a unique `namespace_id`, returning 200/429 from `limit({key:"t"})`. Call its `https://<name>.<subdomain>.workers.dev/` twice within a few seconds. A 200 then a 429 settles "works on workers.dev" on the account's current plan. The account's plan is whatever the dashboard shows (Workers & Pages overview); the deploy succeeding on a Free account settles "Free can use it". Check the dashboard Billing > Billable usage after a day for any rate-limit line item (none is expected, none is documented).
- Namespace count limit: not testable cheaply; ask Cloudflare support or watch for a deploy error if ever many bindings are added.

---

## 2. Semantics

| Claim | Status | Source |
| --- | --- | --- |
| Limits are **local to the Cloudflare location** the Worker runs in. "For each unique key you pass ... there is a unique limit per Cloudflare location." Example given: Sydney only counts Sydney requests. | **Confirmed** | [RL-DOC] "Locality" |
| **Permissive, eventually consistent**, "intentionally designed to not be used as an accurate accounting system". Isolates check a locally cached value; requests count towards the limit "Very quickly, but not immediately". | **Confirmed** | [RL-DOC] "Accuracy" |
| Counters are cached on the same machine and updated **asynchronously** against a backing store in the same location; `await limit()` does not wait on a network request. | **Confirmed** | [RL-DOC] "Performance" |
| Config shape: `simple.limit` (number, allowed requests or `limit()` calls per period) and `simple.period` (seconds, **must be 10 or 60**). `simple` is the only supported type. | **Confirmed** | [RL-DOC] "Configuration" table |
| **Calls to `limit()` increment the counter** ("1500 requests - calls to limit() increment this"). | **Confirmed** | [RL-DOC] config example comment and table |
| `limit()` takes one argument, an object with `key`; "The key you provide can be any `string` value." Returns a promise of an object with `success` (boolean). Docs show `success === false` leading to a 429 response. | **Confirmed** | [RL-DOC]; type in https://github.com/cloudflare/workerd/blob/main/types/defines/ratelimit.d.ts (`RateLimitOutcome { success: boolean }`) |
| Key restrictions: maximum length, allowed characters, hashing. | **UNCONFIRMED** | Not in [RL-DOC]. Only indirect: production counter identity is `hash(key)` (see below), so length is likely not material, but no limit is published. Test: call `limit({key: "x".repeat(10000)})` locally in `wrangler dev` and on a throwaway deploy, and see whether it throws. |
| Behavior with an **empty key**. | **UNCONFIRMED** for production. Locally (Miniflare) `key` defaults to `""` when omitted and `""` is a valid key shared by every caller. The docs' own example uses `url.searchParams.get("userId") \|\| ""` and `cf-connecting-ip \|\| ""` fallbacks. | Local: [SDK-miniflare] `packages/miniflare/src/workers/ratelimit/ratelimit.worker.ts` (`key = ""`). Production: no source. Test: throwaway deploy with `limit=1`; call `limit({key:""})` twice and see whether the second is `success:false`. |
| Docs recommend stable identifiers (API keys, routes, user/tenant IDs) and advise **against IP addresses or locations** as keys, because they can be shared by many users. | **Confirmed** | [RL-DOC] "Best practices" |
| Production counter is **sliding-window**: `prev * (1 - elapsed/period) + cur`, and the increment is **skipped when already over the threshold**. Counter identity in production is `(account_id, namespace, hash(key), bucket, bucket_start_ts)`; the limit is not part of the identity (so differing `limit` on a shared namespace stays coherent). | **Indirect** | Stated in the description of workers-sdk PR #14968 (https://github.com/cloudflare/workers-sdk/pull/14968), which quotes internal Cloudflare source it read. Not in any public doc. The PR is marked as written by an AI agent. Treat as unverified for ceiling math. |
| Local emulation (`wrangler dev`/Miniflare) uses a **fixed window aligned to wall clock** (`epoch = floor(now / (period*1000))`), increments only when `count < limit`, and resets on window rollover. | **Confirmed (source)** | [SDK-miniflare] `packages/miniflare/src/workers/ratelimit/ratelimit-object.worker.ts` |
| Worker-supplied per-call overrides of `limit`/`period` exist in the local client (`options` keys `key`, `limit`, `period`). | **Confirmed in source, not in docs/types** | Same file `ratelimit.worker.ts`; the published TS type only has `key`. Not a documented production feature. |

What this means in practice (derived from the above; marked as inference, not quoted from a source):

- One caller served from one Cloudflare location: roughly **N successes per period per key** in that location, with some slack because the counter is eventually consistent and permissive (concurrent requests at the same instant can all pass before counts propagate). With a fixed window, a burst straddling a window boundary could pass up to about 2N; with the sliding window described in PR #14968 the boundary effect is smaller. Which one production uses is Indirect only.
- One caller reaching **several locations** (anycast routing can change, VPNs, mobile networks, a traveling client): each location keeps its own counter for the same key, so the worst case is **N x (number of locations hit) per period**.
- A global attacker or botnet spread over many locations is therefore bounded only per location, not globally. A limit of N per 10 s is a stricter rate than N per 60 s only in per-second terms (N/10 vs N/60 per second per location); the period choice is limited to 10 or 60.
- Cloudflare's own WAF rate limiting is also per data center (see 5a), so this is a property of the product family, not just the binding.

Whether a given caller stays in one location: [RL-DOC] only says "the Cloudflare location that your Worker runs in". The Workers overview says a request "received by any of Cloudflare's data centers" invokes the Worker (https://developers.cloudflare.com/workers/reference/how-workers-works/ , updated Sep 18, 2026). No page guarantees that a client always lands in the same location (**UNCONFIRMED**; test: log `request.cf.colo` over several calls from the same client over a day).

---

## 3. Wrangler version, syntax, namespace_id, TypeScript type

| Claim | Status | Source |
| --- | --- | --- |
| Minimum Wrangler for the stable `ratelimits` stanza: **4.36.0** ("You must use version 4.36.0 or later"). | **Confirmed** | [RL-DOC]. Wrangler 4.36.0 was published 2025-09-12 (https://github.com/cloudflare/workers-sdk/releases/tag/wrangler@4.36.0) and its release notes include PR #10541 "stable `ratelimit` binding" (https://github.com/cloudflare/workers-sdk/pull/10541 , https://github.com/cloudflare/workers-sdk/pull/10590). Before that the binding lived under `[[unsafe.bindings]]` with `type = "ratelimit"` (beta, wrangler 3.45.0+ per the pre-GA docs diff at the cloudflare-docs commit above). |
| Exact `wrangler.toml` syntax (copied from the docs). | **Confirmed** | [RL-DOC] |
| `namespace_id` rule: a **string containing a positive integer**, "unique within your Cloudflare account"; "Although the value must be a valid integer, it is specified as a string. This is intentional." | **Confirmed** | [RL-DOC] "Configuration" table; maintainer confirmation in https://github.com/cloudflare/cloudflare-docs/issues/25590 |
| Two bindings with the **same `namespace_id`**, even in different Workers on the same account, **share counters per key**. Use a unique id per binding to avoid sharing. | **Confirmed** | [RL-DOC] "Note" under Configuration |
| The namespace is **not pre-created in the dashboard**; it is just an integer you pick. | **Indirect** | Docs describe it only as "An identifier you define". Wrangler uploads the binding inline in the Worker's metadata as `{ name, type: "ratelimit", namespace_id, simple }` with no resource-creation call: [SDK-deploy] `packages/deploy-helpers/src/deploy/helpers/create-worker-upload-form.ts` (the `ratelimits.forEach(...)` block). Wrangler validates only that `namespace_id` is a string and `simple.period` is 10 or 60: `packages/workers-utils/src/config/validation.ts` (`validateRateLimitBinding`); it does not check that the string is numeric. Server-side acceptance of a non-numeric string is **UNCONFIRMED**. |
| `ratelimits` is **not inherited** by `[env.*]` sections; each environment must declare its own. | **Confirmed (source)** | `validation.ts`: `ratelimits: notInheritable(...)`. Not mentioned on the Wrangler configuration docs page (https://developers.cloudflare.com/workers/wrangler/configuration/ has no "ratelimits" section as of 2026-10-14). |
| TypeScript: global interface `RateLimit { limit(options: RateLimitOptions): Promise<RateLimitOutcome> }`, `RateLimitOptions { key: string }`, `RateLimitOutcome { success: boolean }`. | **Confirmed** | https://github.com/cloudflare/workerd/blob/main/types/defines/ratelimit.d.ts ; also present in `@cloudflare/workers-types` (checked in this worktree: `workers/scan-proxy/node_modules/@cloudflare/workers-types/index.d.ts`, version 5.20260817.1, around line 14875). The docs example types the binding as `MY_RATE_LIMITER: RateLimit;` in `Env`. |
| `wrangler types` emits `RateLimit` for `ratelimits` bindings. | **Confirmed (source)** | `packages/wrangler/src/type-generation/index.ts` maps `ratelimit` to `"RateLimit"` (added by PR #6550 for the unsafe form, https://github.com/cloudflare/workers-sdk/pull/6550 ; stable form covered by #10541's type-generation test). |
| Repo note (not Cloudflare): `workers/scan-proxy/package-lock.json` pins wrangler 4.123.0 and miniflare 5.20260811.1-alpha, both newer than 4.36.0. | **Observed locally** | `workers/scan-proxy/package-lock.json` |

Exact TOML (from [RL-DOC]):

```toml
[[ratelimits]]
name = "MY_RATE_LIMITER"
namespace_id = "1001"

  [ratelimits.simple]
  limit = 100
  period = 60
```

Call shape (from [RL-DOC]): `const { success } = await env.MY_RATE_LIMITER.limit({ key })`.

---

## 4. Local dev and tests

| Claim | Status | Source |
| --- | --- | --- |
| `wrangler dev` (local mode) **simulates** the binding; Rate Limiting is listed as "Local simulations: yes", "Remote binding connections: **no**", "Remote development (`wrangler dev --remote`): yes". | **Confirmed** | [DEV-MATRIX] (three tables; "Rate Limiting" row in each) |
| Miniflare has a first-party `ratelimit` plugin. Introduced by PR #5083 on 2024-03-01 ("Add Miniflare support/tests for Ratelimits emulation"), wired into `wrangler dev --local` by PR #5403 on 2024-04-03 (changeset "fix: wrangler dev --local support for ratelimits", released in the Version Packages PR #5485 with miniflare 3.20240329.1). | **Confirmed (source)** | https://github.com/cloudflare/workers-sdk/pull/5083 , https://github.com/cloudflare/workers-sdk/pull/5403 , https://github.com/cloudflare/workers-sdk/pull/5485 ; plugin at `packages/miniflare/src/plugins/ratelimit/index.ts` |
| Local emulation is **in-process, no network, counters persisted to disk** so they survive Durable Object eviction and `wrangler dev` restarts within the same window (fix landed in Miniflare 5.20260731.0-alpha, PR #14968, 2026-08-03). Before that fix, local counters silently reset after about 10 s of inactivity. | **Confirmed (source)** | https://github.com/cloudflare/workers-sdk/pull/14968 ; release notes in https://github.com/cloudflare/workers-sdk/pull/15021 |
| Local counters are keyed by `namespace_id` (not binding name), so two local bindings with one `namespace_id` share a counter (PR #14572, miniflare 4.20260702.0). Counters are scoped to `(key, period)`. | **Confirmed (source)** | https://github.com/cloudflare/workers-sdk/pull/14572 ; `ratelimit-object.worker.ts` |
| `@cloudflare/vitest-pool-workers` runs Miniflare, so the binding is available in Workers-runtime tests; `reset()` from `cloudflare:test` clears ratelimit state since `@cloudflare/vitest-pool-workers@0.18.1` (PR #14409, 2026-07-06). Earlier versions kept bucket counts across tests. | **Confirmed (source)** | https://github.com/cloudflare/workers-sdk/pull/14409 ; release notes in https://github.com/cloudflare/workers-sdk/pull/14536 ; docs say the Vitest integration "Runs tests fully-locally using Miniflare" (https://developers.cloudflare.com/workers/testing/vitest-integration/ , updated Aug 20, 2026). The package is now documented with a migration guide to a "Vitest plugin" (the source tree renamed it, PR #15074) so the package name/version may differ. |
| A documented, official way to unit-test rate limit behavior. | **UNCONFIRMED** | No Cloudflare docs page ([RL-DOC], the Vitest integration pages, the local-development pages) mentions testing the binding. The only first-party examples are workers-sdk fixtures: `fixtures/ratelimit-app/` (wrangler.jsonc with `limit 3, period 60`, test calls the Worker 4 times and expects the 4th to be rejected, and sleeps to avoid a window boundary) and `fixtures/vitest-plugin-examples/reset/`. Those fixtures also note that Miniflare's fixed window can reset mid-burst at a boundary, hence their `waitForFreshRateLimitWindow()` helper. |
| Plain `node --test` unit tests (as scan-proxy uses) can pass a stub with `limit()` returning `{ success }`. | **Inference** | Follows from the `RateLimit` type being a one-method interface; no source documents a stub. |

Test the owner can run to settle local behavior: `npx wrangler dev` in `workers/scan-proxy` with the stanza added; `curl` the route 3-4 times quickly (with the config at a tiny `limit`) and watch for the first rejection. Counters now persist across dev restarts within the window, so wait out the period or change `namespace_id` to reset.

---

## 5. Alternatives (what each stops / cannot stop / owner effort / code effort / running cost)

### 5a. WAF rate limiting rules (zone-level)

Source: [WAF-RL], [WAF-RATE], https://developers.cloudflare.com/waf/rate-limiting-rules/parameters/

- **Applies to workers.dev hostnames?** **UNCONFIRMED.** Rules are created per zone ("Create a rate limiting rule ... for your zone", https://developers.cloudflare.com/waf/rate-limiting-rules/create-zone-dashboard/). [WDEV] says the workers.dev subdomain "is treated as a Free website" but nothing documents that an account can attach WAF rules to its own `*.workers.dev` hostname; the account does not own a zone for it. A sibling Cloudflare docs page for R2 states WAF custom rules are unavailable on the `r2.dev` development URL and need a custom domain (https://developers.cloudflare.com/r2/buckets/public-buckets/), which is analogous but not Workers-specific. Settling test: in the dashboard, check whether any zone exists for `workers.dev` under the account's Websites list (it will not), and whether the Security rules page can be reached for the Worker; or attach a custom domain/route and compare.
- **Free plan limits (zone plan)** [WAF-RL] Availability table: **1 rule**, counting period **10 s only**, counting characteristic **IP only**, rule expression fields **Path and Verified Bot only**, mitigation timeout **10 s only**, counting model number of requests. Pro: 2 rules, periods up to 1 min, IP characteristic. Business: 5 rules. Enterprise: 100 rules.
- **Counting scope:** per data center. "Cloudflare does not support global rate limiting counters across the entire network. Each data center maintains its own counters" except data centers sharing a geographical location ([WAF-RATE]). Excess requests may reach the origin because counters update with a delay of up to a few seconds ([WAF-RL] "Important remarks").
- **Stops:** per-IP bursts on matching paths before the Worker runs (so no Worker invocation or Claude call for blocked requests), if a zone applies. **Cannot stop:** distributed multi-IP abuse (Free counts IP only), global ceilings, per-account/per-token limits (no header characteristic below Enterprise Advanced Rate Limiting). Requires owning a zone and routing the Worker through a route/custom domain.
- **Owner effort:** needs a domain on Cloudflare plus Worker route/custom domain; dashboard rule creation. **Code effort:** none. **Running cost:** none documented for Free-plan rule; the zone/domain cost is outside Cloudflare docs.

### 5b. Workers KV as a counter

Sources: [KV-HOW], [KV-LIM], [KV-PRICE]

- **Consistency:** "eventually-consistent"; changes are "usually immediately visible" at the writing location but "may take up to 60 seconds or more to be visible in other global network locations" ([KV-HOW]). KV "is not ideal for applications where you need support for atomic operations or where values must be read and written in a single transaction" (no atomic increment, so read-modify-write races lose counts). The docs point to Durable Objects for stronger consistency.
- **Write limits:** writes to the **same key: 1 per second** on both plans ([KV-LIM]); Free plan **1,000 writes/day** to different keys and 100,000 reads/day; Paid unlimited. Free-plan overruns fail with an error ([KV-PRICE]).
- **Cost (Paid):** 1 million writes/month included then $5.00 per million; reads 10 million/month then $0.50 per million ([KV-PRICE]).
- **Why poor as a counter (from the above):** the 1-write-per-second same-key cap means a counter cannot be bumped on every request; lost updates under concurrency; up to 60 s stale reads elsewhere; Free plan exhausts 1,000 writes/day quickly.
- **Stops:** slow, coarse limits (e.g. a daily cap with approximate counting). **Cannot stop:** bursts, since the counter lags. **Owner effort:** create a KV namespace. **Code effort:** moderate. **Cost:** as above.

### 5c. Durable Objects (per-key counter)

Sources: [DO-PRICE], [DO-LIM], [DO-CTR], https://developers.cloudflare.com/workers/platform/pricing/ (Durable Objects section)

- **Free plan availability:** yes, but **only SQLite-backed** Durable Objects ([DO-PRICE]). Free daily limits reset at 00:00 UTC and overruns fail with an error.
- **Pricing:** Free: 100,000 requests/day, 13,000 GB-s/day, SQLite rows read 5 million/day, rows written 100,000/day, 5 GB storage. Paid: 1 million requests/month included then $0.15 per million; 400,000 GB-s/month then $12.50 per million GB-s; rows written 50 million/month then $1.00 per million ([DO-PRICE]). Paid plan minimum $5/month (per its pricing examples).
- **Pattern:** one Durable Object per key (e.g. `env.COUNTERS.getByName(name)`), RPC methods that read-then-write storage; "You do not have to worry about a concurrent request having modified the value in storage" ([DO-CTR]). A DO is a single global instance per name, so the count is **global per key** (unlike the binding), at the cost of one extra hop and a location-affinity latency. An individual DO has a soft limit of 1,000 requests per second ([DO-LIM]). Cloudflare does not publish a "rate limiter" Durable Object example at the path I tried (`/durable-objects/examples/build-a-rate-limiter/` returned 404 on 2026-10-14); the counter example above is the closest first-party pattern.
- **Stops:** exact, global per-key limits (including expiry via window-key design or alarms). **Cannot stop:** traffic before it reaches the Worker (each check costs a DO request); unauthenticated floods still bill Workers + DO requests. **Owner effort:** none beyond adding a binding and a migration for the new class. **Code effort:** highest of the in-Worker options (class, migration, window logic, cleanup). **Cost:** per above; negligible at low volume.

### 5d. Other Cloudflare-documented options

- The Rate Limiting binding page's own "alternatives" mention: only the Hono middleware packages (`@elithrar/workers-hono-rate-limit`, `@hono-rate-limiter/cloudflare`, `hono-cf-rate-limit`) which wrap the binding or other stores ([RL-DOC] "Examples"). It does not point to WAF/KV/DO alternatives.
- WAF rate limiting is cited by [RL-DOC] only as the infrastructure the binding is built on.
- **Cloudflare Access in front of workers.dev** can require authentication before reaching a Worker's workers.dev URL, preview URLs, or version URLs ([WDEV] "Manage access to workers.dev"). It stops unauthenticated callers entirely; it is an authentication control, not a rate limit, and would affect legitimate callers that cannot present Access credentials (**not evaluated here; a mobile app calling the Worker directly would need service-token style auth, UNCONFIRMED for this app**).
- **Disabling `workers.dev`** (`workers_dev = false`) removes the hostname but also removes access unless a route or custom domain exists ([WDEV]).
- **Workers Analytics Engine / Workers Logs** for observing 429s ([RL-DOC] "Monitoring"): observation only.

---

## 6. Deploy implications

| Claim | Status | Source |
| --- | --- | --- |
| No dashboard step is documented for the binding. | **Confirmed (absence) / Indirect** | [RL-DOC] describes only the Wrangler config; the binding is sent in the Worker upload metadata with `wrangler deploy` ([SDK-deploy] `create-worker-upload-form.ts`). Binding not shown in dashboard ([RL-DOC] "Monitoring"). |
| Extra API-token permission for the binding. | **UNCONFIRMED** | No page lists a rate-limit-specific permission. The documented CI token template is **Edit Cloudflare Workers** (https://developers.cloudflare.com/workers/ci-cd/external-cicd/github-actions/ , read 2026-10-14). The binding rides on the same script-upload call as KV/R2 bindings, so no separate permission is implied, but that is inference. Settling test: run `wrangler deploy` once with the existing token and the new stanza; an authorization error would name the missing permission. |
| Binding preserved or overridden across deploys. | **Confirmed (principle) / Indirect (this binding)** | Wrangler's config file is the source of truth; dashboard-side changes to routes and variables are overridden on the next deploy (https://developers.cloudflare.com/workers/wrangler/configuration/#source-of-truth). Bindings are re-sent from config on every deploy, so removing the stanza removes the binding. The docs do not state this specifically for ratelimits because the binding cannot be edited in the dashboard. `ratelimits` is also not inherited into `[env.*]` blocks (`notInheritable`, see section 3), so each environment needs its own stanza and its own `namespace_id` unless sharing is intended. |
| Shared `namespace_id` across Workers shares counters (including any other Worker on the account that picks the same integer). | **Confirmed** | [RL-DOC] |
| Existing deployments on the old `unsafe` binding keep working. | **Confirmed** | [RL-GA] |

---

## Unconfirmed list (for quick scanning)

1. Binding works on a workers.dev-only Worker (inference: yes). Test in section 1.
2. Which plans include it; any usage charge; any namespace/binding count cap. Test in section 1.
3. Maximum key length and empty-key behavior in production. Test in section 2.
4. Production window algorithm (fixed vs sliding) and whether blocked calls increment. Only Indirect (PR #14968 text).
5. Whether a client stays in one Cloudflare location. Test: log `request.cf.colo`.
6. Server-side validation of a non-numeric `namespace_id`.
7. WAF rate limiting rules applying to a `*.workers.dev` hostname (inference: no zone available).
8. Official unit-testing guidance for the binding (none found; fixtures only).
9. Extra API-token permission needed (inference: none beyond Edit Cloudflare Workers).
