# Copy changes

Default is no change. Every string in `ui-inventory.json` is kept exactly as written, including the disclaimer wording and the em dashes in the Chooser card descriptions. The list below is the only departure. Each changed string needs its tests updated in the same ticket as the screen.

## Changed strings

| Element id | Old text | New text | Why |
|---|---|---|---|
| `picker.credit_chip` | "…" shown while the balance is not loaded, including when signed out | "0 scans" when signed out. "…" only for a signed-in account whose balance is still loading. | Owner feedback of 2026-10-27, item 6. |
| `chooser.credit_chip` | same | same rule | Same chip, same rule. |
| `truck.reference_hint` | "Hover a field to zoom in on its spot on the tag" | "Tap a field to see its spot on the tag" | A phone has no hover. |
| `trailer.reference_hint` | "Hover a field to zoom in on its spot on the tag" | "Tap a field to see its spot on the tag" | Same. |

## New strings (new elements, no existing text changes)

These belong to `added_elements[]` in the map. None of them replaces an existing string.

| Element id | Text | Notes |
|---|---|---|
| `picker.tagline` | Weight safety, before you roll | Same words as Web. |
| `picker.account_status` | Signed in as `<email>` / Not signed in / Sign in | Owner feedback item 3. |
| `picker.sign_out_button` | Sign out | The word already exists on the Paywall. |
| `picker.account_menu_cancel` | Cancel | |
| `picker.empty_state` | No saved rigs yet / Finish a check and your rig shows up here. Manual entry is free. | New. Replace with the owner's wording if preferred. |
| `results.row_badge` | Within limit / Over limit / Not checked | Says the row status in words, so a fail does not rely on colour. |
| `chooser.loading_text` | Reading… | Reuses the existing "Reading…" string. |
| `splash.branding` | RigCheck / Weight safety, before you roll | Optional. |
| `truck.reference_focus_badge` | GVWR / Front GAWR / Rear GAWR | The name of the field the pinned card shows (#199). Named in `interaction-notes.md`, "Reference image on Truck and Trailer"; "Rear GAWR" is the label's own wording, as in the Truck field's name. |
| `trailer.reference_focus_badge` | GVWR / GAWR per axle / UVW | Same, for the Trailer card (#199). |

## Content descriptions (accessibility labels)

Icon-only controls need these. They are not visible text.

| Control | Content description |
|---|---|
| Back buttons (`*.back`, `paywall.back`) | Back |
| `truck.standalone_info` | What is stand-alone weight? |
| `truck.pin_weight_slider` | Pin weight, percent of trailer weight |
| `truck.reference_image`, `trailer.reference_image` | "Truck compliance label" / "Trailer compliance label"; with a field focused, "Truck compliance label, Front GAWR line outlined" (the badge's name), so a screen reader is told which field the card shows (#199). The badge is also a polite live region. |
| `results.row_chevron` | Show note / Hide note |
| `picker.credit_chip` and the other chips | Scan balance: N scans. Opens the Paywall |
| `picker.account_status` | Account: signed in as `<email>`. Opens account menu / Not signed in. Sign in |
| `picker.logo` and decorative icons | (empty) |

## Sample text in the frames that is not app copy

These appear in the frames only to make them look real. They come from the store, the user or the maths, not from the app:

- Store offer titles, descriptions and prices on the Paywall ("RigCheck Pro", "10 Scans", "$24.99", "CA$12.99 one time").
- Rig names, emails, weights and percentages.
- The plan limits in the History notice ("last 10 checks", "last 100"). The real numbers come from the plan configuration.
- The Account error sentence.
- The row notes are the real notes from `breakdown.py`.

## Follow-up round (17 controls)

No string was changed. The new frames use the inventory's text exactly, including `Delete "<nickname>"?`, "Yes, delete", "Deleting…", "Send feedback", the no-mail line, the crash-report question and details, and the Paywall beta line. These strings are not yet reviewed by the owner (see `DESIGN_FOLLOWUP_BRIEF.md`).

The only text in the new frames that is not from the inventory is sample data: the feedback address in the no-mail lines is the beta address `WTIAppDev@gmail.com` from `docs/BETA_PLAN.md`, and the app shows its own constant. New content descriptions: "Delete <nickname>" (already in the inventory).
