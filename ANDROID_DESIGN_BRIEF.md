# RigCheck Android — Design Brief

Handoff doc for a design pass (e.g. with Claude Designer) ahead of Phase C
(native Android). Written 2026-08-14 on the machine that's been doing the
web/Streamlit work — `git pull` to get this on whichever machine you're
using for design.

## What RigCheck is

An experimental RV/trailer tow-weight safety checker: photograph (web/
Streamlit) or manually enter (Android — see below) the numbers off a
truck's compliance label, a trailer's compliance label, and a CAT Scale
weigh ticket, and it computes an axle-by-axle pass/fail breakdown against
each axle's rated limit. It's explicitly an experimental learning
project, not a certified safety tool — every version shows a blocking
"not for safety decisions" disclaimer before results (see below).

**Live reference — the actual running app**: https://hdttools-ynfeq8py78ghmeyulo2grr.streamlit.app
(Streamlit version; same flow and field set the Android app needs to
cover, just photo-driven instead of manual-entry). Worth walking through
this once before designing — it's the fastest way to see the real
content and flow, not just this document's description of it.

The web app (React, not currently hosted) followed the same flow and was
itself built from a prior pixel-perfect design handoff — precedent for
doing the same here.

## Why Android is different: no OCR, no camera extraction

Decided when planning Phase C: the Android app is **fully native, with no
OCR and no photo extraction at all** — no Tesseract (can't bundle it
reasonably on-device), no cloud vision API (no network dependency
wanted). Instead, each entry screen shows a **reference image annotated
with where each value lives on a real label**, and the user types the
values in directly after looking at their own tag/ticket. This is the
one genuinely new UI element this app needs that neither the web nor
Streamlit version has — see "The annotated reference images" below.

## Brand / design tokens (from the existing web app)

Source of truth: `web/src/design-system/tokens.css`. Native Android has
its own conventions (Material, system fonts, density units) so treat
these as the palette/type pairing to adapt, not literal CSS to port.

**Colors**
| Token | Hex | Use |
|---|---|---|
| Sunset orange | `#f0942f` | Primary accent / CTA |
| Trail green | `#4d7a3a` | Secondary accent, "success" / pass |
| Dusk mauve | `#8d7fa0` | Tertiary accent |
| Sunset rose | `#c17f8f` | Quaternary accent |
| Charcoal | `#2a2a28` | Primary text |
| Charcoal soft | `#4a4844` | Secondary text |
| Cream | `#f6efe4` | Page background |
| White | `#ffffff` | Card/surface background |
| Danger red | `#b5473a` | "Over limit" / fail state |

**Type**: "Quicksand" (headings/display, weight 600–700), "Karla" (body
text), "Alex Brush" (script — used sparingly/decoratively, e.g. a
wordmark, not body content).

**Spacing scale**: 4 / 8 / 12 / 16 / 24 / 32 / 48 / 64px (small to large).
**Corner radius**: 8px (small controls), 14px (cards), 22px (large
panels), pill/999px (buttons, badges).

