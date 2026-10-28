# Design source: the generator behind the frames

Design tooling for the Android re-skin (#187). It is **not application code**: nothing in the app, the build or the test suites imports it, it has no tests, and `scripts/static_checks.py` does not look at this folder (it has its own `ruff.toml`). It is here so a future session can change a frame and get the same files back instead of redrawing by hand.

## What it does
Python builds each screen state as HTML from one component library, renders it with headless Chromium at 2x, measures every element tagged with an inventory id (size, region, reading order, text style), draws the numbered annotation tags, and writes the annotated PNG. The measurements are what fill the `new_region`, `new_width`, `new_height`, `new_order` and `new_style` values in the redesign maps. Output (frames, measurements, canvas boards) goes to a scratch folder, never into the repo directly; a separate step copies chosen files in.

Proof it reproduces the hand-back: rebuilding all 70 frames from this folder gave PNGs **byte-identical** to `design-return/annotated/` (checked 2026-10-28, same machine and Chromium).

## Files
| File | Role |
|---|---|
| `config.py` | Paths and tool lookup. The repo root comes from this folder's place in the repo; `RIGCHECK_DESIGN_OUT` and `CHROME_PATH` override the scratch folder and the browser. |
| `lib.py` | Tokens (colours, radii, shadows), icons, and every component: buttons, chip, badge, header, field, notice, card, dialog, sheet, spinner, the phone frame. A component's `_id` argument is the inventory id; it becomes `data-id` and is what the measurer reads. |
| `screens_a.py`, `screens_b.py`, `screens_c.py` | The screen states, registered with `add(screen, state, builder, scroll_to=...)`. The pair `<screen>__<state>` is the frame name. A, B and C are only a split by size. |
| `build.py` | Renders every state (or those whose name contains the argument): `html/`, `png/`, `meta/` (measurements), `boards/` (`.dc.html` for the Design canvas). |
| `assets.py` | Writes the icon and splash SVGs and the 512 px icon into `design-return/assets/`. |
| `sheet.py` | Contact sheets of chosen frames, for review. |
| `check_hand_back.py` | The completeness check run on the hand-back: every inventory id is in exactly one map, tags match the inventory, frames exist at 824 x 1784, legends resolve. It encodes the two rounds' frame lists; adapt them for a new round. |
| `round1_mapgen.py` | Round 1: derived the full 150-element map from the measurements. **Refuses to run** without `--overwrite-first-round`, because it would replace the committed first map. Keep it as the reference for how a full map is derived. |
| `round2_followup_map.py` | Round 2: the delta round for the 17 added controls. It compares fresh frames with the committed ones, copies only the new and changed PNGs, fills a fixed list of ids and rebuilds the legends. It cannot re-run on the committed state (nothing would be new). Copy it for the next delta round. |

## Running it
Needs: Python via `uv`, the `playwright` package (not a project dependency; use `--with`), a Chromium (Playwright's cached one is found automatically on Windows; otherwise set `CHROME_PATH` or run `playwright install chromium`), and network access for Google Fonts (Outfit and DM Sans).

From this folder:

```
uv run --no-project --with playwright python build.py
uv run --no-project --with playwright python build.py delete_rig
```

The first builds everything; the second only the states whose name contains the text. Then look at the frames (`sheet.py`), copy the ones you mean to ship into `design-return/annotated/`, and update the maps and docs.

## Making a change
1. Edit the component in `lib.py` or the state in `screens_*.py`. Keep the `_id` of every element that has an inventory id; never reuse an id for a different function.
2. Rebuild, then compare with the committed frames (hash them). Only the frames you meant to change should differ; the rest being byte-identical is the check that nothing else moved.
3. New element ids need an entry in the inventory first (`ui-inventory.json`); the maps are derived from it.
4. For a delta round, copy `round2_followup_map.py`, change the id list and the notes, run it once, then `check_hand_back.py`.
5. Update `components.md`, `copy-changes.md` and the README in `design-return/` by hand; they are written, not generated.

## What is not in the repo, and the limits
- **The editable Design canvas** (a private Claude Design artifact) holds a generated copy of every frame (`boards/`). Editing it by hand does not flow back here. It was published with the Artifact tool by a Claude session. The logo in the boards is an uploaded asset of that canvas (`LOGO` in `lib.py`, a `/_blob/<id>` path); a new canvas needs the logo uploaded again and that constant updated. `build.py` swaps it for `web/public/logo.png` when it renders locally.
- **Placeholders:** the label crop (Truck and Trailer), the ticket image (Scale) and the Google glyph are drawn stand-ins. The truck photo is not used because it shows a readable VIN.
- **Reproducibility:** the byte-identical result holds on the machine that produced it. Another Chromium or font version can shift pixels by a little; compare by eye in that case and expect every frame to differ.
- **Sizes in the maps are measured from these frames, not from the running app.** After #189's baseline capture the app is the truth, and these frames matter less.
- **The first-round tokens and the Wandering Trails design system** live in `design-return/tokens.json`; the component library repeats the colours as constants in `lib.py`. Change both together.
