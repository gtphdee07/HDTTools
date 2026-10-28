# Components

Light theme. Sizes in dp. Every touch target is 48 x 48 dp or larger. Names match the `new_style` value in `ui-redesign-map.json` and the `data-style` of the frames. Token names are from `tokens.json`. Every control has default, pressed, focused, disabled and (for inputs) error states; where a state is not drawn, the rule below is the build reference.

Pressed state, all controls: Material ripple using the control's text colour at 12%. Focus (keyboard or switch access): 2 dp `purple-deep` outline with a 2 dp offset, on every surface.

## Top app bar (header)
Used on every screen except Disclaimer and Splash.
- **Anatomy:** teal fill, 24 dp bottom corners, shadow `sm`. Status bar allowance 24 dp plus 12 dp top padding, 16 dp side padding, 12 to 16 dp bottom padding. Row 1: Back icon button (48), title or brand block, balance chip (where shown). Optional row 2: account status (Rig picker only) or step indicator (Chooser and Truck, Trailer, Scale entry).
- **Rig picker variant:** logo (52, 14 dp radius, 2 dp white border), "RigCheck" (`top-bar-title`), tagline (`micro`), chip, then the account status row.
- **Compact:** while the keyboard is open the step indicator is dropped and bottom padding is 12.
- **Ids:** `picker.logo`, `picker.app_title`, `picker.tagline`, `*.back`, `*.title`, `picker.credit_chip`, `chooser.credit_chip`, `truck.credit_chip`.

## Icon button (48)
- 48 x 48 circle. Over the teal bar: `on-teal-wash` fill, `ink` icon (24). Elsewhere: transparent fill, `ink-muted` or `teal-deep` icon.
- States: pressed ripple; disabled 38% opacity (Back is disabled while a paid Scan is in flight; the Chooser overlay also blocks it); focus ring.
- Every one needs a content description: Back ("Back"), info ("What is stand-alone weight?"), row toggle ("Show note" or "Hide note").
- **Ids:** `*.back`, `paywall.back`, `truck.standalone_info`, `results.row_chevron`.

## Button, primary / secondary / ghost / destructive
- Height 56 (48 compact, 52 in dialogs). Pill (999). Padding 20 horizontal. Label `button` (or `button-compact`). Optional 22 dp icon, 8 dp gap. Full width by default; compact ones hug their label.
- **Primary:** `orange` fill, `ink` text, shadow `sm`. Pressed: `orange-deep` fill, white text. One primary per screen.
- **Secondary:** white fill, 1.5 dp `teal-deep` border, `teal-deep` text. Pressed: `tint-teal` fill.
- **Ghost:** no fill or border, `teal-deep` text. Pressed: `tint-teal` fill.
- **Destructive:** white fill, 1.5 dp `danger` border and text. Used only for Sign out.
- **Disabled (all kinds):** `disabled-fill`, `disabled-content` text, no border, no shadow.
- **Ids:** `picker.create_button`, `picker.history_button`, `picker.sign_out_button`, `picker.account_menu_cancel`, `chooser.*` cards (see Option card), `truck.next_button`, `truck.scan_standalone_button`, `trailer.next_button`, `scale.check_button`, `disclaimer.accept_button`, `results.start_another_button`, `results.garage_get_pro`, `history.upgrade_button`, `paywall.buy_button`, `paywall.restore_button`, `paywall.sign_out_button`, `paywall.retry_button`, `account.submit_button`, `account.toggle_mode`, `account.forgot_password`, `account.google_button`, `account.apple_button`, `account.not_now_button`, dialog buttons.

## Text field (and number field with unit)
- Label above (`label`, `ink`), then a 56 dp box: 1.5 dp `border-strong`, 8 dp radius, 16 dp side padding, value `body` 17 sp, unit hint ("lb") right-aligned in `ink-muted` 15 sp, placeholder in `ink-muted`. Optional help line under it (`caption`, `ink-muted`).
- **Focused:** 2 dp `teal-deep` border plus a 4 dp `tint-teal` ring, caret in `teal-deep`.
- **Error:** 2 dp `danger` border, message line in `danger-text` (`body-sm`, 500). Not colour alone: the message names the problem.
- **Disabled:** `disabled-fill` background at 70% opacity. No frame draws a disabled field.
- Numeric fields use the number keyboard. Hint numbers on the Scale screen carry an orange badge (22 dp, `ink` digit) in front of the label.
- **Ids:** all `*_field`, `picker.new_rig_input`, `account.email_field`, `account.password_field`.

