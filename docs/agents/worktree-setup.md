# Worktree setup

How to make a brand-new git worktree test-ready on a machine that is already set up. For a machine that has never run this project, use `docs/BUILD_AND_DEPLOY.md` first; this picks up after it.

## Why it is needed

A new worktree contains only tracked files. Everything gitignored is missing, so tests that pass in the main checkout fail in the worktree, often confusingly. The Scan Proxy returning 502 when its `node_modules` is absent is the usual example.

## The step

From the root of the new worktree:

```
uv run scripts/worktree_setup.py
```

It runs, in order, and stops at the first failure:

| Step | What it creates | Inside the worktree |
|---|---|---|
| `uv sync` | `.venv` (Python 3.14 and the locked dependencies) | yes |
| `npm ci` in `web/` | `web/node_modules` | yes |
| `npm ci` in `workers/scan-proxy/` | `workers/scan-proxy/node_modules` | yes |

`npm ci` installs exactly what the lockfile says. The script is safe to re-run. It then prints which local-only files are missing.

## Then run the offline suites

```
uv run pytest
npm --prefix web test
npm --prefix workers/scan-proxy test
```

None of these makes a live or paid call, and none needs a local-only file. (`uv run pytest` deselects the `external` tests by default, and `tests/conftest.py` fails any other test that reaches the real Anthropic client.) Android is not covered here: it has its own toolchain, and its tickets share one emulator (`docs/agents/session-handoff.md`).

## Local-only files that are not carried into a worktree

| File | Needed by | Offline runs |
|---|---|---|
| `web/.env.local` | Web External suite (`npm --prefix web run test:external`) and the Scan Proxy live suites. It holds the Supabase test-user credentials and the public `VITE_*` values. | not needed |

If you need it, create it as `docs/BUILD_AND_DEPLOY.md` section 3 describes, or copy the main checkout's with:

```
uv run scripts/worktree_setup.py --copy-env
```

That copies only a missing file, never overwrites one, and never prints contents. The file is gitignored (`*.local`); do not add it to a commit, paste it into a ticket, or copy it anywhere tracked.

Machine-wide tools (`uv`, Node 24, Tesseract OCR, and for Android the SDK and JDK) are not per-worktree and are not touched.

## Live and External suites

They are not part of the offline run. They need the file above and, for some, a deployed Worker or a billed provider call. Follow `TESTING.md` and the surface's own `TESTING.md`, and ask the owner before any paid run.
