# Android redesign kit (owner's cover sheet)

Prepared 2026-10-25 on `MPSkills`. Nothing here changes the app; it is the material for a Claude Design round and for coding the result afterwards.

| File | What it is | Who uses it |
|---|---|---|
| [REDESIGN_BRIEF.md](REDESIGN_BRIEF.md) | The brief for Claude Design: what to change, what must not, why it looks flat now, brand tokens, what to hand back, build constraints | Claude Design (paste or attach) |
| [ui-inventory.json](ui-inventory.json) | 167 elements on 15 screens (updated 2026-10-27, #188): name, function, exact text, today's region/order/size/style, existing and proposed test tag, which test files mention it, and empty `redesign` fields. Also each screen's list of states to draw | Claude Design fills it in; the build and the tests read it |
| [ui-inventory.csv](ui-inventory.csv) | The same rows as a spreadsheet (UTF-8 with BOM, opens in Excel). Last 10 columns, `REDESIGN_*`, are for the designer | Same, if a table is easier |

The JSON is the source of truth, and the CSV is generated from it: edit the JSON, then run `uv run scripts/ui_inventory.py` (`--check` fails if the CSV, the app's `UiTags` object or the screens disagree with the JSON). Edits made in the CSV are overwritten.

## Before you send it

1. **Decide the scope.** The brief says "re-skin plus layout rework, no new features". If you also want a different navigation model (bottom bar, a Dashboard-style home like Web), say so in the brief's section 5; otherwise the designer will stay close to today's flow.
2. **Dark theme: in or out?** The brief asks. Today the app is light only; dark roughly doubles the design and test work.
3. **Timing against Alpha.** Alpha testers are on the current UI, tickets #186 (system bars, Paywall scroll, Back) and #182/#184 are still in lane A, and the re-skin touches nearly every Android UI test. I would run the design now (it costs no Android time) and start building after #186 and the Alpha fixes have merged. Your call.
4. **Attach to the Design session:** the three files above, `web/public/logo.png`, `web/src/design-system/tokens.css`, the three reference photos in `android/app/src/main/res/drawable/ref_*.jpg`, and the live Web URL (https://rigcheck-web.pages.dev). Do not attach `ANDROID_DESIGN_BRIEF.md`: its palette and fonts are the old ones.

## What would make the design easier to code and test (not yet done)

These need the emulator, so they belong in lane A and I have not started them:

- **Baseline screenshots plus measured bounds of every screen and state** (a small instrumented test that opens each state from the inventory and writes a PNG and the on-screen position and size of every tagged element). It replaces the estimated sizes in the inventory with real ones, gives the designer true "before" frames to annotate, and the same test is rerun after the re-skin to produce the "after" half of the map automatically.
- **Done in #188 (T0):** a test tag on every inventory element (`test_tag_new` in the inventory, `UiTags` in the app), with the existing tests moved from text lookups to tags; `tests_referencing` now counts the test files that use each tag. The note below is how it was before.
  Before it, 19 elements had a tag and about 410 test lookups went by visible text, which is why the brief freezes the copy; now the re-skin can be a pure visual change that the existing tests already guard.

Filed on 2026-10-25 as epic #187 with children #188 to #197 (T0 = #188, T1 = #189, owner step D = #190, T2 = #191, T3a to T3e = #192 to #196, T4 = #197). Outline: (T0) test tags for every inventory element and tests moved onto them; (T1) baseline capture test; (T2) theme, tokens and shared components from the designer's `tokens.json` and `components.md`; (T3) one ticket per screen group (Rig picker and Chooser; the three entry screens; Disclaimer and Results; History; Paywall and Account and dialogs); (T4) final pass against the annotated PNGs, accessibility checks (48 dp targets, contrast, font scale 2.0, 360 x 640) and 3-button navigation.

## When the map comes back

1. Check every id has `redesign.status`, and that nothing was reused or renamed. (I can script this.)
2. Diff `copy-changes.md`; each changed string needs its tests updated in the same ticket.
3. Elements with `needs_new_function` become their own tickets and wait until after the production release unless you decide otherwise (the `enhancement`/`future` rule).
4. Each screen ticket then uses the map to find which tests reference a moved or changed element (`tests_referencing`), updates only those, and compares the running app to the annotated PNG for each state.

## Things I noticed while inventorying (all in the brief; fix in the re-skin or earlier)

- Four headings use the system font because `headlineSmall` is not mapped in `Type.kt`.
- Truck and Trailer screens say "Hover a field to zoom in", but there is no hover on a phone.
- The Scale Ticket legend ("1 Scale location ...") has no matching numbers on the photo, and is orange text on white.
- Disclaimer and Results do not scroll as a page; the Paywall has no Back control.
- The stand-alone-weight "i" icon is 24 dp, below the 48 dp touch-target minimum.
- Account uses outlined fields; every other screen uses filled fields.

`REDESIGN_BRIEF.md` section 2 says "9 routes"; that counts the screens in `RigCheckRoute.kt`. The inventory has 13 screens because it also lists Account (shown inside the Paywall route when signed out) and the three dialogs.
