# Design return: Android re-skin (ticket #190)

Hand-back of the Claude Design round, 2026-10-27, for epic #187. Light theme only. Same flow, same 9 routes, same words except the changes in `copy-changes.md`. A top app bar with Back was added; there is no bottom bar.

Editable design canvas (private to the owner): https://claude.ai/artifact/VQMbZMRBqnbdHxiyVhXPob

## What is here (section 6 of the brief)

| # | Deliverable | File |
|---|---|---|
| 1 | Redesign map: the inventory with `redesign` filled for every one of the 150 ids, plus 26 `added_elements` | [ui-redesign-map.json](ui-redesign-map.json) |
| 2 | Annotated frames, 412 x 892 dp at 2x (824 x 1784 px), one per screen per state. The one exception is `app_icon__launcher.png`, a 900 x 620 dp sheet of icon masks and layers (not a screen), with no element tags | [annotated/](annotated/), legends in [annotation-legends.json](annotation-legends.json) |
| 3 | Tokens, text styles, Material 3 mapping | [tokens.json](tokens.json) |
| 4 | Components | [components.md](components.md) |
| 5 | Copy changes | [copy-changes.md](copy-changes.md) |
| 6 | Assets: launcher icon, splash icon, mark, 512 px store icon, icon names | [assets/](assets/README.md) |
| 7 | Resize rules | [resize-rules.md](resize-rules.md) |
| 8 | Interaction notes | [interaction-notes.md](interaction-notes.md) |

## Follow-up round: 17 controls (added after the first hand-back)

The first round had 150 elements; #188 raised the inventory to 167. This round covers the 17 added controls (the delete bin and its dialog, the Send feedback links, the Paywall beta label and the crash-report dialog). Brief: [../DESIGN_FOLLOWUP_BRIEF.md](../DESIGN_FOLLOWUP_BRIEF.md).

- **Map:** [ui-redesign-map-followup.json](ui-redesign-map-followup.json). All 17 ids have a `redesign` block, `new_test_tag` equals the inventory's `test_tag_new`. It also lists the frames that are new or re-issued, one `revised_elements` entry (`paywall.toast`, now a Snackbar with the tag `paywall_toast`), and one `drift_notes` item (`paywall.back` is a TextButton with the word "Back" in the updated inventory).
- **Frames:** 7 new (`rig_picker__feedback_no_mail`, `account__feedback_no_mail`, `delete_rig_dialog__question`, `__deleting`, `__delete_failed`, `crash_report_dialog__question`, `__no_email_app`) and 20 re-issued, because the bin, the feedback link or the beta label now shows in them (every Rig picker frame with Rig cards or the empty state, every Account frame except `keyboard_open`, all nine Paywall frames, and the backdrop of `late_scan_dialog__credit_used`). 43 first-round frames are byte-identical. Total 70 frames.
- **Beta only:** all nine Paywall frames are drawn as a beta build shows them. A production build leaves out `paywall.beta_label` and everything below it moves up by 80 dp.
- **Answers to the two questions:** the bin sits at the right end of the card behind a divider and has its own hit area; the Paywall toast becomes a Snackbar (same id). Both are in the follow-up map.
- **Names:** `new_screen` and frame names use the inventory's `screen` values (`delete_rig_dialog`, `crash_report_dialog`).
- The first map is not edited. Its `new_order` values for the Rig picker, Account and Paywall elements count from before these controls existed; the frames are the reference where they differ.
- No `needs_new_function`: everything drawn already exists in the app.

