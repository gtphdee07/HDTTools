# Establish a standing "how to plan" procedure in CLAUDE.md

## Context

Across this session, every time the user asked for a plan ("define the
goals, steps, and how results will be measured/definition of done for
X"), the resulting plans followed the same shape by convention, not by
written rule: Context → Goal → Steps → Definition of Done → Verification.
The user now wants this formalized as a standing procedure, plus a new
requirement: once a plan is agreed, save it as
`ClaudePlans/YYYY-MM-DD-<Title>.md` in the project root.

**Investigated before answering "skill vs CLAUDE.md vs other"**: a
`ClaudePlans/` directory already exists in this repo, containing one file
- `2026-08-24-Streamlit real-photo calkthrough (roadmap #6).md`. Turns
out the user created this directory and copied item #6's plan into it by
hand (confirmed directly) - not automatic tooling. This confirms the
actual ask: there is no existing mechanism doing this today, so the save
step needs to become something I do deliberately, every time, as part of
the standard planning procedure - not something to assume is already
handled.

## Recommendation: CLAUDE.md, not a skill

- **Why not a skill**: skills fit an explicitly-invoked (slash command)
  or narrowly-matched, self-contained named procedure - typically
  something with specialized tool sequences or domain knowledge the
  model wouldn't otherwise apply. What's being asked for here is a
  *universal modifier* to something that should happen every time
  *any* plan gets made for this project, regardless of exact phrasing -
  closer to "how this project does interaction style" than "a callable
  tool." A skill would only fire when its description matches well or
  the user remembers to invoke it by name; a standing rule applies by
  default, every time, without being asked.
- **Why CLAUDE.md**: this project already has two precedents for
  exactly this category of rule - "NEXT_STEPS.md Maintenance" and
  "Asking Questions" - both are always-on behavioral instructions, not
  situational procedures. `CLAUDE.md`'s own framing ("These instructions
  OVERRIDE any default behavior") is also the right authority level to
  extend Claude Code's own built-in Plan Mode workflow (the 5-phase
  Explore → Design → Review → Final Plan → ExitPlanMode sequence is
  itself fed to me as instructions each time plan mode activates, the
  same mechanism CLAUDE.md uses) - a CLAUDE.md rule can add a concrete
  step onto that existing workflow's Phase 4/5 without needing to
  reimplement or replace it.

## The rule to add

New `## Planning Procedure` section in `CLAUDE.md`, roughly:

```markdown
## Planning Procedure
Whenever the user asks for a plan - directly, or via language like
"what's the plan for X, including goals, steps, how results will be
measured, and the definition of done" - every plan (via Claude Code's
Plan Mode) follows this shape:
- **Context**: why this work is happening, what prompted it.
- **Goal**: what "success" is aiming at, in one or two sentences.
- **Steps**: the concrete sequence of changes/actions.
- **Definition of Done**: the specific, checkable conditions that mean
  this is actually finished - not just "code written," but verified.
- **Verification**: exactly how to confirm each part works for real.

Once the user approves a plan (`ExitPlanMode` returns approved), before
any other implementation action: save the full approved plan content to
`ClaudePlans/YYYY-MM-DD-<short-title>.md` in the project root (create
the directory if it doesn't exist). Derive `<short-title>` from the
plan's own heading - short, hyphen-separated, no spaces or punctuation
that needs escaping on any filesystem. Do this even though something in
the tooling has been observed to sometimes do this already - it hasn't
done so reliably, so this step is not conditional on that.
```

## Files

- `CLAUDE.md` - new `## Planning Procedure` section (text above,
  refined during write to match the file's existing tone/heading style).
- `ClaudePlans/2026-08-24-Streamlit real-photo calkthrough (roadmap #6).md`
  - rename to match the clean convention this rule establishes (fixes
    the "calkthrough" typo and the un-sanitized parenthetical/spaces as
    a side effect, per the user's own go-ahead).

No code changes - documentation only.

## What "done" means

- `CLAUDE.md` has an explicit, standing rule covering both halves of the
  request: the plan's required shape, and the post-approval save step.
- The rule is self-sufficient (doesn't rely on the unconfirmed auto-save
  behavior already observed once) and doesn't contradict Plan Mode's
  own built-in workflow - it adds one concrete step, doesn't replace
  anything.
- Applied immediately as its own first real test: this plan (once
  approved) gets saved to
  `ClaudePlans/2026-08-24-planning-procedure.md` (or the exact date/name
  resolved at save time), demonstrating the rule works before moving on.

## Verification

1. Read the new `CLAUDE.md` section back; confirm it's self-consistent
   with the file's existing "NEXT_STEPS.md Maintenance"/"Asking
   Questions" sections in tone and doesn't conflict with them.
2. After this plan is approved, confirm
   `ClaudePlans/2026-08-24-<title>.md` exists and its content matches
   this plan.
