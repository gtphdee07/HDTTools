# Design follow-up: 17 controls the first round did not have

For the Claude Design session that produced the first hand-back (`design-return/`). Same rules as `REDESIGN_BRIEF.md`: light theme only, same flow and same screens, a top app bar with Back, no bottom bar, your own tokens and components. Nothing in the first hand-back needs to change except where the new controls land in a frame you already drew.

## Why

The first round started from the 150-element inventory. Since then four small changes added controls to the app, and `ui-inventory.json` now lists 167 elements. The 17 new ones have no design yet, so the redesign map is incomplete. Attach the **updated** `ui-inventory.json` (167 elements), `REDESIGN_BRIEF.md`, and everything in `design-return/`.

## The 17 elements

Ids are final; do not rename them. "Today" is how it looks and sits now.

**Rig picker (`rig_picker`)**

| Id | What it is | Today |
|---|---|---|
| `picker.rig_delete_button` | Bin icon on each saved Rig card. Asks whether to delete that Rig; it must not start a check. Content description "Delete <nickname>". Shown only when signed in. One per card. | 48 dp Material icon button inside each Rig card (see the inventory for its exact place) |
| `picker.feedback_link` | "Send feedback" text button, opens an email to the beta address. Always shown. | Foot of the screen, primary (orange) text, 40 dp |
| `picker.feedback_no_mail` | "This phone has no email app. Write to <feedback address> instead." Appears under the link on a phone with no mail app. | Small body text under the link |

**Account / sign-in (`account`)**

| Id | What it is | Today |
|---|---|---|
| `account.feedback_link` | The same "Send feedback" link, for trouble signing in. Always shown. | Body of the screen, below the other buttons |
| `account.feedback_no_mail` | The same no-mail line as above. | Small body text under the link |

**Paywall (`paywall`)**

| Id | What it is | Today |
|---|---|---|
| `paywall.beta_label` | "Beta: test payments. Every purchase uses a test card; no real money moves." Bold. Beta builds only; it is absent from a production build. | Full-width line near the top of the body |

**Delete-Rig dialog (new screen `delete_rig`, an overlay on the Rig picker)**

| Id | What it is |
|---|---|
| `delete_rig.dialog` | The dialog. Overlay. |
| `delete_rig.title` | `Delete "<nickname>"?` |
| `delete_rig.body` | "This frees its spot in your Garage and can't be undone." |
| `delete_rig.error` | After a failed delete, in error colour: `We couldn't delete "<nickname>". It's still in your Garage; please try again.` |
| `delete_rig.confirm_button` | "Yes, delete" (reads "Deleting…" and is off while the delete runs) |
| `delete_rig.cancel_button` | "Cancel" (off while the delete runs) |

**Crash-report dialog (new screen `crash_prompt`, an overlay on any screen, shown at launch)**

| Id | What it is |
|---|---|
| `crash_prompt.question` | "RigCheck closed unexpectedly last time. Send details?" |
| `crash_prompt.details` | "It holds the error, the app version, your Android version and phone model. Nothing about your account or your rigs. Nothing is sent unless you tap Send." |
| `crash_prompt.no_mail_app` | "This phone has no email app. Write to <feedback address> instead." Replaces the question and details when Send finds no mail app. |
| `crash_prompt.send_button` | "Send" (hidden once the no-mail line replaces the question) |
| `crash_prompt.dismiss_button` | "Not now" (reads "OK" after the no-mail line) |

Both dialogs are Material 3 `AlertDialog`s today. They may keep that shape, restyled with your tokens, so long as the buttons stay at least 48 dp.

## What to hand back

1. **`ui-redesign-map-followup.json`**: for each of the 17 ids, the same `redesign` block you filled for the others (`status`, `new_screen`, `new_region`, `new_order`, `new_width`, `new_height`, `new_style`, `new_text`, `new_test_tag`, `notes`). `new_test_tag` equals the element's `test_tag_new` in the updated inventory. Anything you add beyond the 17 goes in `added_elements`, as before.
2. **Frames** (824 x 1784 px, `<screen>__<state>.png`, tags and legend as before). Re-issue these first-round frames with the new controls in place: `rig_picker__in` (with the bin on the card), `rig_picker__new_rig_typing` and `rig_picker__account_menu` if the bin or the feedback link shows in them, `account__sign_in` and `account__create_account` (feedback link), and the Paywall frames that show the offers (add the beta label; say in the notes which frames are "beta build only"). New frames: `delete_rig__confirm`, `delete_rig__error`, `delete_rig__deleting`, `crash_prompt__question`, `crash_prompt__no_mail_app`, `rig_picker__feedback_no_mail`, `account__feedback_no_mail`.
3. **`components.md` additions** for anything new (icon button on a card, dialog, text link). Reuse what you already defined where you can.
4. **`copy-changes.md`**: only if you want a string above changed (default: none). The owner approved the first round's copy; these strings are not yet reviewed.

## Two questions

- **Where does the bin go on the redesigned Rig card, and how does it stay clear of the card's own tap?** The card is one big tap target that starts a check.
- **The Paywall toast.** Your frames draw a dark in-app toast ("Purchase complete!"). Today it is an Android system Toast, which the app cannot restyle. Do you want it kept as a system toast (so drop the drawn one), or replaced by a Snackbar (a small code change, done with the Paywall re-skin)? If a Snackbar, say so in `notes` and give it an id.

## Not in this round

Nothing else changes. The pinned label crop stays deferred (#199), and the first round's decisions on the logo mark, fonts and the Truck balance chip stand.
