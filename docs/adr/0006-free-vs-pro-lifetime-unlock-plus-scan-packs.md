# Pricing model: Free vs Pro (one-time lifetime unlock), scans sold as consumable packs

Decided 2026-10-02 (wayfinder ticket [#10](https://github.com/gtphdee07/HDTTools/issues/10), part of map [#3](https://github.com/gtphdee07/HDTTools/issues/3)). Reaffirms the 2026-08-14 "lifetime purchase + consumable credit packs, no subscription" decision from `ARCHIVE_MONETIZATION.md`, and extends it: the tier that ADR-0005 calls "plan" is concretely **Free vs Pro**.

- **Free**: manual entry, a small Garage and History cap, zero Claude-vision scans.
- **Pro** (one-time purchase, kept forever): larger Garage and History caps plus a starter bundle of scans. Pro is a RevenueCat entitlement shared across Android and Web (ADR-0003), so one purchase unlocks the shared account everywhere.
- **Scan packs**: consumable top-ups of the `SCAN` virtual currency. Packs add scans only, never caps.
- **Same price on every platform.** The fee difference between Google Play and RevenueCat Billing/Stripe is absorbed as margin variation. This also avoids a redesign when iOS arrives under stricter store rules.
- **Pricing rule, not dollar figures**: every scan pack, and the Pro bundle's starter scans, must net at least **5x the worst-case scan cost** (about $0.016, see [#9](https://github.com/gtphdee07/HDTTools/issues/9)) after platform fees. Dollar amounts, pack sizes and the exact Free/Pro cap numbers are set at launch, once fees are verified and real per-scan cost (including hidden thinking tokens) is measured.
- **Liability framing**: the product stays "educational, not certified." The Disclaimer gate stays, and the paywall repeats that results are not certified DOT weights. A short legal/terms/refund-policy review is the owner's pre-launch task.

## Considered options

- **Annual subscription for Pro**: rejected. Usage is a few times a year per owner, and per-account storage is bounded by the caps, so a one-time price covers it. It would also need a rule for Garage entries over the Free cap when a subscription lapses.
- **Scans gated only, flat Garage/History caps**: rejected. It drops the storage-cost lever and the upsell hook, and would require amending ADR-0005.
- **Scans, Garage and History each sold separately**: rejected for now. Heavily overlaps the capacity-upsell idea in [#13](https://github.com/gtphdee07/HDTTools/issues/13), which layers on top of Pro later.
- **Cheaper on Web**: rejected. It confuses shared accounts and may conflict with store policy.
- **Lock dollar figures now**: rejected. Cost data is still unmeasured, and pricing blind was the original reason for deferral.
- **Margin multiples of 3x and 10x**: 3x leaves fixed payment fees able to eat small packs; 10x risks prices that feel high for a few-times-a-year app.

## Amendment 2026-10-12: scan packs are for Pro users only

The decision above did not say who may buy a pack, and two places in the spec disagreed (story 31 "As a Pro user, I want to buy additional scans in packs"; story 36 "As a user with insufficient scans ... an easy way to buy a pack"). The Android paywall, which predates the Free/Pro model, listed every package in the offering to any signed-in user, and the Web "Buy more scans" card (#25) was first built the same way. Neither was a decision; the owner has now made it:

- **A pack is sold only to a Pro user, on every platform.** A Free user is offered Pro, not packs; after buying Pro they see the packs. This keeps "Free: zero scans" true, because the scan service checks only the Scan Credit balance, so a Free user holding scans could otherwise scan without Pro.
- **Enforced in the apps, not the Worker.** RevenueCat cannot limit a product to entitlement holders, and the Worker still charges on the balance alone. The remaining gap (a Free account that somehow holds scans, for example from before this rule) is accepted; checking the `pro` entitlement per scan in the Worker was considered and deferred (an extra RevenueCat read per scan).
- Web implements this (#25). Android follows in a separate ticket.
