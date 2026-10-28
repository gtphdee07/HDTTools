# Interaction notes

Only where the behaviour is not obvious from the frames.

## Navigation: what I chose and why
A top app bar with a Back icon button on every screen except the Rig picker, the Disclaimer and the Splash. No bottom bar. The flow is a wizard, not a set of destinations, so a bottom bar would imply peers that do not exist. The system Back button keeps working everywhere it works today. Back (both kinds) is blocked while a paid Scan is in flight, as the Chooser overlay already requires.

## Reference image on Truck and Trailer (the choice asked for in the brief)
A pinned crop that follows the focused field. The old hover and the press-and-hold gesture are both gone.
- The reference card sits under the top bar and does not scroll away.
- When a field takes focus the card shows three lines of the label centred on that field's line, with that line outlined in orange, and a badge naming the field ("GVWR", "Front GAWR", "GAWR per axle", "UVW").
- With no field focused it shows the first three lines and the hint "Tap a field to see its spot on the tag".
- No gesture is needed anywhere. (A tap on the card to open the full photo with pinch zoom would be a nice extra, but it is a new function: if wanted, raise it as its own ticket after the re-skin.)
- Why not tap-and-hold: it is hidden, and it hides the thing you are trying to type next to. A pinned card needs no gesture and stays visible while the keyboard is open.
- In the frames the crop is a placeholder drawn from text. In the app, crop the real photo (keep the redacted VIN block). Each field needs a crop rectangle stored as fractions of the photo. **That is new data and a new function**, so the two focus badges are flagged `needs_new_function` in the map; if the owner prefers, the card can show the whole label with no highlight until a follow-up ticket adds the rectangles.

## Scale ticket
No pinned card. The ticket image carries numbered orange badges (1 to 5). The same numbers sit on the field labels and in the legend pills, so the match is by number, not by hover.

## Account status and sign out (owner feedback items 3 and 4)
- Rig picker top bar: a 48 dp row shows "Signed in as `<email>`" or "Not signed in".
- Signed in: tap opens the account bottom sheet (email, Sign out, Cancel). Sign out is two taps from the Rig picker.
- Signed out: tap goes to the Account screen (the Paywall route, signed-out branch), as the chip does today.
- Not available during a paid Scan. The Chooser and Truck screens have no account row, so this only matters if a later design adds it there.
- Sign out asks for no confirmation: it is easy to undo by signing in.

## Scan balance chip (item 5 and 6)
Stays top right on Rig picker, Chooser and Truck. 48 dp high, 26 dp icon. "0 scans" when signed out. "…" only while a signed-in balance loads. I read "Scan icons top right" as this chip; if the owner meant something else, only the map notes change.

## Results rows
- A row with a note shows a chevron; tapping the row or the chevron expands the note (200 ms, standard easing, essential). Rows without a note show no chevron and do not respond to taps.
- A failing row is drawn expanded in the `results__not_safe_row_expanded` frame to show the pattern. In the app, rows start collapsed. A failing row starts expanded only if the team wants that; it is not required.
- The Results page scrolls as a whole; the footer button stays.

## Scan in flight
Spinner and "Reading…" over a white wash. Nothing underneath is tappable: Back, the chip, the account row and the cards are all blocked. The wash fades in over 100 ms (optional).

## Disclaimer
Blocking, once per app launch, as today. The page scrolls; the button never leaves the screen. At large font sizes the text scrolls and the button stays pinned (frame `disclaimer__large_font`).

## Splash and icon (owner feedback items 1 and 2)
- Splash: Android 12 splash screen API. Background `teal`, icon from `assets/splash_icon.svg` on a sky-gradient disc. The optional fade-in is 300 ms and can be left out. The branding line at the bottom is optional.
- Icon: adaptive. Foreground `assets/ic_launcher_foreground.svg`, background `assets/ic_launcher_background.svg`, themed `assets/ic_launcher_monochrome.svg`. `assets/ic_launcher_512.png` is the future store listing icon.

## Animations
Essential: the Scan spinner and the row note expand. Everything else is optional (see `tokens.json` motion).
