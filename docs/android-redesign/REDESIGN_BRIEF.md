# RigCheck Android: redesign brief

For: Claude Design. Written 2026-10-25. This brief replaces `ANDROID_DESIGN_BRIEF.md` for visual work; that older file still has the original (pre-teal) palette and fonts, so do not use its colours.

## 1. The ask in one paragraph

RigCheck is a weight-safety checker for RV and trailer towing: the user enters (or photographs) three documents, a truck compliance label, a trailer compliance label and a CAT Scale ticket, and gets an axle-by-axle pass/fail with an overall verdict. The Web app looks warm, branded and confident. The Android app has the same flow, the same words and the same colour tokens, but it looks like an unstyled Material 3 template: white screens, thin grey outlines, grey text fields, small default buttons, no logo, no colour blocks. **Re-draw every Android screen so it looks and feels like the same product as the Web app, using native-feeling mobile patterns.** This is a re-skin plus layout rework. It is not a change to features, flow or wording.

Live Web app to look at: https://rigcheck-web.pages.dev (works on a phone-width browser window; sign-in is not needed for the free flow).

## 2. What must not change

- **Behaviour and flow.** Same 9 routes, same order, same gates (see section 5). Add or move controls freely; do not add new features or remove functions (the only additions are the ones the owner asked for after the first phone test, listed in section 10). If a function really should go, say so in the map with a reason.
- **Words.** The app's tests find most controls by their exact on-screen text (about 410 lookups by text, about 70 by tag). Keep every string in `ui-inventory.json` exactly as written. If a string must change, list it in `copy-changes.md` (old text, new text, element id) instead of silently rewording. Disclaimer wording is legally reviewed: never change it.
- **The six result rows and the three verdict outcomes.** Their labels come from the maths: Front Axle (Steer), Rear Axle (Drive), Tow Vehicle Total (GVWR), Trailer Axle(s), Trailer Total (GVWR), Combined Rig Weight (only when GCWR was entered).
- **Fail must never rely on colour alone.** Today a failing row has a different icon shape (Cancel vs CheckCircle vs Info) plus red. Keep a non-colour cue.
- **Manual entry is the free, offline default.** Scanning is optional and costs a credit. The design should make manual entry feel like a first-class path, not a fallback.

## 3. Why it looks boring now (specific, so you can fix the causes)