The overall feel (from the web app's copy and layout): warm, friendly,
a little playful ("Wandering Trails, Wagging Tails" — this is an RV/dog
household's project) rather than clinical or heavily technical, despite
being a numbers-and-safety tool.

## Screens needed

1. **Rig picker** — pick one of up to 5 recently-used rigs (stored
   on-device only, no server — see "Data & persistence" below), each
   showing a nickname + truck/trailer manufacturer if known; or start a
   new rig by typing a nickname (e.g. "Big Blue").
   - Picking an existing rig should skip straight to the Scale Ticket
     screen (step 3) — truck/trailer specs don't change trip to trip,
     only the scale reading does. This is already how the web/Streamlit
     versions behave.
2. **Truck tag entry** — reference image (annotated Ford-style
   compliance label) + fields:
   - Manufacturer (text)
   - GVWR, lb (number)
   - Front GAWR, lb (number)
   - Rear GAWR, lb (number)
   - Stand-alone weight, lb (number, **optional** — used to estimate
     tongue weight; label should make clear it's optional)
3. **Trailer tag entry** — reference image (annotated Brinkley-RV-style
   compliance label) + fields:
   - Manufacturer (text)
   - GVWR, lb (number)
   - GAWR per axle, lb (number)
   - Axle count (number, **optional, defaults to 2** — make the default
     visible/explained, not just an empty field)
   - Unloaded weight / UVW, lb (number)
4. **Scale ticket entry** — reference image (annotated CAT Scale ticket)
   + fields:
   - Scale location (text)
   - Steer axle, lb (number)
   - Drive axle, lb (number)
   - Trailer axle(s), lb (number)
   - Gross weight, lb (number)
5. **Disclaimer** — blocking, shown once per app session before the
   first results screen. Exact required text (already used verbatim on
   web/Streamlit, keep identical):

   > **Experimental Tool — Not for Safety Decisions**
   >
   > RigCheck is an experimental project built to learn AI-assisted
   > software development, not a certified or professional weight-safety
   > tool. Its numbers come from OCR-read photos, manually reviewed by
   > you, and simplified math — any step of that chain can be wrong.
   >
   > Do not use this tool to decide whether your rig is safe to tow.
   > Always verify actual weights and ratings using a certified scale
   > and your vehicle's official documentation, and consult a qualified
   > professional if you're unsure. You use this tool, and any decisions
   > you make based on it, entirely at your own risk and responsibility.

   (Note: the wording mentions "OCR-read photos" — fine to keep as-is
   since it's factually still true of the *data* the math is chained
   from conceptually, but flag to me if you'd rather adjust the wording
   for the manual-entry Android context specifically.)
6. **Results** — six axle-by-axle comparisons, each needing: label,
   actual value, rated limit, a pass/fail visual treatment (green/red,
   not just color — we already hit a bug on Streamlit where an
   over-limit item rendered green because the color logic didn't
   actually key off pass/fail, so make the fail state visually
   unambiguous beyond color alone, e.g. an icon), a percent-of-limit
   bar, and an optional explanatory note. Rows:
   - Front Axle (Steer)
   - Rear Axle (Drive)
   - Tow Vehicle Total (GVWR)
   - Trailer Axle(s)
   - Trailer Total (GVWR) — note may mention an estimated tongue-weight
     inclusion if stand-alone weight was provided
   - Combined Rig Weight

   Plus an overall verdict banner above the breakdown: "Safe to Tow"
   (green) or "Not Safe to Tow" (red), with a one-line explanation.

## The annotated reference images

For each of the three entry screens (truck tag, trailer tag, scale
ticket), design a reference image: a photo or clean illustration of a
real label/ticket with callouts (arrows/circles + labels) pointing at
exactly the value each input field is asking for. Goal: someone who has
never seen a compliance label before can look at the reference image,
find the same spot on their own tag, and type the number in confidently.

Starting material — real, already-in-repo example photos:
- `ExampleDocs/AddieTag.jpg` — truck compliance label (Ford)
- `ExampleDocs/GooseTag.jpg` — trailer compliance label (Brinkley RV)
  (note: these two filenames are swapped relative to what they imply —
  `AddieTag.jpg` is actually the *truck* tag and `GooseTag.jpg` is
  actually the *trailer* tag; this is a known pre-existing mix-up,
  already noted in `NEXT_STEPS.md`, not something to fix here — just
  don't be misled by the names when picking source material)
- `ExampleDocs/CatScale-Ticket.jpg` — CAT Scale weigh ticket

## Data & persistence (Android-specific)

- No server, no shared backend — matches the "self-contained per
  platform" decision made for the whole portability effort (web app
  dropped its SQL database for the same reason; Streamlit uses a local
  JSON file).
- "Last 5 rigs" should persist on-device only (e.g. Room or DataStore —
  an implementation detail for the build phase, not a design concern,
  but worth knowing the data *is* expected to survive an app restart,
  unlike the web app's session-only check history).
- No camera/photo capture UI needed anywhere — this is 100% manual entry
  guided by the static reference images above.

## Deliverables

- Wireframes/mockups for all 6 screens above, phone-sized (the existing
  web design system was not built mobile-first, so don't assume its
  layout choices translate directly).
- Visual treatment for the annotated reference images (at least one
  fully worked example, e.g. the truck tag, to establish the pattern
  the other two should follow).
- Confirmation of touch-friendly control sizing (tap targets, input
  field height) — the web app's inputs were designed for mouse/keyboard.

## Bringing it back

Once mockups exist, commit them into this repo (suggest a new
`android/design/` directory for image assets, or link out if hosted
elsewhere) so the next Phase C planning/build session has them
alongside the code. Flag anything in this brief that turned out to be
wrong, missing, or worth reconsidering once you're actually in the
design work — this doc is a starting point, not a locked spec.
