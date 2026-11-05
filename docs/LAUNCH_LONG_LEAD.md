# Launch long-lead items L1 to L6 (owner guide)

Drafted 2026-11-05 for the joint Web and Android launch in [BETA_PLAN.md](BETA_PLAN.md). These are the steps only you can take, and most wait on a third party, so they start first. Each item says what to do, what to have ready, what it unlocks, and what is still unconfirmed. **Confirmed** means a Google, Stripe or RevenueCat page said it (the source is listed at the end). **Unconfirmed** means I wrote it from general knowledge or a third-party page; check it on the real sign-up screen before relying on it.

## How the six fit together

```
L1 business + D-U-N-S ──► L2 Play organization account ──► Play products, Play-signed Beta, listing
        │                                                      ▲
        ├──► L3 Stripe live ──► RevenueCat live Web Billing    │
        │                                                      │
L5 Web address ───────────► L6 listing content (needs privacy URL) ◄── L4 legal wording + pricing
```

L1 gates L2 and L3. L5 gates the privacy and deletion addresses that L6, L2 and L3 all ask for. L4 is writing and decisions, so it can run alongside everything else. Suggested order of attack: **L5 decision and L1 check this week, then L2 and L3 started the same day**, L4 and L6 in the background.

## L1. Business entity and D-U-N-S number

You said you already have a D-U-N-S number. What is left is a check, not a task:

- [ ] The legal name and address on the D-U-N-S record are exactly what you will type into Google and Stripe. Google checks the record against what you enter; a mismatch fails verification (third-party report, **unconfirmed** as Google policy). Fix the record at Dun & Bradstreet first if anything differs.
- [ ] The legal form of the business (LLC, corporation, sole proprietorship) and its tax id (EIN, or your SSN as a sole proprietor) are decided and written down. Stripe will ask for them (**unconfirmed** here: the pages I read confirmed that Stripe verifies the business, not the exact fields).
- [ ] Country, account type and D-U-N-S number are chosen carefully, because Google says they cannot be changed on an existing payments profile, and Stripe says the business origin country is locked once a service is live (**confirmed** for Stripe; Google's irreversibility is from a secondary summary of Google's notice).
- [ ] A business address and a phone number that can receive a verification call or text.

## L2. Google Play Console organization account

**Do:**
1. Choose the Google account that will be the Account Holder. Use an account you will keep for years (a dedicated business Google account, not a personal one that may change). Only the Account Holder can complete verification (**confirmed**, third-party).
2. Sign up for a Play Console developer account, choose **Organization**, pay the one-time registration fee (I recall $25; **unconfirmed**), enter the D-U-N-S number and the business details.
3. Verify the contact email and phone Google sends codes to, and complete any identity-document step Google asks for (**unconfirmed**: Google may ask for an ID or organization documents).
4. Set up the **payments profile** (bank account and tax details) in the console. Needed to sell in-app products through Play Billing (**unconfirmed** in exact menu naming).
5. Create the app, keep **Play App Signing** on (the default), and note the Play app-signing certificate's SHA-1: it must be added to the Google OAuth **Android** client, or Google sign-in will fail on Play-installed builds.
6. Create the in-app products and link RevenueCat to Play (service-account credentials). That is the part #40 waits on.

**Timing:** the D-U-N-S check is the slow step for new organization accounts; third-party pages say anywhere from days to about 30 days (**unconfirmed**). Starting this on day one is the point of this document.

