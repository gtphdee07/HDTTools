# Web

The React + Vite + TS frontend: the paid-product-in-progress surface that wraps Core's OCR/breakdown math in a guided, multi-step flow. Local dev only today, not hosted.

## Language

**Rig**:
A user-named, reusable pairing of a Truck Tag and Trailer Tag (a `RecentRig`: nickname + truck + trailer + last-used timestamp), saved so a returning user can start a new check without re-entering or re-scanning both tags. Not a Core concept — Core's `compute_breakdown` takes bare truck/trailer/scale data with no notion of a saved, named pairing. This is the product's central noun (the app is "RigCheck"); Android maintains its own equivalent concept independently — see `android/CONTEXT.md` once written.
_Avoid_: vehicle combination, setup.

**Wizard**:
The guided, five-step flow that produces one Breakdown: select a Rig (step 0), enter/scan the Truck Tag (1), Trailer Tag (2), Scale Ticket (3), then view Results (4). Each step has its own sub-state (`upload` / `processing` / `review` / `error` / `finalizing`) tracking where the user is within that step's own data-entry flow.

**History**:
The list of a user's **past, completed** checks (`HistoryEntry`: id, date, rig nickname, Verdict) — a record of *results*, not to be confused with a Rig, which is a *reusable input* (a saved truck+trailer pairing) rather than a past outcome.

**Dashboard**:
The app's home screen, showing recent activity and entry points into the Wizard and History.
