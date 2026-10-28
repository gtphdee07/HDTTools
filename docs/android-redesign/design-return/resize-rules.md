# Resize rules

Reference frame: 412 x 892 dp, edge-to-edge. Status bar allowance 24 dp. Bottom allowance 48 dp (3-button navigation) or about 24 dp (gesture bar); the frames use 48. Side margin 16 dp. The frames are drawn at 412 x 892; the rules below say what changes elsewhere. They were derived from the layout and not yet checked on a device or emulator (see README, open items).

## Layout skeleton, every screen
- **Pinned top:** top app bar (and the reference card on Truck and Trailer). Does not scroll.
- **Scrolls:** everything in the body. The whole body scrolls as one column, including the Results breakdown (the breakdown card no longer scrolls inside itself) and the Disclaimer text.
- **Pinned bottom:** the primary action (Next, Check Weights, Start another check, I Understand, Continue, Restore purchase, Not now) sits in a footer with a top shadow. The footer clears the navigation bar with 64 dp of bottom padding (12 + 48 + 4).
- A soft 28 dp white fade at the bottom of the scrolling area hints that there is more below. It is drawn only while content is cut off.

## 360 x 640 (small phone)
- Header: the step indicator keeps its three circles; labels stay visible. Title may truncate with an ellipsis; the chip never shrinks below 48.
- Rig picker: the account row stays; the heading row wraps the History button under the subheading if the heading and button do not fit (button goes full width).
- Option cards: icon circle shrinks to 56, card min height 132.
- Entry screens: header 120 + reference card about 150 + footer 76 leaves about 290 dp of form. That is intended; the form scrolls. The reference card may collapse to its caption row and one label line below 700 dp of height.
- Results: the verdict band stacks its icon above the text under 380 dp wide. Rows are unchanged.
- Dialogs: width becomes screen width minus 32.

## 600 dp wide (tablet, foldable)
- Content is centred in a column of at most 560 dp. The top bar stays full width; its content aligns to the same column. The footer's button is 560 dp wide and centred.
- Rig picker, History and Paywall packs may use two columns of cards above 600 dp.
- Entry screens: the reference card moves beside the form (left column 280, right column 280) instead of above it.
- Dialogs and the account sheet are 400 dp wide and centred.

## Font scale 1.3
- All text uses sp and scales. Text wraps; nothing is clipped.
- Buttons grow in height (min 56). Chip grows in width, never wraps its label.
- Step indicator labels stay one line.
- Result row labels wrap to two lines; the badge stays at the right of the first line.

## Font scale 2.0
- Top bar: title wraps to two lines at most. Chip label stays one line; if the bar cannot fit the title and chip, the chip moves under the title (full row).
- Step indicator: labels hide, digits stay; the caption "Step n of 3" is kept.
- Option cards: icon circle moves above the text (column).
- Results rows: label on its own line, badge on the next line.
- Disclaimer: see the frame `disclaimer__large_font`: the text scrolls, the button stays pinned.
- Reference card on Truck and Trailer: collapses to one label line plus the caption.

## Keyboard open
- Top bar drops the step indicator and shrinks to 12 dp bottom padding. The reference card stays and shows three lines around the focused field.
- The form scrolls so the focused field sits fully above the keyboard. The footer button stays visible above the keyboard.
- Rig picker: the new-rig panel scrolls into view; Create is enabled once the nickname is not blank.
- Account: the footer ("Not now") stays above the keyboard.

## What scrolls and what is pinned, by screen
| Screen | Pinned top | Scrolls | Pinned bottom |
|---|---|---|---|
| Rig picker | top bar with account row | heading, rig cards, new-rig panel | none |
| Chooser | top bar with step indicator | prompt, two cards, note | none |
| Truck and Trailer entry | top bar, reference card | instructions, fields, panel | Next |
| Scale ticket entry | top bar | instructions, image, legend, fields | Check Weights |
| Disclaimer | none | icon, title, both paragraphs | I Understand, Continue |
| Results | top bar | verdict, notices, breakdown, footer note | Start another check |
| History | top bar | subtitle, notices, entries | none |
| Paywall | top bar | account line, plan, explainer, offers | Restore purchase |
| Account | top bar | reason, fields, buttons | Not now |