| # | What the Android app does today | What Web does | Ask |
|---|---|---|---|
| 1 | No top bar, no logo, no tagline. Screen 1 shows the word "RigCheck" in plain text. | Sticky header with the Wandering Trails, Wagging Tails logo (52 px), "RigCheck" and "Weight safety, before you roll", nav pills, an orange "Start New Check" button | Give every screen a branded frame. Logo asset is `web/public/logo.png`. Decide what the header contains on each screen (title? back? balance chip?). |
| 2 | Almost everything is white with 1 dp grey outlines and no shadow or tint | Cards have soft shadows (`--shadow-sm/md`), 24 px radius, tinted blocks (teal, purple, orange) | Introduce surfaces with elevation and tinted fills; use the three accents as large areas, not just small badges |
| 3 | Verdict on Results is a thin outlined pill with coloured text | Solid colour hero band, 24 px radius, white 20 px icon in a translucent circle, big headline | The verdict should be the hero of Results. |
| 4 | Result rows show "X of Y" text, a percent in coloured text and a 6 dp bar | Each row has a pill Badge showing its status, a 10 px rounded bar, "actual" on the left and "rated" on the right | Richer row. Keep the tap-to-expand note, but show that a note exists (today there is no chevron or hint). |
| 5 | Text fields are the default M3 filled field (grey fill, underline); Account uses a different style again (outlined) | 1.5 px outlined inputs, 8 px radius, teal focus border | One field style everywhere, with a clear focus state, error state and unit hint ("lb"). |
| 6 | Buttons are default M3: 40 dp high, orange, Ink text | Pill buttons, Outfit 600, three variants (primary orange, secondary teal outline, ghost) | Define primary / secondary / ghost / destructive and sizes. Primary actions should be at least 52 dp high on phones. |
| 7 | Step progress is a "Step 2 of 3" caption and a purple 8 dp bar | Numbered circle pills "Rig, Truck Tag, Trailer Tag, Scale Ticket, Results" with check marks | Show where the user is in the journey. Android's bar counts only the three documents (Truck, Trailer, Scale); Web's pills also show Rig and Results. |
| 8 | The picker is a plain list and an input | Dashboard: hero, three coloured step cards (teal 1, purple 2, orange 3), recent checks, "Your Rigs" cards, dashed "New rig" card | The first screen is the app's front door. Make it feel like one. |
| 9 | Four headings (the app name and "Which rig?" on the Rig picker, the Chooser title, the History title) render in the system font, not Outfit, because the `headlineSmall` text style was never mapped (a code bug, which the re-skin fixes) | Outfit everywhere for headings | Specify all text styles explicitly (section 7.2). |
| 10 | Scale Ticket screen lists "1 Scale location 2 Steer ..." in orange text but the numbers are not drawn on the photo | n/a | Draw numbered badges on the ticket image that match the fields. |
| 11 | Truck and Trailer screens say "Hover a field to zoom in" (copied from Web; there is no hover on a phone). Zoom exists only as a hidden press-and-hold gesture. | Hover-to-zoom | Design a touch pattern that shows which spot on the label a focused field refers to. Options we considered: tap-and-hold, or a pinned lower-third crop that follows the focused field. You choose; tell us which. |
| 12 | Disclaimer and Results pages do not scroll as a whole; Paywall is not scrollable and has no back control (ticket #186 is fixing the system-bar overlap) | n/a | Every screen must scroll on a 360 x 640 phone and at 200% font. Primary action pinned at the bottom. |
| 13 | Orange text on white (scale legend, Account info message) | n/a | Orange (#ff7a1a) fails contrast as text on white. Use `orange-deep` (#b84a00) for text or put text on a fill. |
| 14 | Empty and error states are a plain sentence | Same | Design them (section 5 lists each state). |

## 4. Brand and tokens (the current truth)

Source files: `web/src/design-system/tokens.css` and `android/app/src/main/java/com/rigcheck/app/ui/theme/Color.kt` (already identical). Brand: "Wandering Trails, Wagging Tails", a friendly RV-and-dog household project; the tone is warm and plain-spoken, not clinical.

- **Accents:** orange `#ff7a1a` (primary, with Ink text, never white), teal `#12b5ae` (secondary, Ink text), purple `#7b3fe4` (tertiary, white text). Deep versions for text/links: orange-deep `#b84a00`, teal-deep `#087379`, purple-deep `#5b25b8`.
- **Support colours:** sunshine `#ffb627`, sky `#2f9bef`, pine `#3f6b35` (pass), slate `#576775`, blush `#e9a3a0`, danger `#b5473a` (fail).
- **Neutrals:** Ink `#16131f`, Ink-muted `#55506a`, surface `#ffffff`, surface-sunken `#f4f8f9`, border `#d5dee3`, border-strong `#738490`, tints teal `#e3f7f5`, purple `#f1ecff`, orange `#fff0e1`.
- **Type:** Outfit (headings, buttons; 600 to 800) and DM Sans (body; 400, 500, 700); Sacramento (script, for the wordmark only). On Android, fonts load at runtime from Google Fonts; they may be missing offline on first launch, so every style needs a sensible fallback. If you want a font bundled, say so.
- **Radius:** 8 (inputs), 14 (cards), 24 (panels, bands), pill 999 (buttons, badges). **Spacing:** 4, 8, 12, 16, 24, 32, 48, 64. **Shadows:** sm `0 1 3 rgba(22,19,31,.10)`, md `0 8 24 rgba(22,19,31,.12)`, lg as in tokens.css.
- You may propose changes to tokens, but list them in the tokens file under `proposed_changes` so Web can follow (the two apps share one brand).

## 5. Screens and states to design

Design each screen listed in `ui-inventory.json` (`screens[]`), at 412 x 892 dp, and for every state in that screen's `states` list. 13 screens (10 full screens, 3 dialogs). Short summary:

1. **Rig picker** (start screen): saved rigs, new rig by nickname, History entry, Scan balance chip.
2. **Chooser** (x3: Truck, Trailer, Scale): Scan Photo (1 credit, needs sign-in and a balance) vs Enter Manually (free). Plus the photo-source dialog and a Scan-in-flight overlay.
3. **Truck tag entry**, 4. **Trailer tag entry**, 5. **Scale ticket entry**: instruction text, reference photo of the real label, fields, optional-field hints, notices, Next button.
6. **Disclaimer**: blocking, once per app launch.
7. **Results**: verdict, notices (estimate, Garage, History), breakdown, Start another check.
8. **History**: past checks; read-only.
9. **Paywall** (signed in) and 10. **Account** (sign-in/create; shown in the same route while signed out).
11. Dialogs: **Scan failed** (message + up to 2 next-step buttons + OK), **A Scan finished late**.

Navigation today: the system Back button only. There is no app bar and no bottom bar. You may introduce a top app bar with back, a bottom bar, or neither. Say which, and why. Constraint: during a paid Scan the user must not be able to leave or restart the check (the Chooser overlay blocks all taps).

## 6. What you must hand back

Put these in one folder, named as below, so they can be coded and tested without a meeting.

1. **`ui-redesign-map.json`**: the `ui-inventory.json` I gave you, with `redesign` filled in for **every** element id (status, new screen, region, order, width, height, style, new test tag, notes) and any brand-new elements in `added_elements[]`. Allowed statuses are in `meta.status_values`. A CSV copy (`ui-inventory.csv`, columns starting `REDESIGN_`) is equivalent if that is easier; deliver one of the two, not both edited differently. Keep ids unchanged. Never reuse an id for a different function.
2. **One annotated PNG per screen per state** (name: `<screen>__<state>.png`), 412 x 892 dp at 2x, with the element ids from the map written next to each element (small numbered tags with a legend is fine). This is the build reference.
3. **`tokens.json`**: colours (named and hex), text styles (family, weight, size in sp, line height in sp, letter spacing), spacing scale, radii, elevations/shadows, motion durations and easing, opacity values, and a **mapping to Material 3 theme slots** (primary, onPrimary, secondary, tertiary, surface, surfaceVariant, outline, error, plus any custom colours Compose needs beyond M3).
4. **`components.md`**: one entry per reusable component (header, primary/secondary/ghost button, text field and its states, number field with unit, option card, rig card, credit chip, step indicator, verdict band, breakdown row, notice card, badge, progress bar, bottom-sheet or dialog, empty state, toast/snackbar). For each: anatomy, sizes in dp (min touch target 48 dp), colours by token, every state (default, pressed, focused, disabled, error), and which element ids use it.
5. **`copy-changes.md`**: any text you want changed (old, new, id). Default is none.
6. **Assets**: logo as SVG (plus a monochrome version if used on colour), icon list (name and set; Material Symbols preferred, Material icons are what the app uses today), any illustration as SVG or vector-ready PNG at 4x, and 3 annotated versions of the reference photos if you redraw them (the originals are in `android/app/src/main/res/drawable/ref_*.jpg`; the truck and trailer photos have a redacted VIN block, keep it).
7. **Resize rules**: how each screen behaves at 360 x 640, 412 x 892, 600 dp wide (tablet/foldable), font scale 1.3 and 2.0, and with the keyboard open. State what scrolls and what is pinned.
8. **Interaction notes**: only where it is not obvious (the reference-image touch pattern, the expand-a-row behaviour, any animation). Say which animation is essential and which is optional.

## 7. Constraints from the build

### 7.1 Platform
- Native Kotlin and Jetpack Compose with Material 3. Customising M3 (shapes, colours, typography, custom components) is fine; avoid anything that needs a third-party UI library or a custom renderer.
- Light theme only today. **Decision needed from the owner: is a dark theme in scope?** If you design one, provide it as separate token values and frames, clearly marked optional.
- The app is edge-to-edge (content draws under the status and navigation bars). Test frames must account for status bar (about 24 dp) and either the gesture bar or the 3-button bar (48 dp). The owner's phone uses 3-button navigation, which already hid a button once.
- Camera: the app opens the system camera and the system photo picker. It does not have its own camera screen. Do not design a viewfinder.
- Prices on the Paywall come from the store as a formatted string and are not known at design time. Design with a long and a short price ("$4.99", "CA$12.99 one time").
- Plan names are **Free** and **Pro**. Scan credits are called **Scans** in the interface ("12 scans"). A Free account is never shown scan packs; a Pro account is never shown the Pro offer.

### 7.2 Text
- Please give all text styles as a table of name, family, weight, sp, line height, letter spacing, case, colour token; do not rely on Material defaults. Anything you leave unspecified will render in Roboto.
- Numbers are weights in pounds with thousands separators (e.g. "9,600 lb"). Provide a tabular-number or a right-aligned treatment for the Results values if you want columns to line up.

### 7.3 Accessibility
- Touch targets at least 48 x 48 dp (the stand-alone "i" icon is 24 dp today and needs padding).
- Text contrast AA at least. Orange `#ff7a1a` and teal `#12b5ae` need Ink text on top, never white. Do not put orange text on white.
- Pass, fail and not-checked must be distinguishable without colour (icon shape and label).
- Every icon-only control needs a content description; list it in the map `notes`.

## 8. How the result will be built and tested (so you can design for it)

1. A baseline of today's screens (screenshots and measured bounds from the emulator) is to be captured first. It is the "before" half of the map, and it replaces the estimated sizes in the inventory.
2. Every element in the map gets a stable `testTag` equal to `new_test_tag` before the visuals change, and the existing tests move onto tags. That is why ids must not change.
3. The theme, tokens and shared components are built first, then each screen is re-skinned one at a time. Each screen ticket compares the running app to your annotated PNG for the same state.
4. Screens that have many states in the app (Paywall, Results, Chooser) are driven by test fixtures, so every state in `states` must be a state the app can actually reach. Tell us if you have designed a state not on the list.
5. If a design needs a new function (for example, a delete-rig control, a filter, a dark theme toggle), it will be raised as its own ticket after the re-skin. Mark such elements `added_elements[].needs_new_function = true`.

## 9. Where things are

- `docs/android-redesign/ui-inventory.json` / `.csv`: the inventory (150 elements, 13 screens) and the map to fill in.
- Current Android UI source: `android/app/src/main/java/com/rigcheck/app/ui/screens/*.kt`, `.../ui/components/*.kt`, `.../ui/theme/*.kt`.
- Web reference UI source: `web/src/screens/*.tsx`, `web/src/wizard/*.tsx`, `web/src/components/*.tsx`, `web/src/design-system/*`.
- Glossary of the app's own words (Rig, Garage, History, Plan, Scan, Scan Credit, Paywall, Check): `android/CONTEXT.md`.

## 10. Owner feedback after the first run on a phone (2026-10-27)

The owner ran the app on a real phone (Samsung SM-G996U, 3-button navigation) and asked for the following. They add to this brief. They need no new logic: sign-out and the scan balance already exist, and the splash and icon are branding.

1. **Splash screen at load.** A branded screen while the app starts (logo on the brand colour, an optional short animation). It will be built with Android's platform splash mechanism, so give the logo as a vector sized for that, the background colour and, if any, the animation.
2. **App icon.** The launcher icon is a placeholder today. Design an adaptive icon: foreground, background, and a single-colour version for themed icons. Hand back vectors, plus a 512 px version for a future store listing.
3. **Show who is signed in.** The user must be able to see whether they are signed in, and as which account (the email), without opening the Paywall. At least on the Rig picker; ideally in the shared header on every screen that has one. When signed out it should say so and offer Sign in (the same route as today).
4. **A way to sign out.** Today "Sign out" exists only on the Paywall. Make it reachable from the account status in item 3 in one or two taps (a menu or a sheet). It must not be possible during a paid Scan (the same rule as the rest of the app).
5. **The scan balance stays top right, and bigger.** Keep the scan balance chip in the top right on the screens that show it. The camera icon in it is small (16 dp today) and so is the chip; make both larger, with a touch target of at least 48 dp. (The owner wrote "Scan icons top right": keep the chip where it is, and say in the map if you read it differently.)
6. **Signed out shows "0 scans".** Before sign-in the chip shows "...", which the owner read as blank. It should say "0 scans". This is a wording change: list it in `copy-changes.md` (old: the "..." shown when signed out; new: "0 scans"). The "..." stays only for a signed-in account whose balance is still loading.