## Option card (Scan Photo, Enter Manually)
- Min height 148, 24 dp radius, 1.5 dp border (`purple-deep` for Scan, `teal-deep` for Manual), `tint-purple` or `tint-teal` fill, shadow `sm`. 64 dp circular icon at the left (purple with white icon, teal with ink icon), title `title-lg`-ish 20/24 Outfit 700 with the badge beside it, description `body-md` in `ink-muted`.
- The two cards are the same size so Manual is a first-class path. A balance of 0 changes nothing visually (the Scan card still opens the Paywall as today).
- **Ids:** `chooser.scan_card`, `chooser.manual_card`.

## Rig card
- Follow-up round: the card is split in two by a 1 dp `border` divider (40 dp tall). The left part is the card body and the only tap target that starts a check. The right part is the delete bin (see "Icon button on a card"). The card has no padding of its own: the body carries 12 x 8 x 12 x 16, the bin a 4 dp right margin.
- Min height 84, 14 dp radius, 1 dp `border`, shadow `sm`, 12 x 16 padding. 52 dp avatar circle (tint fill, deep-colour initial, Outfit 800 22), nickname `title`, subtitle `body-sm` `ink-muted`, last checked `micro`, chevron at the right. Only the card body (left of the divider) taps; the delete bin is separate (follow-up round). Avatars cycle teal, purple, orange tints.
- **Ids:** `picker.rig_card`, `picker.rig_avatar`, `picker.rig_nickname`, `picker.rig_subtitle`, `picker.rig_last_checked`, `picker.rig_delete_button`.

## Credit chip
- 48 high, pill, white fill, shadow `sm`, 26 dp camera icon, label `chip`. Top right of the bar. Labels: "12 scans", "1 scan", "0 scans" (signed out), "…" only while a signed-in balance loads.
- Tap opens the Paywall route (shows Account when signed out). Content description: "Scan balance: N scans. Opens the Paywall".
- **Ids:** `picker.credit_chip`, `chooser.credit_chip`, `truck.credit_chip`.

## Account status row
- 48 high, 14 dp radius, `on-teal-wash` fill, 12 dp padding. 32 dp avatar (purple with white initial when signed in; white with person icon when signed out), two lines ("Signed in as" `micro`, email `body-sm` 700, ellipsised) and a chevron. Signed out: "Not signed in" and a "Sign in" label in `teal-deep`.
- Signed in opens the account sheet; signed out goes to the Account screen. Not available while a paid Scan is in flight.
- **Ids:** `picker.account_status`, `picker.account_avatar`.

## Bottom sheet
- 24 dp top corners, white, shadow `md`, 12 dp top padding, handle 40 x 4 in `border`, 16 dp side padding, 64 dp bottom padding (clears the 3-button bar). Scrim `ink` at 55%. Dismiss: scrim tap, Cancel, system Back.
- Account sheet: avatar (48) and email, then destructive "Sign out", then ghost "Cancel".
- **Ids:** `picker.account_menu`, `picker.account_menu_email`, `picker.sign_out_button`, `picker.account_menu_cancel`.

## Dialog
- 24 dp radius, 24 dp padding, width 364, shadow `md`, scrim 55%. Title `title-lg`, body `body` 16/24. Buttons stacked full width at 52: primary first, secondary second, ghost OK last.
- **Ids:** `photo_dialog.*`, `scan_error.*`, `late_scan.*`.

## Step indicator
- Three 32 dp circles (Truck, Trailer, Scale) joined by 2 dp lines at 35% `ink`. Current: `ink` fill, white digit, bold label. Done: `ink` fill. Upcoming: white fill, 2 dp `ink` border. Caption "Step n of 3" (`label`) above. The indicator counts only the three documents, as the old bar did.
- **Ids:** `chooser.step_bar`, `truck.step_bar`, `trailer.step_bar`, `scale.step_bar`.

## Verdict band
- 24 dp radius, shadow `md`, 20 dp padding. 64 dp translucent circle (white at 22%) holding a 36 dp icon (check-circle, x-circle or info-circle), headline `headline-verdict`, subline `body-md`, all white. Fill: `pine` (Safe to Tow), `danger` (Not Safe to Tow), `purple` (Partially Checked, Not Enough Information).
- **Ids:** `results.verdict`, `results.verdict_icon`.