**Two traps worth knowing now:**
- **Play refuses debuggable uploads.** The Alpha `beta` build is debuggable on purpose (#185) and Play rejects a debuggable APK with "you need to disable debugging before it can be published" (**confirmed** only through forum reports, not a Google page). So the Beta-on-Play build must be a non-debuggable, Play-signed bundle. The release guard (#166) refuses the Test Store key in such a build, so that Beta build has to use the real production RevenueCat key with Play license testers (Play's own test purchases). That means the Play account, one test product and the RevenueCat link to Play must exist **before** the Beta starts, not only before Release. If L2 is late, the Beta runs Android as an APK by file and the Play pipeline is first exercised in the release week, which I would not recommend.
- **Developer verification for installed APKs.** Google is rolling out an identity check for apps on certified Android devices, including apps installed from outside Play: enforcement starts 2026-09-30 in Brazil, Indonesia, Singapore and Thailand and reaches other countries in 2027 (**confirmed** by several reports; the US date is not named). Apps installed by `adb` are exempt. It does not affect a US Alpha today, and Play-distributed Beta and Release builds are covered by the Play account.
- **Target API level.** New apps and updates must target Android 16 (API 36) or higher since 2026-08-31 (**confirmed**, developer.android.com). The app targets 37, so it passes.

## L3. Stripe live mode, connected to RevenueCat Web Billing

**Do:**
1. Create (or upgrade) a Stripe account for the business and **activate** it: business details, the representative's identity, the bank account for payouts, a business website or app URL, and two-factor sign-in (**confirmed** that Stripe requires business verification before live use, a website or app URL for online sellers, correct bank details and 2FA before live charges). This needs L5 (the website address) and L1.
2. In RevenueCat, open the Web Billing configuration and connect the **live** Stripe account (the RevenueCat Stripe app from the Stripe App Marketplace). RevenueCat keeps sandbox and production as **separate** Web Billing configurations; the live public key (`rcb_...`) appears under the production configuration, and a config linked to the wrong Stripe account shows only a sandbox key (**confirmed** from RevenueCat docs and staff replies in the community forum).
3. Recreate the product, price and offering in the live configuration (sandbox objects do not carry over; **confirmed** for Stripe objects). Keep the same offering id (`default`) so the code does not change.
4. Register the **live** webhook endpoints separately from the test ones (**confirmed**, Stripe go-live checklist).
5. Turn on tax collection. RevenueCat Web Billing does **not** make RevenueCat the seller of record: you are, and tax is calculated through a provider you connect (Stripe Tax or Avalara). Stripe's own "Managed Payments" (where Stripe takes over tax) is not available through RevenueCat Web Billing (**confirmed**, RevenueCat docs). Decide who registers for sales tax where (see L4); Stripe Tax can watch the thresholds but you still own compliance.
6. Run one real low-price purchase and refund it (the proof step in `docs/PRODUCTION_CONFIG.md`, #211).

**Unlocks:** the production Web key for `web/.env.production` (swap with `scripts/wizard_web_revenuecat.sh`), and the one real-money test in the Beta.

**Unconfirmed:** Stripe's processing fees and RevenueCat's fee tier at your volume (needed for pricing in L4); check both fee pages when you set the price.

## L4. Legal wording and pricing (#34 and #33)

Two tickets already exist: **#34** (terms, refund policy, legal review) and **#33** (launch pricing). What each needs:

**Documents to produce (written plainly, reviewed by counsel if you use one; I am not a lawyer and this is not legal advice):**
- **Privacy policy** (#177 drafts it): must name every processor that touches personal data. From the code that is Supabase (account and rows), RevenueCat (purchases), Anthropic (the scan photo, sent through the Cloudflare Worker), Cloudflare (hosting and Worker logs), Google (sign-in) and Stripe (Web payments). It must say how to delete an account (#210).
- **Terms of service:** an acceptable-use clause, a limitation of liability, and above all the disclaimer that results are estimates and not certified weights or a safety determination. The app tells a person whether a rig is within weight limits, so this clause is the most important sentence in the document.
- **Subscription and refund terms:** price, billing period, that it renews automatically, how to cancel (Play for Android purchases, the Web billing portal for Web purchases), and the refund rule. Auto-renewal disclosure rules differ by state and by store (**unconfirmed**: ask counsel which apply to you).
- **Sales tax:** which states you must register in depends on your sales; see L3 step 5.

**Pricing inputs for #33:**
- Per-scan cost: measured in Alpha and Beta (the Anthropic Console shows spend; #183 logs help).
- Store fee: Google's service fee on Play subscriptions (I recall 15 percent; **unconfirmed**, check Play's current fee page) and Stripe's card fee on Web.
- Free-tier caps and Pro caps are placeholders today (Free 5 Rigs and 10 checks, Pro 25 and 50).
- Decide one price or two: Web and Android can differ by the fee, and Play's rules on pointing to a cheaper Web price are **unconfirmed** here, so ask before advertising a Web discount inside the Android app.

**What I can do for you:** draft the privacy text from the code and the data-flow facts (#177), list every claim to check, and collect the fee pages into the pricing sheet. Counsel (or your own judgment) approves the wording.

## L5. The Web address

**Decide:** custom domain or keep `rigcheck-web.pages.dev`. Recommended: a custom domain, because the address appears in the Play listing and data-safety form, in Stripe's activation, in Google sign-in, and in the privacy and deletion pages, and moving it later means redoing all of them.

**If you choose a custom domain, the steps are:**
1. Choose and register the name (Cloudflare Registrar sells domains at cost and keeps DNS in the same dashboard as Pages; **unconfirmed** as to price). Also check the name against trademark searches before you build a brand on it.
2. Add it to the Pages project as a custom domain (Cloudflare adds the DNS record and certificate when the domain's DNS is on Cloudflare).
3. Update every place that names the Web address: Supabase **Site URL** and **Redirect URLs**, the Google OAuth **Web** client (authorized JavaScript origins and redirect URIs), the RevenueCat Web Billing allowed domains if it asks, the Stripe business website, and the Android deep-link and privacy links. `docs/PRODUCTION_CONFIG.md` (#211) is the checklist for this.
4. Set up a support address on the domain (Cloudflare Email Routing can forward `support@yourdomain` to your Gmail for free; **unconfirmed** as to limits). Use it as the feedback and Play support address instead of the personal Gmail.
5. Keep `pages.dev` working as a second address until sign-in is proven on the new one.

## L6. Play listing content

Tracked by **#213**, which drafts what the repo can produce. What you decide or produce yourself:

- **Title and category** (the title limit is 30 characters, **unconfirmed** here). Check the name is not already used on Play and is not confusingly close to another app.
- **Descriptions:** short (80 characters, **confirmed**) and full (4000, **unconfirmed**).
- **Graphics:** app icon 512 x 512 PNG, 32-bit with alpha, at most 1024 KB (**confirmed**); feature graphic 1024 x 500 JPEG or 24-bit PNG without alpha (**confirmed**); phone screenshots (count and ratio **unconfirmed**; the ticket makes the session read the current Play page).
- **Declarations in the console:** privacy-policy URL; data-safety form including the account-deletion web link (**confirmed**: apps that let people create an account must give a web address where deletion can be requested, and temporary deactivation does not count); content-rating questionnaire; target audience; ads; app category; **App access** (reviewer sign-in details so the Google reviewer can open the app; a reviewer account that needs no email code and no payment, **third-party sources**, so keep it simple).
- **Contact details** shown publicly: email, website (L5), and for organization accounts the registered address (**unconfirmed** what Play shows publicly).

## What is blocked on what, in one list

| Item | Needs first | Unlocks |
|---|---|---|
| L5 address decision | nothing | privacy and deletion URLs, Stripe website, Play contact website |
| L1 check | nothing | L2, L3 |
| L2 Play account | L1 | Play products, Play-signed Beta, #40, listing entry |
| L3 Stripe live | L1, L5 | production Web key, live purchase test, tax setting |
| L4 legal and pricing | measured scan cost (Alpha) | #177 final text, #33 prices, #34 terms |
| L6 listing | L5, #177, #210, finished re-skin | Play review submission |

## Sources

- Google Play Help, new personal accounts testing requirement (applies to personal accounts created after 2023-11-13; organization accounts exempt): https://support.google.com/googleplay/android-developer/answer/14151465
- Google Play Help, account-deletion requirements and data-safety form: https://support.google.com/googleplay/android-developer/answer/13327111
- Google Play Help, preview assets (icon, feature graphic, short description): https://support.google.com/googleplay/android-developer/answer/9866151
- Android Developers, target API level requirements: https://developer.android.com/google/play/requirements/target-sdk
- Google Cloud Help, manage app audience (test users, basic scopes): https://support.google.com/cloud/answer/15549945
- Android Developers Blog, Play trust and transparency (D-U-N-S requirement for organization accounts): https://android-developers.googleblog.com/2023/07/boosting-trust-and-transparency-in-google-play.html
- Stripe docs, account activation and go-live checklist: https://docs.stripe.com/get-started/account/activate and https://docs.stripe.com/get-started/checklist/go-live
- RevenueCat docs, Web Billing tax and Stripe Managed Payments: https://www.revenuecat.com/docs/web/web-billing/tax and https://www.revenuecat.com/docs/web/integrations/stripe/stripe-managed-payments
- RevenueCat community, Web Billing sandbox and production keys: https://community.revenuecat.com/general-questions-7/web-billing-config-linked-to-live-stripe-account-only-rcb-sb-key-visible-no-production-rcb-key-7686
- Android developer verification timeline (news reports; confirm on developer.android.com): https://9to5google.com/2025/08/25/android-apps-developer-verification/
- Debuggable upload rejection (forum reports, no Google page found): https://forum.qt.io/post/441624
