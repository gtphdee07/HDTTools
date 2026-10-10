# Handoff: #24 "Buy Pro on Web"

Branch: `worktree-ticket-24` (pushed, **not merged**; based on `MPSkills` at `bde1cae`).
Written 2026-10-10. Audience: whoever merges this branch and runs the remaining human steps.

## 1. What was implemented

A signed-in Web user can buy Pro (one-time lifetime unlock) in RevenueCat's modal checkout and see their plan and Scan Credit balance on the Account screen.

Commits on the branch, oldest first:

| Commit | What |
|---|---|
| `701e78f` | The feature: billing client, provider, paywall, Account wiring, tests, docs |
| `7e1cc7f` | Fixes from the code review (below) |
| `3c6cdd3` | Wizard for the `VITE_REVENUECAT_*` env values |
| `6bed331` | Wizard for the RevenueCat dashboard side |

### Behaviour
- Account screen (signed in) shows **Free plan / Pro plan** and **Scan credits: N**.
- Free users see a **paywall card**: price (read live from RevenueCat), "one time, no subscription", the line that results are *not certified DOT weights*, and a **Buy Pro** button. The existing Disclaimer gate is untouched.
- Checkout is the SDK's **modal placement** (no `htmlTarget`). The inline placement is deliberately not used (did not render in the #5 prototype; upstream purchases-js #1095).
- A visible **Close checkout** button sits above the SDK overlay (design-system `Button`, max z-index). It calls `history.back()`, the same path as the browser Back button, because the SDK pushes a history entry and treats `popstate` as cancel (upstream #973: the modal has no close control of its own).
- Close and Back both end as "Checkout closed. You were not charged." and allow a fresh retry. Other failures show an error and allow a retry.
- Signed-out visitors and builds without RevenueCat config see no plan or paywall (the free calculator is unaffected).

### Design
- `web/src/billing.tsx`: `BillingClient` seam (identify, getProOffer, getStatus, purchasePro) + `BillingProvider`/`useBilling`, mirroring `AuthClient`/`AuthProvider`. Per-account state resets on user change. A completed purchase sets Pro immediately and the follow-up balance refresh **cannot flip the user back to Free** if RevenueCat's entitlement lags (found in review, test added).
- `web/src/revenueCatBilling.ts`: the production client over `@revenuecat/purchases-js` (added, `^1.70.0`). The SDK is **lazy-loaded** on first sign-in (separate ~934 kB / 238 kB gzip chunk), so the free calculator never downloads it or contacts RevenueCat. Configures once with the Supabase account id as the RevenueCat app user id, then `changeUser`. Pro = active `pro` entitlement; balance = `SCAN` virtual currency, cache invalidated before every read. `UserCancelledError` maps to a "cancelled" outcome.
- `web/src/components/ProPaywall.tsx`, `web/src/screens/Account.tsx` (`PlanSection`), `web/src/main.tsx` (provider wiring).
- Config (all public): `VITE_REVENUECAT_WEB_PUBLIC_API_KEY` + `VITE_REVENUECAT_WEB_OFFERING_ID` (both required, else purchases are hidden); optional `VITE_REVENUECAT_PRO_ENTITLEMENT_ID` (default `pro`) and `VITE_REVENUECAT_PRO_PACKAGE_ID` (default: the offering's lifetime package).
- Docs touched: `docs/BUILD_AND_DEPLOY.md` (env table, RevenueCat setup notes, wizard pointers), `web/CONTEXT.md` (new term **Pro**).

### Tests and verification (as of the last commit)
- `web/`: `npm test` 189 passing; `tsc -b`, `knip`, `npm run build` clean. New: `App.billing.test.tsx` (interaction tests with a fake billing client that mimics the modal's push-state / Back-cancels behaviour), `revenueCatBilling.test.ts` (production client against a fake SDK).
- Root `uv run pytest`: 793 passed, 4 xfailed, no failures (after `npm install` in `workers/scan-proxy`; see #82/#83 for why it initially failed).
- Both wizards: `bash -n` clean and dry-run in a scratch folder with browser launchers stubbed. **Never run against the real dashboard.**

### Code review outcome
Two-axis review ran (Standards, Spec). Fixed: Pro flip-back, duplicated button styles, unused `ProOffer.title`, named `BillingStatus` type. Acknowledged, not changed (judgement calls): `PlanSection` could live in `components/`; `CloseCheckoutButton` lives in `billing.tsx`; the state-reset block in the provider's effect repeats initial values; `createRevenueCatClientFromEnv` has no test of its own (`readBillingConfig` does); the optional entitlement/package env overrides and the `offerings.all[id] ?? offerings.current` fallback go slightly beyond the ticket; `web/TESTING.md` was not updated (its table and suite count were already stale; refresh is #64).

## 2. Outstanding: not done in this branch

1. **Nothing was run against real RevenueCat.** No sandbox purchase, no real cancel test. Everything above is verified only against fakes.
2. **RevenueCat dashboard is not configured for Pro.** Needed: a non-consumable Pro product on the Web Billing config, a `pro` entitlement with it attached, the product associated with `SCAN` for the starter bundle, and it attached to the `default` offering's Lifetime package. `scripts/wizard_web_revenuecat_dashboard.sh` walks it; unrun.
3. **Env vars are not set anywhere.** `web/.env.local` and `web/.env.production` have no `VITE_REVENUECAT_*` yet, so the paywall is hidden everywhere, including the live site. `scripts/wizard_web_revenuecat.sh` sets them; unrun.
4. **Web External suite is stale.** `pages-site` and `supabase-auth` show stale (and the README dashboard row is red) because this branch changed `web/package.json`, the lockfile and `web/src/main.tsx`. This is correct behaviour, not a false failure. Run the free suite from the main checkout (`web/test-external.ps1`, needs `web/.env.local` credentials, not present in the worktree) after merging.
5. **Branch not merged**, per instruction.

## 3. Tickets created from this work

| # | Title | Covers |
|---|---|---|
| #80 | Retry when the Web plan fails to load | Initial plan/offer load failure shows an error but no way to retry (paywall hidden until plan known) |
| #81 | Starter scans appear after a Web Pro purchase without a reload | Starter bundle is granted server-side; balance is read once after purchase, so it can lag until reload. Bounded recheck + "updating your scans" state |
| #82 | Missing scan-proxy install fails with a clear message, not a 502 | Without `workers/scan-proxy/node_modules`, valid-token tests return a misleading 502 (lazy Claude SDK import fails, treated as extraction failure) |
| #83 | A fresh git worktree can be set up for testing in one documented step | New worktrees lack gitignored deps/config (`node_modules`, `.env.local`) |

(#82's body originally blamed the dashboard for a scan-proxy failure; that was wrong and is corrected by a comment and an edit.)

## 4. Left undone or uncovered, and NOT resolved by closing #80-#83

- **#11 (human checklist) still stands and is now unblocked.** It needs the real sandbox cancel test: close control, Back button, fresh retry, against the real SDK. Specific unverified assumptions in the code that test must confirm:
  - The modal pushes exactly one history entry, so `history.back()` cancels it rather than navigating away or doing nothing.
  - After a *successful* purchase, no stale `{checkoutOpen}` history entry is left that a later Back could trip over (spec review flagged this as unverified).
  - The Close button's z-index actually sits above the SDK's overlay and is not obscured or clipped.
  - Upstream #973 and #1095 were both still open on 2026-10-10; SDK is now 1.70.0 (prototype used 1.63.1).
- **Starter-scan timing is unmeasured.** #81 picks a window, but the real grant latency can only be observed on the real sandbox purchase.
- **`revenuecat-web-billing` External surface is still `planned` with empty `boundary_files`.** `web/src/revenueCatBilling.ts` now exists and should probably be its boundary file, promoting it to a real surface. **No ticket was filed** (offered, the owner chose to leave it).
- **Android has no Pro entitlement.** Whether to attach Android's Test Store Lifetime product to `pro` is an owner decision (the dashboard wizard flags it). Without it, a Pro bought on Android does not show as Pro on Web, which the parent spec (#15) intends. Android also has no Pro UI.
- **Going live is untouched:** a real Stripe account linked to the Web Billing config, the production `rcb_` key, real prices and pack sizes (placeholders only; ADR-0006 pricing rule), and committing `web/.env.production`. The wizard refuses a sandbox `rcb_sb_` key for that file.
- **Scan packs on Web** (parent spec story 31, "buy additional scans in packs") are not part of #24. Check the remaining child tickets of #15; none was created here.
- **Wizard URLs and menu names are unverified.** They come from RevenueCat docs and the #5 notes; the wizards open the project root and give menu paths in words because deep links could not be confirmed. How to mark an offering as default was not in the docs fetched.
- **Process notes for whoever merges:**
  - `EnterWorktree` created the worktree from stale `main`; its branch was reset to `MPSkills` HEAD. The four uncommitted Android test edits in the main checkout (`RigCheckNavHostTest`, `ScaleTicketEntryScreenTest`, `TrailerTagEntryScreenTest`, `TruckTagEntryScreenTest`) are **not** in this branch.
  - The pre-commit hook adds the regenerated `dashboard.svg` to commits; this branch's copy shows the stale Web External row as red.
  - The worktree at `.claude/worktrees/ticket-24` is registered as locked and will need unlocking before `git worktree remove`.
  - Lint shows two `react(only-export-components)` oxlint warnings in `billing.tsx`, the same pattern `auth.tsx` already has.
