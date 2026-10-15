# The "Scan did not deliver" experience on Web and Android

Research for #111 (parent #15). Documentation and local reading only: no live Scan, no money spent, no deployed Worker called, no code changed.

- Read at commit `dd041c1` (`MPSkills`). #110 is merged (Web's 90 s limit is in `web/src/api.ts`); #79 and #101 are still open, so the Android code below is as they found it. Re-read the Android files if either lands before this is acted on.
- Terms follow the glossary: **Scan**, **Scan Credit**, **Spend / Refund** (`workers/scan-proxy/CONTEXT.md`), **Account token**, **Idempotency Key**. "Scan failed" means any case where the user pays attention to a Scan and does not end up with the fields they expected.
- Every claim about code cites `file:line`; every claim about the Worker's contract cites the document. A claim I inferred and did not read in code or see in a test is marked **(unverified)**.
- Out of scope, as the ticket says: Streamlit, what the Worker charges or refunds, any code change.

## Contents

1. [Summary](#summary)
2. [Phase 1: requirements](#phase-1-requirements) (R1 to R8)
3. [Phase 2: audit](#phase-2-audit) (Web, Android)
4. [Phase 3: gap table](#phase-3-gap-table)
5. [Phase 4: draft follow-up tickets](#phase-4-draft-follow-up-tickets)
6. [Decisions](#decisions) (D1 to D10, decided 2026-10-14)

## Summary

- **Web has the settled behaviour; Android has not caught up.** Web names each Worker error in its own words, keeps one request id across a lost answer, drops results for a gone check, locks the check while a Scan is in flight, gives up after 90 s, and tells the user a no-weight ticket Scan was used. Android shows the Worker's raw text or a raw exception message, makes a **new request id on every tap**, and has no lock or stale-result guard.
- **The one money-relevant Android gap is the request id.** After any lost answer (`network_error`, `parse_error`, `billing_error`, `extraction_failed_no_refund`, or the 60 s read timeout) Android's next tap is a new paid Scan, though the Worker's dedupe exists for exactly this. Nothing in #79, #101 or #110 covers it.
- **Both clients treat a delivered-but-blank main-path Scan the same way: straight to review, no words about the Scan Credit.** The stand-alone ticket path is handled on Web and not on Android.
- **Web's "Try again" after a no-weight answer is the #104 review finding.** It re-sends the same photo as a new paid Scan (`web/src/wizard/ReviewStep.tsx:134-140`).
- **Recommendation for where the rules live (R8):** one outcomes table in `workers/scan-proxy/CONTEXT.md` (the words), plus a shared fixture `test-vectors/scan_outcomes.json` that both clients' tests read, the same pattern as `test-vectors/breakdown_cases.json`.
- 16 gaps found (G1 to G16). G3, G5, G14 and G15 are covered in whole or part by #79 and G16 by #101; G11 is recorded as "accept" (decision D10); the other 10 need new tickets. Eight drafts (A to H) are in Phase 4.

---

## Phase 1: requirements

Written from the Worker's contract and the glossary, not from what the clients do. Each requirement ends with **Default** (what the audit is measured against) and **Why**. All defaults were put to the owner as D1 to D10 and accepted on 2026-10-14 (see [Decisions](#decisions)).

Sources for the contract:

- `workers/scan-proxy/README.md:30-41` (success and error codes), `:43-48` (CORS), `:50-56` (timeouts), `:58-86` (idempotency and its known gap, #96).
- `workers/scan-proxy/src/scan.ts:50-125` (spend, extract, refund flow and the exact response bodies), `workers/scan-proxy/src/index.ts:11-16` (the two auth errors).
- `workers/scan-proxy/CONTEXT.md:7-15` (Scan, Scan Credit, Spend / Refund, including the decision that a **delivered** Scan is charged even if the client finds nothing usable in it, #104).
- `web/CONTEXT.md:32-33` and `android/CONTEXT.md:3` (client Scan entries), ADR-0003 (one shared Worker and RevenueCat for both), ADR-0006 and its 2026-10-12 amendment (Free has zero Scans; packs are sold to Pro only; the Worker checks only the balance).
- Client error taxonomies: `web/src/scanError.ts:1-18`, `android/.../data/ScanApiClient.kt:32-38`.

### R1. The case list

Every way a Scan can end without usable fields. "Spent" is whether the Worker took a Scan Credit; "Refunded" whether it gave it back.

| # | Case | Where it comes from | Spent? | Refunded? | What the user must be told |
|---|---|---|---|---|---|
| 1 | `insufficient_credits` (402) | `scan.ts:75-79` | No | n/a | You are out of Scans; nothing was used. Next: buy a pack (Pro) or upgrade (Free); or type it in. |
| 2 | `unauthorized` (401) | `index.ts:16` | No | n/a | Your sign-in is not accepted; nothing was used. Next: sign in again. |
| 3 | `auth_unavailable` (503) | `index.ts:14`, README `:35` | No | n/a | We could not verify your account just now; nothing was used. Next: try again shortly (free). |
| 4 | `extraction_failed` (502) | `scan.ts:106-111` | Yes | **Yes** | We could not read the photo; the Scan Credit was refunded. Next: a clearer photo, or type it in. A new attempt is a new Scan. |
| 5 | `extraction_failed_no_refund` (502) | `scan.ts:113-123` | Yes | **No** (refund failed) | We could not read the photo and could not refund automatically. Next: try the same photo again (the same request id, so it is not charged again); contact support if it keeps happening. |
| 6 | `billing_error` (502) | `scan.ts:66-84` | **Unknown** | n/a | We could not confirm your balance, so nothing was read. You may or may not have been charged. Next: try again; the same request id means it is charged at most once. |
| 7 | `bad_request` (400) | `http.ts:30-31` | No | n/a | The request could not be accepted. Next: try a different photo, or type it in. (This is a client bug or an odd photo, not something the user can fix; do not echo the Worker's internal detail.) |
| 8 | A photo the client cannot send (unsupported format, still too large after shrinking, undecodable) | Web `scanImage.ts:60-73`; Android `PhotoEncoding.kt:19-22` | No (nothing sent) | n/a | Nothing was used; this photo cannot be sent. Next: a different photo, or type it in. |
| 9 | No scan service address in this build | Web `api.ts:45-59`. Android has none: the address is a compile-time constant (`ScanApiClient.kt:29`), so this case is Web-only. | No | n/a | Scanning is not set up here; nothing was used. Next: type it in. |
| 10 | No connection, or a reply that is not the Worker's (an edge error page, an unreadable success) | Web `api.ts:88-90, 118-120`; Android `ScanApiClient.kt:96, 103-105` | **Unknown** | n/a | We got no usable answer; you may or may not have been charged. Next: try again with the same request id (charged at most once). |
| 11 | A request that never answers (#110) | Web `api.ts:41, 63-72`; Android 30 s connect + 60 s read (`ScanApiClient.kt:69-72`) | **Unknown** | n/a | Same as 10, plus "it took too long". |
| 12a | Delivered, every field blank (main path) | `scan.ts:95` returns `ok:true` with whatever Claude gave; the Worker does not read document contents (`CONTEXT.md:15`) | **Yes** | **No** (decision of #104) | A Scan was used and nothing could be read from this photo. Next: a different photo, or type it in. |
| 12b | Delivered, no weight (stand-alone ticket) | same | **Yes** | **No** | Same words, plus that trying again uses another Scan. |
| 12c | Delivered, some fields filled | same | **Yes** | **No** | Show the filled fields for review; say which were not read. |
| 12d | Delivered, a field that looks wrong | same | **Yes** | **No** | Nothing special: the review step is where the user fixes anything that looks off. |

Inconsistency in the contract itself, to fix in the README: `README.md:39-40` says for `billing_error` that "spending never happened, so nothing to refund". `scan.ts:64-72` maps a *thrown* spend (RevenueCat unreachable or its 10 s timeout) to the same `billing_error`, and a timed-out request can have been applied by RevenueCat. Web already treats it as possibly charged (`web/src/api.ts:110-112`, `:24-25`). Row 6 above says "unknown" for that reason. A second README gap: the error list at `README.md:32-41` has no `extraction_failed_no_refund`, which `scan.ts:113-123` returns.

**Default:** this table is the case list. **Why:** it is the full set of outcomes the Worker can produce plus the client-side ones, and each row's "spent / refunded" comes from `scan.ts`, not from a client.

### R2. What the user is told

Every message answers four things, in this order, in one consistent set of words: **(a)** was a Scan Credit used, **(b)** was it refunded, **(c)** does a retry cost another, **(d)** the next step. Part (c) is stated wherever a retry is offered or a new photo is the next step (cases 3 to 6, 10 to 12); for cases 1 and 2 the next step is buying or signing in, so there is no retry to price.

The words, for both clients (the table in R1 gives the facts; this is the phrasing to approve):

| Case | Recommended message |
|---|---|
| 1 | "You're out of Scans. Nothing was used." + [Buy more Scans] or [Upgrade to Pro]; "or type the numbers in yourself." |
| 2 | "Your sign-in has expired. Nothing was used. Sign in again to scan." + [Sign in] |
| 3 | "We couldn't verify your account just now. Nothing was used. Try again in a moment." |
| 4 | "We couldn't read that photo, and your Scan Credit was refunded. Try a clearer photo, or type the numbers in yourself." |
| 5 | "We couldn't read that photo, and couldn't refund your Scan Credit automatically. Trying this photo again won't charge you again. If it keeps happening, contact support." |
| 6 | "We couldn't confirm your Scan balance, so nothing was read. You may not have been charged. Try again in a moment; a retry is not charged twice." |
| 7 | "We couldn't use that photo. Nothing was used. Try a different photo, or type the numbers in yourself." |
| 8 | Web's wording (`scanImage.ts:69, 72`), with "Nothing was used." added. |
| 9 | Web's wording (`api.ts:59`). |
| 10, 11 | "We didn't get an answer from the scan service [it took too long]. You may not have been charged. Try again; a retry is not charged twice." |
| 12a | "We used a Scan Credit but couldn't read anything on that photo. Try a different photo, or type the numbers in yourself." |
| 12b | Web's wording (`App.tsx:217-219`): the Scan was used, trying again uses another, type the weight in. |
| 12c | A one-line notice above the review fields: "A Scan was used. We couldn't read: <field labels>. Fill those in yourself." |

**Default:** four-part messages with the wording above, written once. **Why:** today the same case reads differently per client (Phase 2), and a user on both should not have to learn two vocabularies. "Scan Credit" in capitals in the glossary; in user-facing text "Scan" / "scan" is fine and is what Web already says ("You're out of scans", `api.ts:17`); the lower-case "scan credit(s)" in `android/.../PaywallScreen.kt:70` is the only drift from the glossary to fix.

### R3. Retry rules

- **Same request id** when the answer to the last request is unknown, because the service may or may not have charged: cases 5, 6, 10, 11 (the Web `lostResponse` flag, `web/src/scanError.ts:21-33`, and `ScanAttempts`, `web/src/scanAttempts.ts:7-21`). The retry must be for the **same photo** (the Worker's key also hashes the image, `README.md:62-66`).
- **New request id** after any answer that settles the attempt: success, case 1 to 4, 7, 12. The next Scan is a new paid Scan.
- **"Try again" is offered** after cases 3, 4, 5, 6, 10, 11 (it re-sends the same photo and is either free or correctly priced). It is **not** offered after case 1 or 2 (the next step is buying or signing in), after 7 and 8 (the same photo will fail again; offer "Choose a different photo"), or after 12 (see below).
- **After a delivered-but-unusable answer (12a, 12b): do not offer "Try again" with the same photo.** The same photo through the same model will probably give the same blank answer and it is a new paid Scan. Offer "Choose a different photo" and "Type it in". (#104's review noted that Web's stand-alone "Try again" re-sends the same photo at a new paid id.)
- **Known Worker caveat to keep in mind:** a same-key replay re-runs the extraction (README `:73-86`, tracked in #96). It does not change the client rule; it means "charged at most once" is about the balance, not about Claude cost.

**Default:** as above. **Why:** it keeps the charge to one for every lost answer and stops the app from selling the user a second, near-certainly identical, Scan.

### R4. Credit visibility

- After every outcome, read the balance again. For case 1 set it to 0 first (the Worker has just said so), so the screen is right even if the read fails; Web then also reads it back, Android does not need to (D6). Today Web does this for every outcome, including the "nothing was sent" cases 8 and 9, where the extra read is harmless (`web/src/App.tsx:142-153`, because `scan()` wraps `prepareImage` and the address check).
- If the re-read fails, keep the balance on screen and say nothing: the next Scan is checked by the Worker either way (Web's existing comment, `web/src/billing.tsx:233-235`).

**Default:** as above. **Why:** the balance on screen is a convenience, the Worker is the authority, and an error banner about the counter would be noise next to a more important Scan message. The alternative (a small "couldn't update your count" note) is listed in the decisions.

### R5. State while a Scan is in flight, and after it ends

- **A Scan lands in the check that started it, or nowhere.** While one is in flight the check cannot be left or restarted (Web's rule, `web/CONTEXT.md:33`), with a short note saying why. Where the platform cannot lock (Android back button, app switched away), a late result is **dropped** and the user is **told**: "A Scan finished after you left that check, so its result wasn't used. It used a Scan Credit."
- **One Scan at a time per check.** A second tap while one is in flight does nothing.
- **Backgrounding and rotation** must not lose or repeat a Scan: the in-flight state survives rotation.
- **Process death (Android) or reload (Web)** loses the in-flight state; the next attempt is a new request id. This is accepted, not engineered around, but the user is not told anything because they cannot be. The cost is bounded (one Scan Credit per occurrence).
- **A late result for a gone check** is dropped silently only where the lock makes it unreachable; elsewhere it is dropped with the notice above.

**Default:** as above. **Why:** #103 made Web's check a place where a result can only arrive in the right check. Android is a different shape (a shared ViewModel, no lock) and needs the "drop and tell" half.

### R6. Signed-out, Free and no-credit users

- Where each entry point sends them, with no photo taken first:
  - Signed out: sign in.
  - Signed in, Free: upgrade to Pro (packs are not sold to Free, ADR-0006 amendment; #101 on Android).
  - Pro with no Scan Credit: buy a pack.
  - Still loading or failed to load: "Checking your scans..." / "Try again".
- Both entry points (main upload, stand-alone ticket) follow the same rule.
- Typing the numbers in is always open.

**Default:** as above. **Why:** Web already does exactly this (`web/src/scanAccess.ts:5-32`, `components/ScanGate.tsx:43-75`); #79 and #101 bring Android to it.

### R7. Delivered-but-unusable on the main path

- **All fields blank (12a):** go to review with a notice above the fields: "A Scan was used and nothing could be read. Type the numbers in, or go back and choose a different photo." Do **not** treat it as a failure (no error state, no Try again, no refund claim): the Scan was delivered and charged (`CONTEXT.md:15`).
- **Some fields blank (12c):** go to review; the same notice names the unread fields.
- The user is told a Scan was used in both cases, because it was.

**Default:** a notice, not a failure. **Why:** a failure state would suggest a retry or a refund; neither is true. A review screen with a clear notice is the cheapest consistent answer and matches how the stand-alone ticket already behaves (the message says the Scan was used). **This is the owner's decision**; if the owner picks "treat all-blank as a failure", the gap rows marked (R7) below change as listed in the decisions.

### R8. Where the wording and rules live

**Recommendation (one place for the words, one fixture for the rules):**

1. **The words and the facts** (the R1 table, the R2 messages, the R3 retry rules) go in `workers/scan-proxy/CONTEXT.md` as a new "Scan outcomes" glossary entry. That file already owns Scan, Scan Credit, Spend / Refund and the "delivered is charged" decision (`:7-15`), both client CONTEXT.md files already defer to it (`web/CONTEXT.md:33`, `android/CONTEXT.md:3`), and `CONTEXT-MAP.md` lists it as the shared vocabulary.
2. **A shared fixture** `test-vectors/scan_outcomes.json` holds one row per case: `code`, `spent`, `refunded`, `retryKeepsRequestId`, `offersTryAgain`, `nextStep`, `messageContains` (phrases, not full text). Web (Vitest) and Android (JVM unit test) each load the same file and assert their own client against it, exactly as both already do for `test-vectors/breakdown_cases.json` (`CONTEXT-MAP.md:13-14`). A new case or changed rule then fails whichever client forgot it.
3. Each client keeps its **own message strings in one file** (Web: `api.ts` `MESSAGES`, or move them to `scanError.ts`; Android: a new `ScanMessages.kt` next to `ScanApiClient.kt`), checked by the fixture. No shared message table in code: the two clients are written in different languages and the repo's precedent is hand-port plus a shared fixture (ADR-0001, amended by ADR-0007).

**Why not the alternatives:** a shared message table in code needs a build step across Kotlin and TypeScript that the repo does not have; a glossary entry alone does not stop drift (it did not here: Android's wording never followed Web's). The fixture is the part that actually fails a build.

---

## Phase 2: audit

Method: read the files named in the ticket and the tests that exercise them. Nothing run live. Test file names are given with the test titles that pin a behaviour. "None" means I searched the test directories and found no test of it (Web: `web/src/**/*.test.ts(x)`; Android: `android/app/src/test` and `android/app/src/androidTest`; the Android suite listing is in the appendix).

Both audits are against the **recommended defaults** of Phase 1.

### Web

Files: `web/src/api.ts`, `scanError.ts`, `scanAttempts.ts`, `scanImage.ts`, `scanAccess.ts`, `App.tsx`, `wizard/UploadStep.tsx`, `wizard/ReviewStep.tsx`, `components/ScanGate.tsx`, `billing.tsx`.

**Per case (R1/R2/R3):**

| Case | What the code does | Exact message the user sees | Request id on retry | Pinned by |
|---|---|---|---|---|
| 1 `insufficient_credits` | Named error; balance set to 0 and re-read (`App.tsx:150-152`); the page then shows the no-scans gate with "Buy more scans" (`ScanGate.tsx:57-58, 68-69`). | "You're out of scans." (`api.ts:17`) plus the gate's "You're out of scans. Buy a scan pack ... or type the numbers in yourself." | New (answer settles it, `scanAttempts.ts:18`) | `api.test.ts:105-200` ("no scans left"); `App.scan.test.tsx:106`, `:122` (also when the re-read fails) |
| 2 `unauthorized` | Named error; not a lost response. Nothing changes the gate: access stays whatever `useScanAccess` says (`scanAccess.ts:20-32`), normally `ready`. | "Your sign-in has expired. Sign in again to scan." (`api.ts:18`). **No sign-in button** (the gate shows "N scans left"). | New | `api.test.ts` ("a token the service refuses", message only). Next step: **none** |
| 3 `auth_unavailable` | Named error, not lost. | "We couldn't verify your account just now, so nothing was scanned and you were not charged. Try again in a moment." (`api.ts:19`) | New | `api.test.ts` ("the service unable to verify the account") |
| 4 `extraction_failed` | Named error; the Extract Data button remains with the same photo (`UploadStep.tsx:101-105`). | "We couldn't read that photo, and your scan was refunded. Try a clearer photo, or type the numbers in yourself." (`api.ts:20-21`) | New | `api.test.ts` ("an extraction that failed and was refunded"); `App.scan.test.tsx:52` (refund, says so, try again) |
| 5 `extraction_failed_no_refund` | Named error with `lostResponse: true` (`api.ts:112`). | "...we couldn't refund your scan automatically. Trying this photo again will not charge you again. If it keeps happening, contact support." (`api.ts:22-23`) | **Same** | `api.test.ts` (flag and message); `App.scan.test.tsx:136`; `:245` (stand-alone, same id) |
| 6 `billing_error` | Named error, `lostResponse: true`. | "We couldn't confirm your scan balance with the payment service, so nothing was scanned. You may not have been charged. Try again in a moment; a retry is not charged twice." (`api.ts:24-25`) | **Same** | `api.test.ts` ("the payment service giving no answer") |
| 7 `bad_request` | Named error, not lost. | "The scan service could not accept that request (<Worker's message>)." (`api.ts:114-117`): echoes the Worker's internal detail. Does not say nothing was used. | New | `api.test.ts` ("a request the service rejects") |
| 8 Unsendable photo | `prepareImage` throws before any request (`scanImage.ts:60-73`). | "We can't read that kind of photo here. Use a JPEG, PNG, WebP or GIF, or type the numbers in yourself." / "That photo is too large to send. Try a smaller photo, or type the numbers in yourself." Does not say nothing was used. | n/a | `scanImage.test.ts` (all four paths); `api.test.ts:97` (nothing sent) |
| 9 No service address | `scanEndpoint()` null (`api.ts:45-59`). | "Scanning is not set up on this site. You can type the numbers in yourself." | n/a | `api.test.ts:88` |
| 10 No connection / not the Worker's reply | `network` (`api.ts:88-90`); `unknown` for an edge page or unreadable success (`api.ts:118-120`); both `lostResponse`. | "We couldn't reach the scan service. Check your connection and try again. A retry is not charged twice." / "We didn't get a usable answer from the scan service. Try again; a retry is not charged twice." (`api.ts:28-30`) | **Same** | `api.test.ts:204` and the two `unknown` cases; `App.scan.test.tsx:70` |
| 11 Never answers | `AbortController` plus a 90 s race over the whole exchange (`api.ts:41, 63-72, 98-101`); `timeout`, `lostResponse`. | "The scan service took too long to answer. Try again; a retry is not charged twice." (`api.ts:31`) | **Same** | `api.test.ts:218-310` (four tests, fake timers); `App.scanTimeout.test.tsx:47, 64, 86, 94, 111` (lock released; retry keeps the id) |
| 12a All blank, main path | `setWizard(... [moduleKey]: extracted, subStep: 'review')` (`App.tsx:174`): straight to review, blank inputs (`ReviewStep.tsx:72-85`). Copy is "Here's what we read off your photo. Fix anything that looks off" (`ReviewStep.tsx:68-70`). **No word that a Scan was used or that nothing was read.** | none | n/a | **None** (the success test uses non-empty fields, `App.scan.test.tsx:34`) |
| 12b No weight, stand-alone | Throws a plain `Error` after the Scan (`App.tsx:215-220`); `ReviewStep` stores the photo as `failedTicket` and shows **Try again** (`ReviewStep.tsx:44, 58, 134-140`). | "We read the ticket but couldn't find a weight. That Scan was used, and trying again uses another. You can also type the weight in." | New (the answer settled it) | `App.scan.test.tsx:170` (message, balance, and that Try again spends another) |
| 12c Partly filled | Same path as 12a. No notice, no mark on which fields are empty. | none | n/a | **None** |
| 12d Field looks wrong | Review step; any field is editable (`ReviewStep.tsx:72-85`). | n/a | n/a | `ReviewStep.test.tsx:22, 29` |

**R3 retry rules:** `ScanAttempts` keeps the id for the same `File` while the last answer was lost and resets it on any other outcome (`scanAttempts.ts:10-21`; tests `scanAttempts.test.ts:21, 30, 40`). "Try again" on the stand-alone ticket re-runs the failed `File` for *every* failure, including 12b (`ReviewStep.tsx:134-140`), and is hidden once the user can no longer scan (`:134`, test `ReviewStep.test.tsx:165`). On the main path there is no "Try again" button; the user presses Extract Data again with the photo still selected (`UploadStep.tsx:101-105`).

**R4:** the balance is re-read after success and after every failure; case 1 sets 0 first (`App.tsx:147-152`, `billing.tsx:226-236`). A failed re-read leaves the balance and says nothing (`billing.tsx:233-235`). Tests: `App.scan.test.tsx:122` (the 0 survives a failed re-read), balance counts in several tests. A failed re-read after success is untested.

**R5:** the check cannot be left or restarted while any Scan is in flight: header and footer `locked`, "Back to Dashboard" disabled, with the note "Reading your photo... you can leave this check once it's done." (`App.tsx:274-281, 328-348, 415`). A result for a changed check is dropped, and a failure for one is not shown (`App.tsx:173, 176, 206, 210`); the balance is still re-read. Double tap: Extract Data moves the step to `processing`, which unmounts the upload step (`App.tsx:164, 265-268`); the stand-alone button is disabled while reading (`ReviewStep.tsx:125`). Tests: `App.scanInFlight.test.tsx:49, 65, 79, 97, 113, 127`; `App.scanStale.test.tsx:22, 40, 55`. No test for a double tap (the code gives it by construction). A dropped result is **silent**. Page reload mid-scan loses the check and the request id (state is in React memory, `App.tsx:61, 75`) and there is no `beforeunload` guard (search of `web/src` found none): a Scan Credit can be spent and its result lost **(unverified in a browser; read from code)**.

**R6:** `useScanAccess` gives ready / unavailable / sign-in / checking / load-failed / upgrade / no-scans (`scanAccess.ts:5-32`); both Upload and the stand-alone section show the gate and hide the action unless `ready` (`UploadStep.tsx:99-105`, `ReviewStep.tsx:104-130`). Tests: `App.scan.test.tsx:277, 294, 306, 320, 333, 348, 361, 378`; `UploadStep.test.tsx:67, 72, 83`.

### Android

Files: `data/ScanApiClient.kt`, `ui/RigCheckViewModel.kt`, `ui/screens/ChooserScreen.kt`, `ui/screens/TruckTagEntryScreen.kt`, `ui/navigation/RigCheckNavHost.kt`, plus `data/PhotoEncoding.kt`, `data/ScanFieldMapping.kt`, `ui/screens/PaywallScreen.kt`. Paths under `android/app/src/main/java/com/rigcheck/app/`.

Android has one error type for everything: `ScanResult.Failure(code, message)` (`ScanApiClient.kt:32-38`), and the screen shows `message` in an "Scan failed" dialog with a single OK button (`ChooserScreen.kt:145-152`, `TruckTagEntryScreen.kt:234-241`). The message is **whatever the Worker's body said**, or the strings below.

| Case | What the code does | Exact message the user sees | Request id on retry | Pinned by |
|---|---|---|---|---|
| 1 `insufficient_credits` | `Failure("insufficient_credits", <Worker text>)`; balance not refreshed (`RigCheckViewModel.kt:231`) and **not set to 0**, so the chip keeps showing the old positive number. OK only; no buy button. | "Not enough scan credits." (`scan.ts:77`) | New (every tap) | **None** (the dialog test uses a made-up message, `ChooserScreenTest.kt:82`). #79 adds a test. |
| 2 `unauthorized` | Same path. OK only; no sign-in. | "Missing or invalid account token." (`index.ts:16`) | New | **None**; #79 adds a test and a next step. |
| 3 `auth_unavailable` | Same path. | "Could not verify your account right now." (`index.ts:14`). Does not say nothing was used. | New | **None**; #79. |
| 4 `extraction_failed` | Same path; balance refreshed. | "Could not read the image. Credit refunded." (`scan.ts:108`) | New | **None** |
| 5 `extraction_failed_no_refund` | Same path. | "Could not read the image, and we weren't able to automatically refund your credit. Please contact support if this keeps happening." (`scan.ts:118-120`). Says nothing about a retry. | **New**: a retry is a **new paid Scan** | **None** |
| 6 `billing_error` | Same path. | "Could not verify scan credits." (`scan.ts:69, 82`). Does not say whether anything was charged. | **New**: if the spend did apply, the retry charges again | **None** |
| 7 `bad_request` | Same path. | The Worker's `message` (a validation string). | New | **None** |
| 8 Unsendable photo | `encodePhotoForScan` throws (`PhotoEncoding.kt:20-22`); `runCatching` makes `Failure("client_error", e.message)` (`RigCheckViewModel.kt:216`). Nothing sent. | "Could not decode the captured photo." Does not say nothing was used or that typing is open. | n/a | **None** |
| 9 No service address | n/a: compile-time constant (`ScanApiClient.kt:29`). | n/a | n/a | n/a |
| 10 No connection / not the Worker's reply | `onFailure` -> `Failure("network_error", e.message ?: "Network error")` (`ScanApiClient.kt:96`); an unparseable body -> `Failure("parse_error", "Could not parse the server's response.")` (`:103-105`). | The raw exception text (for example "Unable to resolve host ...") or "Could not parse the server's response." Neither says a charge may have happened. | **New**: the code comment records the opposite assumption: "No client-side auto-retry... a client retry after a lost response risks a redundant paid Claude call" (`ScanApiClient.kt:75-77`) yet the id is regenerated each tap (`RigCheckViewModel.kt:211, 252`) | **None** (`ScanApiClientTest.kt:21, 28, 38` cover only how the request is built) |
| 11 Never answers | OkHttp `connectTimeout` 30 s, `readTimeout` 60 s (`ScanApiClient.kt:69-72`); a timeout is an `IOException`, so it is case 10. 60 s is shorter than the Worker's worst case, which Web's `api.ts:36-40` puts at about 87 s. | same as 10 (raw exception text) | **New** | **None** |
| 12a All blank, main path | `mergeScanFields` only overwrites a field when the Scan returned a value (`ScanFieldMapping.kt:24-44`), so blank leaves the entry screen as it was; `scanState` goes Idle and the app navigates to the entry screen (`RigCheckViewModel.kt:219-227`, `RigCheckNavHost.kt:84-86`). **No notice.** | none | n/a | **None** |
| 12b No weight, stand-alone | `standaloneWeightFrom` null -> `scanState = Error("Couldn't find a weight on that ticket — try a clearer photo, or enter it manually.")` (`RigCheckViewModel.kt:264-272`). Says nothing about the Scan being used; "try a clearer photo" invites a retry. No Try again button (OK only). | that message | New | **None** |
| 12c Partly filled | As 12a. | none | n/a | **None** |
| 12d Field looks wrong | Entry screen is editable. | n/a | n/a | entry-screen tests only |

**R3 retry:** the id is `UUID.randomUUID()` per tap, in both `performScan` (`RigCheckViewModel.kt:211`) and `performStandaloneScan` (`:252`), and is never kept across taps, so the Worker's dedupe never applies. The ViewModel comment says "no existing client-side retry loop, so generating it once here is enough" (`:207-210`), which is true of an automatic loop and not of the user pressing Scan Photo again. There is no Try again.

**R4 credit visibility:** the balance is re-read after success and after every failure except `insufficient_credits` (`RigCheckViewModel.kt:226, 231, 263, 276`); a failed re-read is ignored silently (`:157-162`, `runCatching ... onSuccess`). It is cleared to "not loaded" whenever the linked account changes (`:100-114`). The chip says "scan credit(s)" lower case in the paywall (`PaywallScreen.kt:70`). Tests: none for the ViewModel (no `RigCheckViewModel` test exists); `CreditBalanceChipTest` covers display only.

**R5 in flight:**

- State: `scanState = Loading` (`RigCheckViewModel.kt:204, 250`) shows a scrim and spinner over the Chooser (`ChooserScreen.kt:113-122`). `TruckTagEntryScreen` shows only the button label "Reading..." (`:180`), no scrim.
- No guard against a second `performScan` while Loading: it sets Loading and launches again unconditionally (`:204-205`). Whether a tap reaches the buttons under the scrim is **(unverified)**: the scrim `Box` declares no pointer input (`ChooserScreen.kt:114-118`), which in Compose normally lets touches fall through to the content below.
- The user can press Back during a Scan **(unverified: no back handler found in the files read)**. On success the ViewModel merges into the *current* `truck`/`trailer`/`scale` regardless of which rig or screen is current (`:220-224`) and calls `onDone(true)`, which navigates forward to the entry screen of the module captured when the Scan started (`RigCheckNavHost.kt:84-86`). A result for a rig the user has since left or replaced is therefore applied to the wrong rig and may navigate the user off wherever they went. This is Android's equivalent of #103.
- The `ViewModel` survives rotation, but the `onDone` lambda belongs to the composition that started the Scan **(unverified)**.
- Process death loses the Scan, the id, and the form state: the ViewModel has no `SavedStateHandle` (`RigCheckViewModel.kt:60-64, 66-83`). A Scan Credit may have been spent. **(unverified at runtime; read from code)**
- Tests: **none** for in-flight state.

**R6 entry points:**

- Main Scan Photo: allowed when `creditBalance > 0`, otherwise the paywall (`ChooserScreen.kt:97-103`); a signed-out user has no balance (`RigCheckViewModel.kt:111`), so is sent to the paywall route, which for a signed-out user shows the account screen (`RigCheckNavHost.kt:102-112`). Tested: `ChooserScreenTest.kt:61`; `RigCheckNavHostTest.kt:115` (signed out -> "Continue with Google" -> back).
- Stand-alone ticket: **no gate at all** (`TruckTagEntryScreen.kt:176-181`): a signed-out user takes a photo and gets "Scan failed / Sign in to scan." with no path to sign in (`RigCheckViewModel.kt:48, 253-254`). Covered by #79.
- Free vs Pro: the main gate looks at the balance only, so a Free user with no balance lands on the pack paywall (#101).

---

## Phase 3: gap table

Status per requirement and client. **Met** / **Gap** / **Differs between clients** / **Untested** (behaviour appears right but nothing pins it). "Covered" names an open ticket that already contains the work.

| Req | Web | Android | Notes |
|---|---|---|---|
| R1 cases 1-6, 10-11: named, correct spent/refunded | **Met** (`api.ts:16-31, 108-120`) | **Gap**: Worker text or raw exception shown; nothing says what a charge did for cases 6, 10, 11 | G2 |
| R1 case 7 bad_request | **Gap**: echoes the Worker's detail (`api.ts:115`) | **Differs**: shows the Worker's text, same cause | G10 |
| R1 case 8 unsendable photo | **Met** wording; missing "nothing was used" | **Gap**: "Could not decode the captured photo." (`PhotoEncoding.kt:22`) | G2, G10 |
| R1 case 12 delivered-but-unusable | **Gap** main path (no notice); **Met** stand-alone no-weight | **Gap** main path; **Gap** stand-alone wording (does not say Scan was used) | G8, G9 |
| R2 consistent words | **Differs between clients** | **Differs between clients** | G2 |
| R2 next step offered | **Gap**: no sign-in action after `unauthorized` (`api.ts:18` message; gate stays `ready`) | **Gap**: OK-only dialog for every case. **Covered in part by #79** (401, 503, 402, `not_signed_in`) | G3, G6 |
| R3 same id after a lost answer | **Met** (`scanAttempts.ts`, tests) | **Gap** (new id every tap, `RigCheckViewModel.kt:211, 252`) | G1 |
| R3 Try again only where R3 allows | **Gap**: on the stand-alone ticket `failedTicket` is set for every failure (`ReviewStep.tsx:58, 134-140`) and hidden only when the user can no longer scan (`canScanTicket`), so it also shows after `unauthorized`, `bad_request`, an unsendable photo and the no-weight answer | **Met** (no Try again anywhere; also none after the cases that should have it, see G2/G3) | G7 |
| R4 re-read after every outcome | **Met** | **Differs**: 402 leaves the old positive balance (`RigCheckViewModel.kt:231`) | G5. #79's 4th criterion says "balance not refreshed on 402, as today" |
| R4 failed re-read | **Met** (default: silent), **Untested** after success | **Met** (silent), **Untested** | |
| R5 locked while in flight | **Met** (`App.tsx:274-348`; tests `App.scanInFlight.test.tsx`) | **Gap**: no lock; no re-entry guard (`RigCheckViewModel.kt:204`) | G4 |
| R5 result for a gone check | **Met** (dropped, `App.tsx:173,176,206,210`; tests `App.scanStale.test.tsx`); silent but practically unreachable behind the lock | **Gap**: applied to the current rig and navigates (`:220-224`, `RigCheckNavHost.kt:84-86`) **(unverified at runtime)** | G4 |
| R5 reload / process death | **Gap** (unverified in a browser): no `beforeunload`, loses id | **Gap** (unverified): no `SavedStateHandle` | G11 (documented, accept) |
| R5 timeout | **Met** (90 s, tests) | **Gap**: 60 s read timeout is shorter than the Worker's worst case (Web's `api.ts:36-40` computes about 87 s) and a timeout is a new-id retry | G1, G12. #110 was Web only |
| R6 signed-out / Free / no credit | **Met** both entry points (tests `App.scan.test.tsx:277-378`) | main **Met** for signed-out (`RigCheckNavHostTest.kt:115`); **Gap** for Free (**#101**); stand-alone **Gap** (**#79**) | |
| R7 main path blank/partial | **Gap** | **Gap** | G8 |
| R8 one place for words and rules | **Gap**: Web's strings are in `api.ts`; nothing checks them against the other client | **Gap**: none | G13 |
| Tests for response handling | **Met** (`api.test.ts`) | **Untested**: `ScanApiClientTest.kt` has 3 tests, all on building the request; response parsing and every error code are unpinned. **Covered in part by #79** (401, 503, 402, `not_signed_in`) | G14 |
| Glossary wording | **Met** | **Gap**: "scan credit(s)" lower case at `PaywallScreen.kt:70` | G2 |

### Gap register

| ID | Gap | Client | Size | Covered by open ticket? | Verified? |
|---|---|---|---|---|---|
| G1 | A retry after a lost answer is a new request id, so it can be charged twice (`RigCheckViewModel.kt:211, 252`); 60 s read timeout makes that more likely | Android | Medium | No | Read in code; double charge itself not exercised live |
| G2 | Error text is the Worker's raw message or a raw exception; no consistent four-part wording; "Scan failed" title always | Android | Medium | No | Read |
| G3 | OK-only dialog: no next step (sign in, buy, upgrade) for any case | Android | Medium | **#79** for 401, 503, 402, `not_signed_in` only; the rest is new | Read |
| G4 | No in-flight lock or re-entry guard; a result is applied to the current rig and navigates after the user left | Android | Large | No | Read; runtime behaviour **unverified** |
| G5 | 402 leaves the old balance on screen (`:231`) | Android | Small | **#79** criterion 4 says to keep it; see decision D6 | Read |
| G6 | No sign-in button after `unauthorized` | Web | Small | No | Read; whether `auth.user` is still set after a refused token is **unverified** |
| G7 | The stand-alone ticket's "Try again" is offered after a delivered-but-unusable (no-weight) answer (#104's review finding), and also after `unauthorized`, `bad_request` and an unsendable photo, where the same photo fails again or the next step is signing in | Web | Small | No | Read; the no-weight case is test-confirmed (`App.scan.test.tsx:170`); the other three are read from `ReviewStep.tsx:58, 134-140` and have no test |
| G8 | Main path: an all-blank or partly filled Scan goes to review with no word that a Scan was used | Web and Android | Small per client | No | Read |
| G9 | Android stand-alone no-weight message does not say the Scan was used or that a retry costs another, and invites a retry | Android | Small | No | Read |
| G10 | `bad_request` and unsendable-photo wording: Web echoes internal detail and lacks "nothing was used" | Web (and Android as part of G2) | Small | No | Read |
| G11 | Page reload or process death during a Scan loses the result and the id | Web, Android | n/a (accept) | No | **Unverified** |
| G12 | Android's 60 s read timeout is below the Worker's worst case (about 87 s per Web's comment) | Android | Small | No | The 87 s figure is from `web/src/api.ts:36-40`; I did not re-derive it. `claude.ts` defines `ANTHROPIC_TIMEOUT_MS = 20_000` (`:18`), passes it as `timeout` and sets no `maxRetries` (`workers/scan-proxy/src/claude.ts:26`); the SDK's default retry count is outside this repo **(unverified)** |
| G13 | No single place for outcome words and rules; clients drifted | Both | Medium | No | Read |
| G14 | Android has no tests for Worker responses or error codes; no ViewModel tests | Android | Medium | **#79** for four codes | Read |
| G15 | Standalone scan button ungated for signed-out and no-credit users | Android | Small | **#79** | Read |
| G16 | Free users on Android are sent to the pack paywall | Android | Medium | **#101** | Read |

The #104 review findings: *Try again after a delivered-but-unusable answer* is G7; *the main-path all-blank result* is G8.

---

## Phase 4: draft follow-up tickets

Drafts for the owner to file. Style follows #102 to #110. They are posted as a comment on #111, not filed. Each states the shared decision once.

Related open tickets stay as they are: **#79** (Android gate and four error cases), **#101** (Android packs only for Pro). Drafts A and B below are written to sit beside #79 and not repeat it.

### Draft A (Android): a retry after a lost answer keeps the request id

**What is wrong.** `RigCheckViewModel.performScan` and `performStandaloneScan` create a new `UUID` per tap (`RigCheckViewModel.kt:211, 252`), so after a lost answer (`network_error`, `parse_error`, a 60 s read timeout, `billing_error`, `extraction_failed_no_refund`) the user's next tap is a new Scan the Worker cannot dedupe. Web fixes this with `ScanAttempts` (`web/src/scanAttempts.ts`).

**What to build.** Keep the id for the same photo until the answer settles the attempt (a Worker answer of any kind other than the lost-answer codes). Mirror Web's rule: same photo plus last answer lost -> same id; otherwise new. Decide how "same photo" is told apart (the photo URI).

**Acceptance criteria**

- [ ] A second Scan of the same photo after `network_error`, `parse_error`, `billing_error` or `extraction_failed_no_refund` sends the same `client_request_id`
- [ ] A Scan after a settled answer (success, `insufficient_credits`, `extraction_failed`, `unauthorized`) or of a different photo sends a new id
- [ ] Both Scan entry points behave the same
- [ ] Tested with a fake Scan client (no network); the tests fail without the change

Blocked by: none. Shares the outcome table (Draft G) but does not need it.

### Draft B (Android): say what happened and offer the next step for every Scan outcome

**What is wrong.** The "Scan failed" dialog shows the Worker's raw text or an exception message with only OK (`ChooserScreen.kt:145-152`, `TruckTagEntryScreen.kt:234-241`). Cases 5, 6, 10 and 11 never say whether a Scan Credit was used, and no case offers a next step (the next step for 401, 503, 402 and `not_signed_in` is in #79; this ticket does the rest and the wording for all).

**What to build.** Replace the dialog text with the Phase 1 R2 messages, keyed by outcome, kept in one file (`ScanMessages.kt`); add the "Try again" and "Choose a different photo" actions per R3; fix the lower-case "scan credit(s)" in `PaywallScreen.kt:70`; say so when the photo could not be encoded. Do not change what #79 owns (the sign-in and paywall routing).

**Acceptance criteria**

- [ ] Each case in the R1 table (rows 1-8, 10, 11) shows the R2 wording, including whether a Scan Credit was used and whether a retry costs another
- [ ] The stand-alone ticket's no-weight answer (row 12b, gap G9) says the Scan was used and that trying again uses another, offers "Type it in" and "Choose a different photo", and has no "Try again"
- [ ] "Try again" is offered only after cases 3, 4, 5, 6, 10, 11 and re-sends the same photo (id behaviour per Draft A)
- [ ] After case 7 or 8, a "choose a different photo" action is offered
- [ ] Balance after a 402 is set to 0 locally with no network refresh (so #79's "no refresh on 402" still holds; see decision D6)
- [ ] Tested at ViewModel / screen level with a faked `ScanApiClient`, one test per case

Blocked by: #79 (shares the dialog and the routing). The wording (D4) is approved.

### Draft C (Android): one Scan at a time, and a result that arrives for a changed check is dropped

**What is wrong.** There is no lock, no re-entry guard (`RigCheckViewModel.kt:204`), and a result is merged into whichever rig is current and navigates to the entry screen of the module that started it (`:220-224`, `RigCheckNavHost.kt:84-86`). The user can leave, pick another rig, and have the old photo's result written into it.

**What to build.** Ignore a second Scan tap while one is in flight; note which check (rig selection) a Scan started in and drop its result if the check has changed, telling the user "A Scan finished after you left that check, so its result wasn't used. It used a Scan Credit." (R5). Decide whether to lock Back while in flight or only drop and tell. Verify first, on the emulator, what Back, rotation and the scrim actually allow today; this research marks all of that unverified.

**Acceptance criteria**

- [ ] A second Scan tap while one is in flight does nothing and sends nothing
- [ ] A result arriving after the user has left the check, or started another rig, does not change the current rig and does not navigate
- [ ] The user is told a Scan was used and its result dropped
- [ ] The balance is still re-read
- [ ] Tested with a delayed fake Scan client; fail without the change

Blocked by: none. Do after A and B so the messages exist.

### Draft D (Web and Android, one ticket per client): main-path Scan that delivered nothing usable says a Scan was used

**What is wrong.** A Truck Tag, Trailer Tag or Scale Ticket Scan that returns all-blank (or partly blank) fields goes to review with no word about the Scan Credit (`web/src/App.tsx:174`; `RigCheckViewModel.kt:219-227`). #104 left this out of scope. **Shared decision (D1, decided):** a notice on the review screen, not a failure.

**What to build.** On the review screen after a Scan, if no field was filled: "A Scan was used and nothing could be read. Type the numbers in, or go back and choose a different photo." If some were not filled: name them. No "Try again" (R3). Web: `ReviewStep` plus a flag from `App.tsx`. Android: the entry screen after `performScan`.

**Acceptance criteria**

- [ ] An all-blank Scan reaches review with the notice and no Try again
- [ ] A partly filled Scan names the unread fields
- [ ] A fully filled Scan shows no notice
- [ ] The balance still drops by one and is re-read
- [ ] Tested at the interaction level; fail without the change

Blocked by: none (D1 is decided).

### Draft E (Web, small): Web gaps from this audit

**Shared:** the Phase 1 wording (R2) once.

1. After `unauthorized`, offer a "Sign in again" action (G6); the gate stays `ready` today (`ScanGate.tsx:43-60`).
2. Offer the stand-alone ticket's "Try again" only after cases 3, 4, 5, 6, 10 and 11 (R3). After the no-weight answer, `unauthorized`, `bad_request` and an unsendable photo, offer "Choose a different photo" (and, for the no-weight answer, "Type it in") instead (G7, `ReviewStep.tsx:58, 134-140`).
3. Stop echoing the Worker's detail for `bad_request` and add "Nothing was used." to `bad_request` and unsendable-photo messages (G10, `api.ts:115`, `scanImage.ts:69,72`).

**Acceptance criteria**

- [ ] After a refused account token the user sees "Sign in again" and it leads to the Account screen and back to the same check
- [ ] After the no-weight answer there is no "Try again", and there is a way to choose another photo and to type the weight
- [ ] `bad_request` and the two photo messages say nothing was used and contain no Worker internals
- [ ] Tests for each, failing without the change (update `App.scan.test.tsx:170`, which currently asserts Try again)

Blocked by: none (D2 and D3 are decided).

### Draft F (Android): Scan timeout covers the Worker's worst case

**What is wrong.** `readTimeout(60s)` (`ScanApiClient.kt:71`) is below the Worker's worst case (about 87 s per `web/src/api.ts:36-40`), so the app can give up on a Scan the service delivers; combined with G1 the retry is a second charge.

**What to build.** Set a limit that outlasts the Worker's worst case, as Web's #110 did (90 s), covering the whole call (`callTimeout`, so a trickling reply is bounded too), and treat a timeout as a lost answer (R3). Re-derive the Worker's worst case at the time.

**Acceptance criteria**

- [ ] A request that never answers is abandoned after the limit and reported as a lost answer ("took too long, a retry is not charged twice")
- [ ] The retry keeps the request id (Draft A)
- [ ] A reply that arrives before the limit is unaffected
- [ ] Tested with a fake server or clock; no real waiting

Blocked by: A.

### Draft G (both clients): shared Scan outcomes table and fixture

**What is wrong.** Words and rules for a Scan that does not deliver live in each client's code; they drifted (Phase 2).

**What to build.** (1) A "Scan outcomes" entry in `workers/scan-proxy/CONTEXT.md` with the R1 table, R2 words and R3 rules; (2) `test-vectors/scan_outcomes.json`; (3) one test per client that loads it and checks that client; (4) fix the README at `workers/scan-proxy/README.md`: the sentence at `:39-40` ("spending never happened") to match `scan.ts:64-72`, and add the missing `502` `extraction_failed_no_refund` entry to the error list at `:32-41` (the Worker returns it, `scan.ts:113-123`).

**Acceptance criteria**

- [ ] The glossary entry exists and both client CONTEXT.md files point at it
- [ ] The fixture covers every R1 case
- [ ] Web and Android each have a test that fails when a case's message, retry-id rule, or Try-again rule differs from the fixture
- [ ] The README statement about `billing_error` matches the code, and the README lists `extraction_failed_no_refund`

Blocked by: none (D4 and D5 are decided). Land it before B, or alongside it.

### Draft H (Android): tests for the Worker's responses

**What is wrong.** `ScanApiClientTest.kt:21, 28, 38` test only how the request is built; response parsing, every error code, and the empty-fields success are unpinned.

**What to build.** Tests for `ScanApiClient.scan` against a fake HTTP server (OkHttp `MockWebServer`) covering every Worker code and the client-side `network_error` and `parse_error`; success with empty `fields`. Overlaps #79 for 401, 503, 402 and `not_signed_in` at the screen level; this ticket is the client layer, #79 the user-visible layer.

**Acceptance criteria**

- [ ] One test per Worker error code and for `network_error` / `parse_error` asserts the code and message returned
- [ ] A success with `fields: {}` returns Success with no fields
- [ ] The tests fail if a code is mapped wrongly

Blocked by: none.

---

## Decisions

**Decided by the owner on 2026-10-14: D1 to D10 each take the recommended default below** (D9: check first, as the default says). The audit above was finished against these defaults, so no gap, requirement or draft changes. The last column records what the alternative would have changed.

| # | Decision | Decided (the recommended default) | If the owner had chosen differently, these would change |
|---|---|---|---|
| D1 | A main-path Scan that comes back all-blank or partly blank (R7) | Go to review with a notice that a Scan was used; not a failure | If it becomes a **failure**: G8 and Draft D become "show the error state and Try again"; R3's "no Try again after 12" and G7 flip for the main path; the stand-alone no-weight rule stays |
| D2 | Offer "Try again" after a delivered-but-unusable answer (R3) | No; offer "Choose a different photo" and "Type it in" | If **yes**: G7 closes (Web's behaviour is kept); Draft E item 2 is dropped; Android's stand-alone ticket must get a Try again (G9 grows) |
| D3 | Wording of `bad_request` and unsendable-photo messages | Plain wording, no Worker internals, "Nothing was used." | Draft E item 3 and Draft B change wording only |
| D4 | The R2 messages (the words in both clients) | As written in R2 | Drafts B, E and G change wording only |
| D5 | Where wording and rules live (R8) | CONTEXT.md entry plus `test-vectors/scan_outcomes.json` | If only a glossary entry: Draft G loses its fixture and tests, and G13 stays partly open |
| D6 | Balance after a 402 on Android | Set to 0 locally with no network re-read, so #79's "not refreshed on 402" still holds (Web's extra re-read after the 0 is not required on Android) | If #79's criterion is meant literally with no local 0: G5 stays open and Android keeps showing a positive balance after the Worker said none left |
| D7 | A failed balance re-read (R4) | Silent, keep the balance | If a note is wanted: new small ticket on both clients |
| D8 | Result for a gone check on Android (R5) | Drop it and tell the user | If only drop silently: Draft C loses its notice criterion |
| D9 | Lock Back on Android while a Scan is in flight | Check first: Draft C starts by verifying on the emulator what Back, rotation and the scrim allow today, then decides | Affects the size of Draft C (large with a lock, medium without) |
| D10 | Page reload / process death mid-Scan (G11) | Accept and document; one Scan Credit at risk | If not accepted: a `beforeunload` guard on Web and a `SavedStateHandle` on Android, both new tickets |

## Appendix: what was read

Worker: `workers/scan-proxy/README.md`, `CONTEXT.md`, `src/scan.ts`, `src/index.ts:8-20`, `src/http.ts:30-31`, `src/claude.ts:16-26`. Docs: `CONTEXT-MAP.md`, `web/CONTEXT.md`, `android/CONTEXT.md`, ADR-0003, ADR-0006 and its amendment, `docs/agents/session-handoff.md`. Web: `api.ts`, `scanError.ts`, `scanAttempts.ts`, `scanImage.ts`, `scanAccess.ts`, `App.tsx`, `wizard/UploadStep.tsx`, `wizard/ReviewStep.tsx`, `components/ScanGate.tsx`, `billing.tsx:140-270`; tests `api.test.ts`, `App.scan.test.tsx`, `App.scanInFlight.test.tsx`, `App.scanStale.test.tsx`, `App.scanTimeout.test.tsx`, `scanAttempts.test.ts`, `scanImage.test.ts`, `wizard/UploadStep.test.tsx`, `wizard/ReviewStep.test.tsx` (titles). Android: `ScanApiClient.kt`, `RigCheckViewModel.kt`, `ChooserScreen.kt`, `TruckTagEntryScreen.kt`, `RigCheckNavHost.kt:55-182`, `PhotoEncoding.kt`, `ScanFieldMapping.kt`, `PaywallScreen.kt:70`, `SupabaseAccountBackend.kt:102`; tests `ScanApiClientTest.kt`, `ChooserScreenTest.kt`, `TruckTagEntryScreenTest.kt`, `RigCheckNavHostTest.kt`, `CreditBalanceChipTest.kt` (titles). Open tickets read: #79, #101, #110 (closed).

Not run: any suite. Test coverage statements come from reading test titles and the bodies quoted above, not from a run.
