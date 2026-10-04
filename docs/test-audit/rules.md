# Test-execution rules and audit yardstick

Agreed 2026-10-04 in a grilling session (map issue: #49). These rules extend, and do not replace, the root `TESTING.md` (Minor/Major/External) and `docs/adr/0008-*.md` (per-surface External suites). Audit agents measure the current tests against them.

## Rules

1. **Scope ladder.** File, then context (a `CONTEXT-MAP.md` context), then application. The size of the diff picks the level.
2. **Per issue.** The issue's own targeted test must exist and run first. Then Minor/Major as in `TESTING.md`, with no sampling: the module's Minor suite always; the Major suite when the public interface or a dependency changed; the inter-module interface tests for every module that shares a changed interface.
3. **Session end.** Run the whole file, context or application, per the ladder. For Android this means the JVM tests; instrumented (device) tests run only when the diff touches code they cover, or at a release.
4. **Release.** A full run of every category, including paid External tests and Android device tests, for Android (Play Store push) and the Worker (wrangler deploy). Web, Streamlit and Core have no full-run release; Core is covered through the apps that use it.
5. **Web gate.** A push that deploys Web keeps ADR-0008's External freshness gate, without a full run.
6. **External surfaces add to, never replace, the old suites.** Free surfaces run when stale. Paid surfaces run only after the owner confirms, within the surface's call maximum.
7. **Their side changed.** Detected by the registry-release-date proxy in ADR-0008. The audit lists dependencies that are not yet watched.
8. **Enforcement.** An advisory planner script may print the test set from the git diff. It never blocks.
9. **Coverage.** The audit reports gaps with no pass/fail verdict. The owner sets targets after seeing the numbers.

Interfaces under test come in two kinds: *our* declared contracts (public surface of a module, inter-module and cross-platform contracts such as the golden-vector fixture) and *their* contracts (third-party APIs: Anthropic, RevenueCat, Google Play Billing, Supabase, Cloudflare Workers/Pages).

## What each audit report must contain

Write one file per product to `docs/test-audit/<product>.md` with these sections, in this order. Cite file paths and line numbers; separate measured facts from judgement.

1. **Summary**: five lines at most; the worst gap first.
2. **Inventory**: test files grouped by `TESTING.md` category (1 function, 2 interaction, 3 module, 4 inter-module, 5 external); counts; how each group is run (exact command); runtime if measured; what it needs (network, secrets, device).
3. **Code coverage**: measured numbers if the product has a coverage tool and it can run offline; otherwise say how it could be measured. List uncovered files and functions of consequence.
4. **Feature coverage**: each feature or requirement (from the specs below) with the test that verifies it, or "none".
5. **Interface coverage**: *our* interfaces (public surface per module; shared contracts) and *their* interfaces (third-party APIs the product calls), each with the test that covers it, or "none". Note which third-party packages are watched in `scripts/external_manifest/`.
6. **Spec check**: places where tests contradict, lag behind, or exceed the stated requirements.
7. **Rule fit**: for each of rules 1 to 5 above, whether the product's tests and scripts can support it today (for example: can a Minor suite be run alone; is there a file-level command; is there a context-level command; what blocks a session-end run).
8. **Incremental complexity**: the cheapest test run to the most expensive for this product, as an ordered list with command, rough time, and cost or prerequisites at each step.
9. **Gaps and suggested tickets**: a short list, each with a one-line title, the rule or section it comes from, and a size guess (small, medium, large). Suggestions only; do not create or edit issues.

## Ground rules for audit agents

- Read-only on the product. The only file an agent writes is its own report under `docs/test-audit/`.
- Never run paid or live External tests, deploy anything, or call a provider. Offline test suites and coverage runs are fine. If a command would reach the network or need a secret, report it instead of running it.
- Use `uv run` for Python, never bare `pip` or global `python`.
- Do not install system tools. If a tool is missing, report it.
- Before any command that deletes more than one file, or writes anywhere outside this repo, show exactly what it will touch first. Prefer to avoid such commands entirely.
- Do not edit any text between `<!-- HUMAN-WRITTEN -->` markers.
