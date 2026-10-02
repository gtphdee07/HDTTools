# Garage (Rig collection) and History become account-synced via Supabase, capped per account

Decided 2026-10-02 (wayfinder ticket [#12](https://github.com/gtphdee07/HDTTools/issues/12), part of map [#3](https://github.com/gtphdee07/HDTTools/issues/3)). **Supersedes [ADR-0004](0004-supabase-for-shared-accounts-auth.md)'s "Rig/History stay local/per-device" scoping.**

New information surfaced this requirement: the real multi-device use case is **one shared account** used concurrently from multiple devices/platforms by different household members (e.g. husband on Android, wife on a future iOS app) — not separate accounts needing reconciliation. Device-local-only storage breaks this directly: each device shows a different Garage under the same account, and once Garage size becomes a plan-gated quota (per [#10](https://github.com/gtphdee07/HDTTools/issues/10)), per-device local enforcement would let a household exceed its entitled quota by filling each device's own copy of the cap independently.

**Decision**: Garage and History both become account-synced via the existing Supabase layer (ADR-0004), using the same account/device-count-agnostic model already used for entitlement (ADR-0003).

**Concurrency**: writes touching a quota-gated resource (adding a Rig once Garage size is plan-gated; inserting a History record under its own capped limit) reuse the idempotency-key pattern already proven on `workers/scan-proxy`'s Spend/Refund — a server-side capacity check before accepting the write, with a client-supplied idempotency key so a retried request can't double-count. Non-quota-gated writes (e.g. updating a Rig's last-used timestamp) stay simple last-write-wins — no scarce resource to protect there.

**History capping**: a fixed count per account, oldest record auto-pruned on insert — the same trim-to-N mechanic already used for Garage locally today (`web/src/recentRigs.ts`, `RecentRigsRepository.kt`), moved server-side — with the cap itself **tiered by plan**, a secondary upsell lever alongside pure cost control. The exact per-tier numbers belong to #10, not fixed here.

Also recorded on map #3: iOS is now acknowledged in the map's Notes as a planned future platform. No other already-locked decision on this map (#4–#7) needed revisiting — only #7/ADR-0004's Rig/History scoping line.

## Considered options

- **Local-first with opportunistic sync**: rejected — real conflict-resolution logic for near-simultaneous multi-device edits would reintroduce the reconciliation-engineering cost this project already chose to avoid once (ADR-0003's 1A-over-1B reasoning).
- **Permanent local-only** (ADR-0004's original scoping): rejected — doesn't satisfy the stated requirement, and risks a quota-enforcement leak under a plan-gated Garage size.
- **Time-based History retention window** (e.g. last 90 days) instead of a fixed count: rejected — doesn't give as hard a worst-case per-account storage/cost guarantee as a fixed count, since a very active household still generates proportionally more rows within any fixed time window.
- **Flat (non-tiered) History cap**: rejected — a tiered cap keeps the same cost-control property while also giving a monetization lever, at no extra mechanism cost over a flat cap.