## Reading the map
- Ids are unchanged and none was reused. Every inventory id has a status. The value is the first word of `meta.status_values`: `kept`, `restyled`, `moved`, `merged`, `split`, `removed`, `replaced`. Added elements carry `added`.
- Totals: 125 restyled, 16 moved, 8 replaced, 1 removed (`picker.header_divider`, replaced by the top bar's rounded edge), 0 kept, 0 merged, 0 split.
- `new_region`, `new_width`, `new_height` and `new_order` are **measured from the frames**, not estimated. `new_order` is the reading order in the frame named in `notes`. A `new_width` of `fill` means the element spans the content column (16 dp side margins). The `today` values are still the inventory's estimates: the baseline frames from #189 did not exist yet (owner decision 3 was "wait for #189", and the design was started from the inventory and the live Web app instead).
- `new_test_tag` equals `test_tag_new` for every existing id; added elements use their id with dots as underscores.
- Two added elements have `needs_new_function = true`: `truck.reference_focus_badge` and `trailer.reference_focus_badge`. The pinned reference crop needs a stored crop rectangle per field (fractions of the photo), which is new data. Under the brief's rule it should become its own ticket after the re-skin; until then the card can show the whole label with no highlight. Everything else added has an existing function behind it (sign-out and the balance already exist).
- A repeated element (rig card, history entry, result row, field) carries its ids on the first instance in the frame only.

## Frames
Name: `<screen>__<state>.png`, screens as in the inventory. Tags are numbered in reading order and the numbers map to ids in `annotation-legends.json`. Where content is longer than the screen, the frame is scrolled (a `scroll_to` state) and a neighbouring frame shows the top. The frame holds the real pinned header and footer. 63 frames:

| Screen | Frames |
|---|---|
| rig_picker | in, account_menu, signed_out_empty, new_rig_typing |
| chooser | truck, trailer, scale, scan_in_flight, balance_loading |
| truck_tag_entry | blank, filled, scan_notice, gcwr_warning, standalone_blank, standalone_pin_weight, standalone_info, standalone_filled, standalone_scan_in_flight, keyboard_open |
| trailer_tag_entry | blank, filled, scan_notice, keyboard_open |
| scale_ticket_entry | blank, filled, scan_notice, keyboard_open |
| disclaimer | default, large_font |
| results | safe, not_safe_row_expanded, partially_checked, not_enough_information, notices, notices_scrolled, safe_scrolled_to_end |
| history | few_entries, limit_notice, empty |
| paywall | free_pro_offer, free_busy, free_no_pro, pro_packs, pro_no_packs, pro_bought_waiting, loading, load_error, plan_unknown |
| account | sign_in, create_account, error, info_reset_sent, busy, keyboard_open, apple_enabled_future |
| photo_source_dialog, scan_error_dialog, late_scan_dialog | default; message_only, one_next_step, two_next_steps, long_message; credit_used |
| splash, app_icon | default; launcher |

States in the inventory that are not drawn as their own frame, and why:
- Balance 0, 1, many: only the chip text differs (see `tokens.json` and `components.md`).
- 5 or more rigs, many history entries: the list scrolls; `few_entries` shows the card pattern.
- Signed in versus signed out garage or history: same look.
- Trailer axle count blank versus filled: `blank` and `filled` show it. History "all four verdict labels": `few_entries` shows all four.
- Paywall "3-button bar overlapping Restore": every Paywall frame has Restore in the pinned footer with 64 dp bottom padding, which fixes it.
- Truck "image zoom active": replaced by the pinned crop; `filled` and `keyboard_open` show it following a field.
- Scan error dialog on the Truck screen: same dialog as on the Chooser.
- Results with and without the Combined row: `safe` shows six rows; `partially_checked` and `not_enough_information` show five.
- "A Scan finished late", no credit used: the code has only the credit-used message, so there is one frame.
- Small phone (360 x 640): described in `resize-rules.md`, not drawn.

## Decisions recorded for this round
1. Dark theme: no, light only.
2. Navigation: re-skin plus layout rework, same flow and screens. A top app bar was added.
3. Timing: wait for #189 (answered on the ticket on 2026-10-27). That did not happen before this round; see below.

## Open items for the owner
- **Decide on the crop rectangles.** See the `needs_new_function` note above: keep the pinned crop (new data, own ticket) or fall back to the whole label.
- **The Truck screen now has a scan balance chip** (`truck.credit_chip`), because it has a paid stand-alone Scan button. The brief said to keep the chip "on the screens that show it"; this is one more screen. Say if you would rather not.
- **Approve or replace the mark.** `assets/` holds a simplified geometric redraw of the logo, not the painted logo itself.
- **Fonts.** Bundle Outfit and DM Sans (about 300 KB) or keep runtime loading with a fallback. See `tokens.json`.
- **Placeholders in the frames:** the label crop on Truck and Trailer, the ticket image on Scale, and the Google glyph on Account. Production uses the real photos (keep the redacted VIN block) and Google's official asset.
- **Copy.** Review `copy-changes.md`: four changed strings and a few new ones, including the empty Rig picker text.
- **Not checked on a device.** Sizes, scroll behaviour and the resize rules come from the layout and the rendered frames, not from an emulator. #189's baseline capture should confirm them.
- **The `today` sizes in the map are still estimates** for the same reason.
- **#191's validator** is the check for map completeness; it did not exist when this was filed. A check was run here by script: every inventory id is present, has a status, and none was renamed.