## Breakdown row
- Row: 26 dp status icon, label `title-sm`-ish (Outfit 700 17), status badge, optional chevron (48 dp target, only when the row has a note). Under it a 10 dp rounded progress bar (track `#e7edf0`; fill `pine`, `danger` or `slate`) and a line with "A lb of B lb" (`body-sm`, `ink-muted`) at the left and the percentage (700) at the right. A fill over 100% is clamped at the bar's end.
- Expanded: the note appears under the row in a `surface-sunken` block (`body-sm`); 200 ms expand.
- Tones: pass (check-circle, "Within limit"), fail (x-circle, "Over limit", percentage in `danger-text`), not checked (info-circle, "Not checked", 0%).
- **Ids:** `results.row` and its parts (`results.row_icon`, `results.row_label`, `results.row_values`, `results.row_pct`, `results.row_bar`, `results.row_note`), `results.row_badge`, `results.row_chevron`, `results.breakdown_card`, `results.verdict_icon` (64 dp circle with a 36 dp icon).

## Badge
- Pill, 2 x 10 padding, `badge` text, optional 14 dp icon. Kinds: credit (`purple` / white), free (`pine` / white), within limit (`tint-green` / `pine`), over limit (`tint-red` / `danger-text`), partially checked (`tint-purple` / `purple-deep`), not checked (`surface-sunken` with 1 dp `border-strong` / `ink-muted`), plan (`tint-teal` / `teal-deep`).
- **Ids:** `chooser.scan_badge`, `chooser.manual_badge`, `results.row_badge`, `history.entry_verdict`, `paywall.plan_label`.

## Notice card
- 14 dp radius, 12 x 14 padding, 22 dp leading icon, text `body-sm` in `ink`, optional title `title-sm`. Tones: info (`surface-sunken`, 1 dp `border`), scan and warn (`tint-orange`, `orange-deep` icon), error (`tint-red`, `danger-text` icon).
- **Ids:** `truck.scan_notice`, `trailer.scan_notice`, `scale.scan_notice`, `results.garage_notice`, `results.history_notice`, `results.estimated_notice`, `history.limit_notice`, `account.info`, `paywall.load_error`, `paywall.no_packs`, `paywall.no_pro`.

## Reference card (pinned crop) and reference image
- Pinned under the top bar on Truck and Trailer: white card, 24 dp radius, shadow `md`, 12 dp padding. Caption row (search icon, "Tap a field to see its spot on the tag", and a plan-coloured badge naming the focused field), then a crop of the label showing three lines with the focused line outlined 2.5 dp in `orange` on `tint-orange`.
- Scale ticket: the image sits in the scroll with orange numbered badges (24 dp) drawn on it; legend pills below match the badges on the field labels.
- **Ids:** `truck.reference_image`, `truck.reference_hint`, `truck.reference_focus_badge`, `trailer.reference_image`, `trailer.reference_hint`, `trailer.reference_focus_badge`, `scale.reference_image`, `scale.legend`.
- The focused-field badge and the crop need a stored crop rectangle per field. That is new data (see `interaction-notes.md`).

## Panel (tinted block)
- 24 dp radius, 16 dp padding, 12 dp gaps. Purple tint (new-rig panel) or orange tint (stand-alone weight panel).
- **Ids:** `picker.new_rig_label` (inside), `truck.standalone_panel`.

## Offer card
- **Ids:** `paywall.offer_card`, `paywall.offer_title`, `paywall.offer_description`, `paywall.buy_button`.
- **States:** default; buttons disabled while a purchase is busy (frame `paywall__free_busy`).
- Free: one large card, `tint-purple` fill, 1.5 dp `purple-deep` border, 24 dp radius, title `offer-title`, description `body-md`, full-width primary button with the store price. Pro: one white row card per pack with the title, description and a compact primary price button; the price text comes from the store ("$4.99", "CA$12.99 one time"), so the button grows and never truncates.

