# Core

The shared tow-rig safety-check domain: OCR extraction from real-world documents, and the weight-margin math that turns those readings into a pass/fail verdict. Every product surface (Android, Web, Streamlit) is a client of this math, whether by calling it directly (Web, Streamlit) or by hand-porting it (Android).

## Data sources

**Truck Tag**:
The truck manufacturer's compliance/certification data plate — the source of a truck's GVWR and front/rear GAWR.
_Avoid_: sticker, label (use "tag," the term this project's code and OCR modules already use).

**Trailer Tag**:
The trailer manufacturer's compliance/certification data plate — the source of a trailer's GVWR and per-axle GAWR.

**Scale Ticket**:
A real, physical weighing ticket (e.g. from a CAT scale) giving actual measured axle weights for a hitched or unhitched rig — the "actual" side of every weight comparison, as opposed to a tag's "rated" side.

**Steer Axle / Drive Axle**:
The truck's front axle and rear axle, each with its own actual (scale) weight and rated GAWR limit.

**Standalone Weight**:
The truck's own actual weight measured without a trailer hitched to it — used to estimate Pin Weight when no direct hitched-and-unhitched pair of scale readings exists.

**Hitched Reading**:
A Steer Axle + Drive Axle scale reading taken while the trailer is hitched. When both a Hitched Reading and a Standalone Weight exist, Pin Weight can be calculated exactly rather than estimated.

## Weight-rating vocabulary

**GVWR** (Gross Vehicle Weight Rating):
The manufacturer's maximum rated weight for one vehicle (truck or trailer) on its own, read from that vehicle's Tag.

**GAWR** (Gross Axle Weight Rating):
The manufacturer's maximum rated weight for one axle (or, for a trailer, per axle across all its axles), read from a Tag.

**UVW** (Unloaded Vehicle Weight):
A trailer's own empty weight, read from its Tag. Captured and displayed, but **not currently consumed by `compute_breakdown`** — no Breakdown Item compares against it today.

**GCWR** (Gross Combined Weight Rating):
The truck manufacturer's maximum rated weight for the truck-plus-trailer combination, specified separately from GVWR (typically in the owner's manual, not the compliance Tag) and often lower than the sum of the two vehicles' individual GVWRs. **Not currently captured anywhere in this product** — see the "Combined Rig Weight" entry below and [issue #1](https://github.com/gtphdee07/HDTTools/issues/1).

**Pin Weight**:
The portion of a hitched fifth-wheel/gooseneck trailer's weight transferred onto the truck's hitch point, expressed as a percentage of the trailer's total weight (`DEFAULT_PIN_WEIGHT_PCT` = 20%). This product is scoped to fifth-wheel/gooseneck trailers today.
_Avoid_: tongue weight — a related but physically distinct concept for bumper-pull/ball-hitch trailers, which this product doesn't yet distinguish or support (see [issue #2](https://github.com/gtphdee07/HDTTools/issues/2)). Don't use the two terms interchangeably in new code or copy.

## Breakdown

**Breakdown**:
The ordered list of weight comparisons (Front Axle, Rear Axle, Tow Vehicle Total, Trailer Axle(s), Trailer Total, Combined Rig Weight) produced by comparing each Item's actual weight against its rated limit. This is a *weight-margin report*, not a mechanical failure — the name is established throughout the codebase (`compute_breakdown`, `POST /api/breakdown`) and isn't being revisited, but don't let "breakdown" drift toward meaning "the rig broke down" in any new copy or comments.

**Item**:
One row of a Breakdown (e.g. "Front Axle (Steer)," "Combined Rig Weight") — an actual weight, a rated limit, a Margin, a Tone, and an Estimated flag.

**Margin**:
The headroom between an Item's rated limit and its actual weight (`limit - actual`), shown to the user as "N lb to spare" (positive) or "N lb over" (negative).

**Tone**:
An individual Item's own pass/fail/insufficient-data signal (`success` / `warning` / `insufficient`). Distinct from Verdict's `status`, which summarizes across every Item in the Breakdown.

**Estimated**:
A flag on an Item marking that its actual weight was derived (via Pin Weight math) rather than read directly from a Scale Ticket. A safety-relevant distinction: an Estimated Item is less certain than a directly-measured one.

**Combined Rig Weight**:
The Breakdown Item comparing the rig's actual gross weight against a combined-weight limit. Today that limit is `truck GVWR + trailer GVWR` — a deliberate-looking but actually unintended approximation of GCWR, since no real GCWR value is ever captured from the user. See [issue #1](https://github.com/gtphdee07/HDTTools/issues/1): the intended fix is to use a real GCWR when the user provides one, and skip this Item entirely (mark it `insufficient`, not approximate it) when they don't.

**Verdict**:
The overall `pass` / `fail` / `partial` / `insufficient` summary computed across every Item in a Breakdown (`verdict_for`). A single `fail` Tone anywhere always wins, even if other Items are `insufficient` — missing data never hides a genuine over-limit reading.
