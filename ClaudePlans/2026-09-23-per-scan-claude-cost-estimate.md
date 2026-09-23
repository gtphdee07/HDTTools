# Per-scan Claude API cost estimate

Research for [issue #9](https://github.com/gtphdee07/HDTTools/issues/9), "Estimate real
per-scan Claude API cost", a child of [#3](https://github.com/gtphdee07/HDTTools/issues/3)
(shared Android+Web accounts/paywall) and a blocking input to
[#10](https://github.com/gtphdee07/HDTTools/issues/10) ("Lock pricing model"). This document
answers the cost question only — it does **not** set a credit price or subscription tier;
that's #10's job.

Ground truth for every claim below is either this repo's own source (cited by path/line) or
Anthropic's own docs (cited by URL), fetched 2026-09-23.

## 1. The real request shape

### 1.1 What `claude.ts` actually sends

`workers/scan-proxy/src/claude.ts:13` pins the model:

```ts
const MODEL = "claude-sonnet-5";
```

The comment above it (`claude.ts:5-12`) documents *why*: Haiku 4.5 was tried first
(~$0.01/scan estimate at the time) but returned confidently wrong GVWR/GAWR numbers on a real
fixture (`AddieTag.jpg`) on two separate live calls, so the code was moved to Sonnet 5.

`extractFields()` (`claude.ts:20-61`) builds one `messages.create()` call per scan:

- `max_tokens: 1024`
- `system: config.systemPrompt` — a doc-type-specific instruction string from `docTypes.ts`
- `tools: [{ name, description, input_schema }]` — one tool, one doc-type-specific JSON schema
- `tool_choice: { type: "tool", name: config.toolName }` — **forced** tool use (not `auto`)
- one user message containing an `image` block (`type: "base64"`, real `media_type`, real
  `data`) followed by a fixed text block: `"Extract the requested fields from this image."`

`claude.test.ts` (the SDK's own coverage, `claude.test.ts:38-61`) confirms this shape end to
end by mocking `fetch` and asserting on the captured request body: `model` is
`"claude-sonnet-5"`, `tool_choice` is `{ type: "tool", name: config.toolName }`, and the image
block's `source.media_type`/`source.data` pass through unchanged. The test fixtures use a
trivial 1-byte-decoded placeholder (`"aGVsbG8="`) for `data`, so the test file is useful for
confirming *shape*, not for real image size — that has to come from the real image pipeline
(§1.2).

There is no `workers/scan-proxy/CONTEXT.md` in this repo/branch (searched; not found), so "a
Scan" vocabulary is taken from `NEXT_STEPS.md` item #20 and the code itself instead.

### 1.2 The real image: size, resize, encoding

Android is the only client that currently drives this path in production. Its encoder is
`android/app/src/main/java/com/rigcheck/app/data/PhotoEncoding.kt`:

```kotlin
private const val MAX_LONG_EDGE_PX = 1600
private const val JPEG_QUALITY = 85
```

`encodePhotoForScan()` downscales any captured photo so its long edge is at most 1600px
(preserving aspect ratio via `Bitmap.createScaledBitmap`), re-encodes as JPEG at quality 85,
then base64-encodes it for `ScanApiClient`'s `image_base64` field. The comment on this file
(`PhotoEncoding.kt:10-13`) is explicit that this value was chosen to land near "~1,600 image
tokens" for the existing $0.01–0.03/scan placeholder in `NEXT_STEPS.md` — i.e. this file *is*
the prior, informal version of the same calculation this document now makes precisely.

Real fixture photos exist in the repo at `ExampleDocs/AddieTag.jpg` and `ExampleDocs/GooseTag.jpg`
(also duplicated under `android/app/src/androidTest/assets/`). Both are genuine Samsung
SM-G996U phone captures, EXIF-confirmed at **4032×1816px**. Applying the app's real resize
(long edge → 1600px, aspect preserved): scale = 1600/4032 = 0.39683; output ≈
**1600×720px** — this is the actual pixel size of the JPEG base64 payload `claude.ts` sends to
Anthropic for a truck/trailer tag photo. (CAT scale ticket photos would typically be a similar
phone-camera aspect ratio; no scale-ticket-specific resize logic exists — the same
`encodePhotoForScan()` path handles all three doc types.)

### 1.3 The three doc types (`docTypes.ts`)

`DOC_TYPE_CONFIG` (`workers/scan-proxy/src/docTypes.ts:28-158`) defines `truck_tag`,
`trailer_tag`, and `scale_ticket`, each with its own `systemPrompt`, `toolName`,
`toolDescription`, and JSON `schema`. Measured directly from the source (system prompt + tool
name + tool description + `JSON.stringify(schema)`, i.e. the actual text Anthropic bills as
input):

| Doc type | System+tool+schema chars | ≈ tokens (÷4) |
|---|---|---|
| `truck_tag` | 1,531 | 383 |
| `trailer_tag` | 1,211 | 303 |
| `scale_ticket` | 1,254 | 314 |

The three doc types are close in size (303–383 tokens) — none dominates, and as shown in §3
this whole component is smaller than the image itself. `truck_tag` is the largest (it has two
nested tire sub-objects, front and rear) and is used below as the representative/worst case;
`trailer_tag` (one tire object, no front/rear split) is the smallest.

## 2. Image tokens: Anthropic's actual formula

Per Anthropic's vision docs (primary source, fetched 2026-09-23):

> Claude views images in patches instead of pixels. Each patch is a 28×28-pixel block of the
> image, referred to as a visual token. An image, therefore, costs `⌈width / 28⌉ × ⌈height / 28⌉`
> visual tokens.
>
> — [Vision — Resolution and token cost](https://platform.claude.com/docs/en/build-with-claude/vision#evaluate-image-size)

Each model has a resolution tier that caps this before the formula matters:

| Resolution tier | Models | Max long edge | Max visual tokens |
|---|---|---|---|
| Standard | pre-4.7 models | 1568px | 1568 |
| High-resolution | Claude 4.7 and later models | 2576px | 4784 |

Claude Sonnet 5 is on the **high-resolution tier** (confirmed via Anthropic's own vision docs
page framing "Claude 4.7 and later models," and independently corroborated by third-party
coverage of the Sonnet 5 launch noting it as "the first Sonnet-tier model with a high-resolution
image tier"). This turns out not to matter for this specific calculation — see below.

Applying the formula to the real 1600×720px image from §1.2:

```
⌈1600 / 28⌉ × ⌈720 / 28⌉ = 58 × 26 = 1,508 visual tokens
```

1,508 is under **both** tiers' caps (1,568 standard / 4,784 high-res), so Claude does not
downscale it further regardless of which tier applies — the 1,508 figure is exact, not an
approximation, and the standard-vs-high-res tier ambiguity that would otherwise matter turns
out to be moot here. (Source for the exact resize/no-resize rule: [Coordinates and bounding
boxes — How Claude resizes and pads
images](https://platform.claude.com/docs/en/build-with-claude/vision-coordinates#how-claude-resizes-and-pads-images).)

This is a clean validation of the Android-side comment in §1.2: they targeted "~1,600 image
tokens" and the real, formula-derived number is 1,508 — a 5% margin, well within "close enough
to plan around."

## 3. Assembling the full input-token count

For one scan (`truck_tag`, the representative/largest doc type):

| Component | Tokens | Source |
|---|---|---|
| Image (1600×720px, high-res tier, under both caps) | 1,508 | §2, formula |
| User text block `"Extract the requested fields from this image."` (47 chars) | 12 | ÷4 char rule ([pricing FAQ](https://platform.claude.com/docs/en/about-claude/pricing#how-is-token-usage-calculated): "1 token is approximately 4 characters") |
| System prompt + tool name + tool description + JSON schema | 383 | §1.3, measured from `docTypes.ts` |
| Forced tool-choice system-prompt overhead (Claude Sonnet 5, `tool_choice: {type: "tool", ...}`) | 474 | [Pricing — Tool use pricing table](https://platform.claude.com/docs/en/about-claude/pricing#tool-use-pricing), row "Claude Sonnet 5 / `any`, `tool`" — this is exact, documented per-model, not estimated |
| **Total input tokens** | **2,377** | |

The same arithmetic for the other two doc types:

| Doc type | Image | Text | Sys+tool+schema | Tool-choice overhead | **Total input** |
|---|---|---|---|---|---|
| `truck_tag` | 1,508 | 12 | 383 | 474 | **2,377** |
| `trailer_tag` | 1,508 | 12 | 303 | 474 | **2,297** |
| `scale_ticket` | 1,508 | 12 | 314 | 474 | **2,308** |

The image (1,508 tokens) is ~63–66% of total input regardless of doc type — doc-type choice is
a minor cost factor compared to the image itself, confirming the framing in §1.3.

**Important — `claude.ts` does not use prompt caching** (no `cache_control` anywhere in
`extractFields()`), and each scan is a fresh, independent, single-turn request (no conversation
history resent). So there is no cache discount to apply here: every scan pays the full base
input rate on every one of these tokens, every time.

## 4. Output tokens

`max_tokens: 1024` is a ceiling, not the real spend — `extractFields()` expects exactly one
`tool_use` block whose `input` matches the doc type's schema (`claude.ts:54-58`), and nothing
else in the response gets used.

To estimate a realistic filled-in JSON payload, this document constructed one plausible
example object per schema (real-looking VIN, weights, tire specs, etc.) and measured its
serialized size:

| Doc type | Example JSON size | ≈ output tokens (÷4) |
|---|---|---|
| `truck_tag` (20 fields incl. 2 nested tire objects) | 438 chars | 110 |
| `trailer_tag` (15 fields incl. 1 nested tire object) | 319 chars | 80 |
| `scale_ticket` (17 flat fields) | 425 chars | 107 |

**Caveat that matters for the real number — adaptive thinking is on by default for Sonnet 5,
and it's billed as output tokens even though it's invisible.** `claude.ts` never sets a
`thinking` parameter. On Claude Sonnet 5, omitting `thinking` does not mean "no thinking" — per
Anthropic's docs, Sonnet 5 runs **adaptive thinking by default** when the parameter is omitted,
and (unlike some newer models) adaptive thinking is compatible with forced `tool_choice`, which
is exactly what this code uses. Anthropic's pricing/thinking docs state thinking tokens are
billed at the standard output rate "under every setting," and the default `display` is
`"omitted"` — meaning the thinking, if any occurs, is both billed and invisible in the response
your code reads. Because adaptive thinking dynamically decides *whether* and *how much* to
think per-request, and this is a narrow, low-ambiguity extraction task (read a label, fill a
schema) rather than open-ended reasoning, actual hidden thinking spend for this workload cannot
be stated precisely without an instrumented real call (reading `response.usage.output_tokens`
directly) — it is very plausibly small-to-none for a task this constrained, but it is not
provably zero from documentation alone.

So this document gives a **baseline** (JSON-only, no meaningful hidden thinking) and flags the
uncertainty rather than hiding it:

- Baseline output: **~100 tokens** (average of the three doc types above)
- If adaptive thinking adds a moderate hidden buffer (e.g. 300 tokens, a plausible guess for
  this task shape, not a documented figure): output rises to ~400 tokens
- Recommended follow-up (cheap, decisive): log `response.usage.output_tokens` from a handful of
  real production `extractFields()` calls — this single number resolves the uncertainty
  completely and costs nothing beyond scans already happening.

## 5. Current pricing (Claude Sonnet 5, fetched 2026-09-23)

Per Anthropic's official pricing page:

> Claude Sonnet 5 — Base input tokens: **$2 / MTok**. Output tokens: **$10 / MTok**.
>
> — [Pricing — Model pricing](https://platform.claude.com/docs/en/about-claude/pricing#model-pricing)

The page also notes explicitly that this is *not* introductory pricing about to expire: the
$2/$10 rate "announced at launch as introductory pricing through August 31, 2026, is now the
standard price. The previously scheduled increase to $3/$15 per million input/output tokens on
September 1, 2026 will not occur." So $2/$10 is the durable, current rate as of this
research (2026-09-23), not a rate about to change underneath this estimate.

No Batch API (real-time scan, awaited synchronously by Android within a 20s timeout —
`claude.ts:15-18`, `ANTHROPIC_TIMEOUT_MS = 20_000`) and no prompt caching (§3) apply, so the
plain base input/output rates are the correct ones to use — no discount multiplier.

## 6. The arithmetic: dollars per scan

Using `truck_tag` (largest schema, representative worst case) and the baseline (JSON-only)
output estimate:

```
input:  2,377 tokens × ($2.00 / 1,000,000)  = $0.004754
output:   110 tokens × ($10.00 / 1,000,000) = $0.001100
                                    total    = $0.005854
```

All three doc types, baseline output, same method:

| Doc type | Input tokens × $2/MTok | Output tokens × $10/MTok | **Total per scan** |
|---|---|---|---|
| `truck_tag` | 2,377 × $2e-6 = $0.004754 | 110 × $1e-5 = $0.001100 | **$0.005854** |
| `trailer_tag` | 2,297 × $2e-6 = $0.004594 | 80 × $1e-5 = $0.000800 | **$0.005394** |
| `scale_ticket` | 2,308 × $2e-6 = $0.004616 | 107 × $1e-5 = $0.001070 | **$0.005686** |

**Average across the three doc types: ≈ $0.0056/scan (about 0.56 cents).**

If the adaptive-thinking uncertainty from §4 turns out to add a moderate hidden output buffer
(e.g. +300 output tokens = +$0.003), the per-scan cost rises to roughly **$0.0086–$0.0089**.
Even a generous +1,000 hidden thinking tokens (+$0.010, close to saturating the 1024-token
`max_tokens` ceiling) only pushes the ceiling to roughly **$0.015–$0.016/scan**.

## 7. Final figure and sanity check

**Real per-scan Claude API cost, Claude Sonnet 5, current pricing: ≈ $0.006/scan baseline,
with a documented-but-unresolved upside to ≈ $0.016/scan worst case** depending on how much
(if any) invisible adaptive-thinking output the model actually spends on this task — resolvable
with one real `response.usage` read, not further research.

**Sanity check against the code's own prior guess:** `claude.ts:5-6`'s inline comment already
estimated "Sonnet 5, not the cheaper Haiku 4.5 this used to be pinned to (~$0.01/scan vs
~$0.03)." This document's independently-derived range ($0.006–$0.016/scan, centered close to
$0.01) brackets that guess closely — the informal estimate that motivated the Sonnet 5 switch
holds up against the real, formula-and-pricing-table-grounded number.

**What this means for #10 ("Lock pricing model") — informational only, not a decision here:**
at true cost of ~$0.006–$0.016/scan, even a conservative 5–10x margin target lands a
break-even credit price/scan around $0.03–$0.16, which is small next to any plausible per-scan
or per-credit price a user-facing paywall would charge (the existing $0.01–0.03/scan placeholder
in `NEXT_STEPS.md` was already in the right ballpark). Real Claude cost is very unlikely to be
the constraint on #10's pricing decision — RevenueCat/Stripe fees, support cost, and desired
margin are far more likely to dominate that decision than the API cost computed here.

---

### Sources

- [Vision — Resolution and token cost](https://platform.claude.com/docs/en/build-with-claude/vision#evaluate-image-size) (image token formula, resolution tiers)
- [Coordinates and bounding boxes — How Claude resizes and pads images](https://platform.claude.com/docs/en/build-with-claude/vision-coordinates#how-claude-resizes-and-pads-images) (exact resize-or-not rule)
- [Pricing — Model pricing](https://platform.claude.com/docs/en/about-claude/pricing#model-pricing) (Claude Sonnet 5 $2/$10 per MTok, standard-price confirmation)
- [Pricing — Tool use pricing](https://platform.claude.com/docs/en/about-claude/pricing#tool-use-pricing) (forced tool-choice system-prompt overhead, 474 tokens for Claude Sonnet 5)
- [Pricing — How is token usage calculated (FAQ)](https://platform.claude.com/docs/en/about-claude/pricing#how-is-token-usage-calculated) (≈4 chars/token rule of thumb)
- This repo: `workers/scan-proxy/src/claude.ts`, `workers/scan-proxy/src/claude.test.ts`, `workers/scan-proxy/src/docTypes.ts`, `android/app/src/main/java/com/rigcheck/app/data/PhotoEncoding.kt`, `ExampleDocs/AddieTag.jpg` (EXIF dimensions), `NEXT_STEPS.md` item #20
