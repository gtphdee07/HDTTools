# Test credit cards for sandbox purchases

Use these when testing a purchase on Web (Buy Pro, Buy scan packs) with a **sandbox** RevenueCat key. They are Stripe's published test cards; no real money moves and they do not work on a production key.

## How to tell you are in the sandbox

`web/.env.local` has `VITE_REVENUECAT_WEB_PUBLIC_API_KEY` starting with `rcb_sb_` (sandbox). A production key starts with `rcb_` without `sb`. RevenueCat's sandbox runs on Stripe test mode, so only Stripe test cards are accepted ([RevenueCat: Testing Purchases](https://www.revenuecat.com/docs/web/web-billing/testing)). Do not put a sandbox key in `web/.env.production`.

## The card that succeeds

| Field | Value |
| --- | --- |
| Card number | `4242 4242 4242 4242` (Visa) |
| Expiry | any future date, for example `12/34` |
| CVC | any three digits |
| Postal code | any valid one |

Other card numbers (such as one starting `4646`) are not in the list below and the checkout may reject them. Use the card above.

## Cards that fail on purpose

Use these to check how the checkout reports a failed payment. Same expiry and CVC rules as above.

| What it simulates | Card number | Stripe error code |
| --- | --- | --- |
| Generic decline | `4000 0000 0000 0002` | `card_declined` (`generic_decline`) |
| Insufficient funds | `4000 0000 0000 9995` | `card_declined` (`insufficient_funds`) |
| Lost card | `4000 0000 0000 9987` | `card_declined` (`lost_card`) |
| Stolen card | `4000 0000 0000 9979` | `card_declined` (`stolen_card`) |
| Expired card | `4000 0000 0000 0069` | `expired_card` |
| Incorrect CVC | `4000 0000 0000 0127` | `incorrect_cvc` |
| Processing error | `4000 0000 0000 0119` | `processing_error` |
| Incorrect number (fails the number check) | `4242 4242 4242 4241` | `incorrect_number` |
| Velocity limit exceeded | `4000 0000 0000 6975` | `card_declined` (`card_velocity_exceeded`) |
| Attaches to a customer, but later charges fail | `4000 0000 0000 0341` | charge fails after attaching |

`4000 0000 0000 0036` is the card used to test a failed postal code check.

## Other ways to pay

- **Apple Pay and Google Pay**: in the sandbox these use a real card, but Stripe processes it in test mode, so nothing is charged ([RevenueCat: Testing Purchases](https://www.revenuecat.com/docs/web/web-billing/testing)). The plain card form above is the simpler test.
- **Cancel path**: open the checkout and close it without paying. That is the case the upstream cancel bugs are about (#11).

## Where this comes from

Stripe's full list, including cards for 3D Secure and other countries, is at [Stripe: Test cards](https://docs.stripe.com/testing). This file copies only the numbers checked on 2026-10-15; the part of Stripe's page after the first 100,000 characters was not read, so a card missing here may still exist there.

## Steps for a purchase test on localhost

1. In `web/`, set `VITE_REVENUECAT_WEB_PUBLIC_API_KEY`, `VITE_REVENUECAT_WEB_OFFERING_ID` and `VITE_SCAN_SERVICE_URL` in `.env.local` (never commit that file).
2. Run `npm run dev` and open http://localhost:5173.
3. Sign in with a test account and choose Buy Pro.
4. Enter `4242 4242 4242 4242`.
5. The account should show Pro and its starter scans; the grant can take a few seconds.
