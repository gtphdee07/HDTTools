# RevenueCat Web Billing product maturity — research (GitHub issue #4)

Resolves [issue #4](https://github.com/gtphdee07/HDTTools/issues/4), a child
of the wayfinder map issue #3 ("Shared Android+Web accounts/paywall
architecture (item #20)"). Feeds the "Lock entitlement source-of-truth +
scan-gating unification" decision, specifically whether Option 1A
(RevenueCat as single source of truth for both Android and Web, with Web
adopting RevenueCat's own Web Billing product instead of Stripe — see
`ClaudePlans/2026-09-21-entitlement-and-scan-gating-unification-impacts.md`,
"Option 1A") is safe to lock, or whether the "newer and less proven than
Stripe" risk note there is a real blocker.

All findings below are sourced from RevenueCat's own primary sources:
official docs (revenuecat.com/docs), their status page, and their public
`purchases-js` GitHub repo (issues, releases, commit history) — not
secondary blog posts or tutorials. Research performed 2026-09-23.

## 1. Consumable / credit-pack purchases

RevenueCat Billing's Product Catalog explicitly supports three product
types, not just subscriptions:

- **Consumable**: "A non-recurring purchase that can be purchased one or
  more times (repeated)" — this is the credit-pack shape.
- **Non-consumable**: "A non-recurring purchase that can only be purchased
  once."
- **Subscription** (auto-renewing).

Source: [Configure RevenueCat Billing products & prices](https://www.revenuecat.com/docs/web/web-billing/product-setup)

More importantly, RigCheck's Android implementation doesn't actually use
the generic "consumable product" type for scan credits — it uses
RevenueCat's **Virtual Currencies** feature (see
`android/app/src/main/java/com/rigcheck/app/data/RevenueCatManager.kt`,
which calls `awaitGetVirtualCurrencies()` and reads a balance keyed by a
`SCAN` currency code, with credit deduction/refund happening server-side
via a direct RevenueCat REST call from `workers/scan-proxy`). The question
that actually matters for parity is whether Virtual Currencies work on
Web, and they do:

- Web (JS/TS) SDK support for reading virtual currency balances
  (`getVirtualCurrencies()`) since SDK **v1.13.0**, alongside iOS (5.32.0+),
  Android (9.1.0+), React Native, and Unity.
- Currency is auto-granted when a customer purchases an associated
  product (works identically for a Web Billing consumable purchase as for
  an Android IAP).
- Deposits/spends still go through the same server-side Developer API
  call (secret-key REST call) regardless of platform — this is already
  RigCheck's existing pattern, not new work Web Billing would introduce.
- Note: client-side *spending* of virtual currency isn't yet supported by
  the SDK (server-side spend, which RigCheck already does, is what's
  required either way).

Source: [Virtual Currency](https://www.revenuecat.com/docs/offerings/virtual-currency)

**Verdict on Q1**: Supported, and specifically the mechanism (Virtual
Currencies) RigCheck's Android side already relies on has explicit,
version-pinned Web SDK support. No gap here.

## 2. Identity: keying a Web Billing customer to a shared-account user ID

RevenueCat's identity model is platform-agnostic and is the same on Web as
on Android: a developer-supplied **App User ID**, set via
`Purchases.configure()`/`logIn({ appUserID })` on Web (functionally
identical to the Android SDK's `logIn()`). RevenueCat does not care how
that ID was derived — it doesn't need to be a Google/Apple/Firebase
identity, it's explicitly meant to be "an identifier you already have,
such as a database identifier or a user ID from your own backend." Because
"customers may be referenced by multiple App User IDs, also known as
aliases[, and] each grouping of App User IDs is considered a single
customer," passing the same backend-issued user ID (produced after
email+password or Google/Apple sign-in resolves to RigCheck's own account
system) from both the Android app and the Web app lands both platforms on
the same RevenueCat customer record and entitlement/virtual-currency
balance.

Sources:
[Customers in RevenueCat / App User IDs](https://www.revenuecat.com/docs/customers/user-ids),
[Identifying Customers](https://www.revenuecat.com/docs/customers/identifying-customers)

For context: `RevenueCatManager.kt` today does **not** yet set a custom
`appUserID` (it relies on the SDK's anonymous ID, since shared accounts
don't exist yet) — so this isn't a Web-specific gap Android has already
solved and Web hasn't; it's greenfield work on *both* platforms once
accounts land, and the mechanism is identical on both.

**Verdict on Q2**: No platform asymmetry. The identity model that a shared
accounts system would need is the same `logIn(appUserID)` call on Android
and Web.

## 3. Checkout UX: presentation and customization

Web Billing checkout is **embedded, not redirect-based**, via the Web SDK:

- `Purchases.purchase()` takes an optional `htmlTarget` (an `HTMLElement`)
  — if provided, the checkout form mounts **inline** inside that element
  on the host page; if omitted, the SDK creates its own modal overlay
  appended to `document.body`.
- A separate product, **Web Purchase Links**, is a RevenueCat-hosted
  (i.e., off-site/redirect-style) checkout page for links distributed via
  campaigns/email — RigCheck would use the embedded Web SDK path, not
  this, to stay in-app.
- Customization is done via the dashboard **Appearance Editor**: page
  background, form background, primary/accent/error colors, button and
  form-element shapes, and an app icon shown during checkout — applied
  consistently across the Web SDK checkout, Web Purchase Links pages, and
  lifecycle emails.

Sources:
[Getting Started With RevenueCat Web](https://www.revenuecat.com/docs/web/overview),
[Web SDK](https://www.revenuecat.com/docs/web/web-billing/web-sdk),
customization behavior per the Appearance Editor docs at
`revenuecat.com/docs/web/web-billing/customization` (page contents
confirmed via RevenueCat's own search index; direct fetch of that URL
404'd during this research — treat the customization claims above as
corroborated but not directly re-fetched),
[`purchases-js` API reference — `purchase()`](https://revenuecat.github.io/purchases-js-docs/)

**Important nuance for the "no generic prebuilt paywall UI" requirement**:
RevenueCat Billing "uses Stripe as a payment gateway, and therefore
RevenueCat does not directly handle or store credit card information"
([RevenueCat Billing and Web SDK](https://www.revenuecat.com/docs/web/revenuecat-billing)).
Concretely, the card-entry step is a Stripe-powered embedded
component (Stripe Elements / Embedded Checkout) rendered by RevenueCat's
SDK — confirmed indirectly by open `purchases-js` GitHub issues that
reference `StripeServiceError` and "Stripe fullscreen checkout" /
"Inline (htmlTarget) Stripe checkout" by name (issues #1096, #1095, #973
— see below). This means the level of control available on Web is
**theming** (Appearance Editor tokens + inline-vs-modal placement via
`htmlTarget`), not a fully hand-built payment form the way a bespoke
Stripe Elements integration or a fully custom native Android screen would
be. You *can* build a fully custom offerings/pricing/package-selection
screen and skip `presentPaywall()` entirely (calling `purchase()`
directly against your own UI, same pattern Android already uses to avoid
RevenueCat's prebuilt paywall) — but the final card-entry surface itself
is still a RevenueCat/Stripe-rendered element, styled rather than
rebuilt. Open feature requests underline this is a live area of investment
rather than a finished one: issue #1178 asks RevenueCat to "expose a
colour-mode option on `PresentPaywallParams` so a host app can present the
paywall in its own theme," filed and still open as of this research.

**Verdict on Q3**: Embedded, in-page (not redirect), and brand-customizable
via the Appearance Editor + inline mounting — good enough for a bespoke
brand design at the theming/placement level. It is *not* as fully
hand-rollable as a raw Stripe Elements integration would be, and Android's
"no prebuilt UI" bar is a slightly higher bar than what Web Billing
currently offers for the payment-entry step specifically. This is a real,
but minor and non-blocking, gap: RigCheck's "Wandering Trails Wagging
Tails" brand design can very plausibly be matched via the Appearance
Editor's color/shape tokens plus inline mounting; a pixel-perfect custom
card form is not currently possible without dropping to raw Stripe
(i.e., Option 1B/1C territory).

## 4. Outages, deprecations, and maturity signals (as of Sept 2026)

**Status/uptime**: RevenueCat's [status page](https://status.revenuecat.com)
shows all systems operational, 100% uptime over the trailing 90 days as of
2026-09-23. The only recent incident (2026-09-16) was a drop in Google Play
pub/sub notification delivery affecting *Android* purchase event delivery
— unrelated to Web Billing — acknowledged by Google and resolved same day
(17:44 UTC). No Web Billing/Web SDK incidents appear in recent history.

**Release cadence / activity** (`RevenueCat/purchases-js` on GitHub, the
Web SDK repo):
- 8 releases in the 10 days from 2026-09-07 to 2026-09-17 (`v1.59.0`
  through `v1.63.1`) — active, frequent shipping, not stalled.
- 70 commits in the 30 days prior to this research.
- 44 issues ever filed against the repo, 28 closed / 16 open — a small,
  actively-triaged backlog for an SDK of this scope, not a graveyard of
  unaddressed problems.

Source: [`RevenueCat/purchases-js` releases](https://github.com/RevenueCat/purchases-js/releases)
and repo issue/commit history (queried via `gh api` against the public
GitHub API, 2026-09-23).

**Notable open issues relevant to a checkout integration** (primary
source: the repo's own issue tracker):
- [#1095](https://github.com/RevenueCat/purchases-js/issues/1095) — inline
  (`htmlTarget`) Stripe checkout can't be cancelled, and the orphaned
  Embedded Checkout instance breaks every later `purchase()` call on the
  same page. Real bug in exactly the inline-mount path RigCheck would use.
- [#973](https://github.com/RevenueCat/purchases-js/issues/973) — the
  fullscreen (modal) checkout drops `onClose` and has no visible cancel
  affordance.
- [#1096](https://github.com/RevenueCat/purchases-js/issues/1096) —
  `StripeServiceError` doesn't extend `Error`, so Stripe init failures
  report with a hardcoded message and no underlying cause (debuggability
  gap).
- [#1178](https://github.com/RevenueCat/purchases-js/issues/1178) — open
  feature request for a paywall colour-mode/theme option (see Q3).
- [#802](https://github.com/RevenueCat/purchases-js/issues/802) — flags
  that RevenueCat's own AI-integration prompt/docs reference a deprecated
  `configure()` API and lack SSR guidance — a thin-documentation signal,
  not a functional break.

None of these are deprecations or abandonment signals — they read as
normal in-flight bugs/requests for an actively developed product, but
#1095 and #973 are directly in the cancel/dismiss-handling path of the
checkout UX RigCheck would build against and should be accounted for in
implementation (test cancel flows explicitly; consider defensive handling
around repeated `purchase()` calls into the same `htmlTarget`).

**Product age**: RevenueCat Billing (Web Billing) launched
[2024-03-21](https://www.revenuecat.com/blog/company/introducing-revenuecat-billing)
as a generally-available product (not beta) on Pro/Scale/Enterprise plans,
with the Web Paywall SDK and additional payment gateways explicitly called
out at launch as "not yet supported." As of Sept 2026 (~2.5 years later),
those gaps have since closed: [Web Paywalls](https://www.revenuecat.com/docs/web/overview)
now ship, and "Web Billing" today spans **three swappable billing
engines** — RevenueCat Billing (RC's own checkout, Stripe under the hood),
Stripe Billing (bring-your-own Stripe account), and Paddle Billing — all
behind the same Web SDK integration surface. This is a relevant side
finding: even if Web Billing's own theming ceiling (Q3) or a specific rough
edge (Q4) became a blocker later, the "Stripe Billing" engine option means
a bring-your-own-Stripe reconciliation path (closer to Option 1B) is
reachable *without* leaving the RevenueCat SDK/API surface on Web — i.e.,
1A and 1B are not as sharply forked at the integration-code level as the
original framing suggested.

Source: [Getting Started With RevenueCat Web](https://www.revenuecat.com/docs/web/overview)

## Verdict

Nothing found here constitutes a real blocker to Option 1A. Consumable/
credit-pack purchases are supported, and specifically the Virtual
Currencies mechanism RigCheck's Android side already depends on has
explicit, version-pinned Web SDK support (Q1). The identity model needed
for a shared-account user ID is identical on Android and Web and isn't
Web-Billing-specific risk at all (Q2). Checkout is embedded and
brand-themeable, not a bare redirect to a RevenueCat-branded page, and
active development is visible in cadence and issue-tracker activity (Q3,
Q4). The one genuine, worth-tracking gap is that Web Billing's brand
customization ceiling is theming (colors/shapes/placement), not a fully
hand-built payment form — a real but narrow shortfall relative to
Android's "no prebuilt UI" bar — plus a couple of open bugs in cancel/
dismiss handling for the inline and modal checkout paths (#1095, #973)
that implementation should test against explicitly. Given the project
owner's own framing — RigCheck is low-volume and low-criticality, an
educational tool rather than a certified safety product — none of this
rises to a level that should block locking Option 1A. The original "newer
and less proven than Stripe" characterization was directionally fair as a
general caution but overstated as a specific risk once checked against
RevenueCat's actual current docs, status history, and repo activity.