## Slider
- **Ids:** `truck.pin_weight_slider`. The element is 48 dp tall. States: default (frame `truck_tag_entry__standalone_pin_weight`); pressed thumb grows to 32; hidden when the stand-alone field has a value.
- 4 dp track (`border`), `teal-deep` fill, 28 dp thumb with a 3 dp `teal-deep` ring and white centre, 48 dp touch height. 15 to 25%, default 20%.

## Progress bar, spinner, toast, empty state, divider
- **Progress bar:** 10 dp, fully rounded, drawn as one fill on one track with no gap between them and no dot at the track end (the old M3 bar has both; switch them off). Id `results.row_bar`. States: pass, fail, not checked (colours above).
- **Spinner:** 40 dp (48 in the Scan overlay), 4 dp ring in `border` with a `teal-deep` arc. Ids `paywall.loading`. Indeterminate; rotation is the essential animation.
- **Toast (snackbar):** `ink` fill, white `body-md`, 14 dp radius, 16 dp margins, sits above the pinned footer. Id `paywall.toast`. Shown 4 s, then fades.
- **Empty state:** dashed 2 dp `border-strong`, 24 dp radius, `surface-sunken` fill, 56 dp logo, title and text. Ids `picker.empty_state`, `history.empty`.
- **Divider:** 1 dp `border`. Id `account.divider`.

## Overlay (Scan in flight)
- White at 88% over the whole screen including the top bar, centred spinner and "Reading…". Blocks every tap, including Back and the account row.

## Icon button on a card (follow-up round)
- 48 x 48 dp circle, transparent fill, 24 dp `trash` glyph in `ink-muted`, 4 dp margin from the card's right edge, 1 dp `border` divider (40 dp tall) on its left. It is a sibling of the card body, not a child of its tap area, so the two hit areas and ripples never overlap.
- States: pressed (ripple confined to the bin, glyph turns `danger-text`), focused (focus ring around the 48 dp circle), disabled (38% opacity, while a delete runs). Not drawn at all when signed out.
- Content description "Delete <nickname>". Opens the Delete-Rig dialog; never starts a check.
- **Ids:** `picker.rig_delete_button`.

## Text link (Send feedback) (follow-up round)
- The ghost button at 48 dp with `button-compact` text, centred, `teal-deep`. Same component as every other ghost button; there is no separate link style. Orange text is not used for links because it fails contrast on white.
- Under it the no-mail line: `caption` (13/18) in `ink-muted`, centred, shown in place after the tap finds no mail app. The frame uses the beta address WTIAppDev@gmail.com; the app fills in its own constant.
- **Ids:** `picker.feedback_link`, `picker.feedback_no_mail`, `account.feedback_link`, `account.feedback_no_mail`.

## Dialog, destructive and crash prompt (follow-up round)
- Same dialog as above (24 dp radius, 24 dp padding, 364 dp wide, shadow `md`, scrim 55%, 52 dp stacked buttons).
- **Delete-Rig:** title (`title-lg`), body (`body`), optional error line (`body-sm`, 500, `danger-text`), then "Yes, delete" as the destructive button and "Cancel" as a ghost button. While the delete runs: "Deleting\u2026" and Cancel are drawn disabled; scrim tap and Back are ignored. Ids `delete_rig.dialog`, `delete_rig.title`, `delete_rig.body`, `delete_rig.error`, `delete_rig.confirm_button`, `delete_rig.cancel_button`.
- **Crash report:** the question is drawn as the heading (`title-lg`), the details as `body-sm` in `ink-muted`, "Send" is the primary button and "Not now" a ghost button. After the no-mail line only "OK" remains. Ids `crash_prompt.question`, `crash_prompt.details`, `crash_prompt.no_mail_app`, `crash_prompt.send_button`, `crash_prompt.dismiss_button`.

## Beta notice and Snackbar (follow-up round)
- **Beta notice:** the existing Notice card, tone "scan" (tint-orange, orange-deep info icon), body text bold. Full width at the top of the Paywall body. Beta builds only; a production build leaves it out. Id `paywall.beta_label`.
- **Snackbar:** replaces the system Toast on the Paywall. `ink` fill, white `body-md` text, 14 dp radius, 16 dp side margins, shadow `md`, 148 dp above the bottom edge so it clears the pinned Restore button, shown 4 s. No action button. Id `paywall.toast`, test tag `paywall_toast`.

## Splash and app icon
See `assets/` and the frames `splash__default` and `app_icon__launcher`.
