# Android

The native Kotlin/Compose app: manual-entry-first, with an optional paid Claude-vision Scan (see Scan Proxy's `CONTEXT.md`; what the user is told for each way a Scan can end, and when a retry keeps the request id or offers Try again, is its "Scan outcomes" entry, which `ScanOutcomesFixtureTest.kt` checks this app against through `test-vectors/scan_outcomes.json`) for any of the three documents.

Android's `Rig`/`Breakdown`/`Item`/`Tone`/`Verdict` model mirrors Core/Web's shape exactly (`RecentRig.kt`, `BreakdownItem.kt`, `Tone.kt`, `VerdictInfo.kt`) but is its own independent implementation, not a shared library — see `CONTEXT-MAP.md`'s Relationships and ADR-0001. Definitions for those terms live in `src/hdttools/CONTEXT.md`; this file only covers what's genuinely Android-specific.

## Language

**Disclaimer**:
A blocking, once-per-app-session acknowledgment ("Experimental Tool — Not for Safety Decisions") shown before the first Results screen. Session/process-scoped only — never persisted, so it re-appears every app launch. Android's wording is deliberately its own, not shared with Web/Streamlit (see `CONTEXT-MAP.md`'s Relationships — each platform independently implements this gate), because the original text assumed OCR'd photos and Android defaults to manual entry.

**Entry Module**:
Which of the three documents (Truck Tag, Trailer Tag, or Scale Ticket) a given screen is currently collecting data for — the app's own routing/UI concept, not a Core concept.

**Check**:
One run through the three Entry Modules for one rig, from picking or starting the rig to Results. A Scan belongs to the Check and the screen it was started on: when the user picks or starts another rig, or leaves that screen (backs out or moves on), that Check is over for the Scan, and a result that arrives later is not used. Turning the device is not leaving.

**Account**:
The shared RigCheck sign-in (Supabase Auth; email + password and Google; Apple is deferred to the iOS port, #77) that Android shares with Web — the same account on every device. Its id is also the RevenueCat app user id, so purchases and the Scan Credit balance follow the account (ADR-0003, ADR-0004). Asked for only when something needs it — buying or scanning; the free manual-entry flow never requires one. Signing out affects this device only. Anonymous-id beta users are not migrated.

**Plan** (Free or Pro):
Whether the signed-in Account has the RevenueCat `pro` entitlement, however and wherever Pro was bought — a Pro bought on Web shows as Pro here, and the other way round (#27, ADR-0003, ADR-0006). Shown on the Paywall; read again when the Paywall opens and after a purchase or restore, since it can change on another device. Not known (signed out, RevenueCat not yet linked to the Account, or the read failed) is shown as nothing, never as Free. The Scan Credit balance follows the Account the same way and is read from the same place.

**Paywall** ("Get More Scans"):
What the Plan decides the Account may buy (#101, ADR-0006's 2026-10-12 amendment): a Free Account is offered Pro (the Offering's lifetime package) and no scan packs; a Pro Account is offered the scan packs and not Pro; while the Plan is not known nothing is offered, with Try again. Buying Pro keeps the Paywall open: the Plan and Scan Credit balance are read again and the packs replace the Pro offer. Buying a pack closes it. Pro is told from a pack by what RevenueCat reports about the package (lifetime package type; any other one-time package is a pack, a subscription is neither), never by product id; prices come from the store. The Android SDK does not report consumable versus non-consumable, which is why the lifetime package type is the marker. The scan service still checks only the balance, so this is enforced here, not there.

**Scan notice**:
The note above the fields of the entry screen reached after a delivered Scan (Truck Tag, Trailer Tag, Scale Ticket) that did not read every field: "A Scan was used and nothing could be read…" when it read none, or the unread fields named when it read some (#120). The Scan was charged whatever it read, so this tells the user one was used. A notice, not a failure: no Try again. Manual entry never shows it; it goes away when the user leaves the screen or types in the missing fields.

## Open question, not yet a term

`ANDROID_DESIGN_BRIEF.md` describes a two-tier purchase model (a "lifetime unlock" with preset credits, plus separate consumable "credit packs"). The Paywall now makes that distinction (see **Paywall** above, as Pro and scan packs), but don't treat "lifetime unlock"/"credit pack" as established vocabulary — the terms are Pro and scan pack, and pricing and pack sizes are still undecided (#33).
