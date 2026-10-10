# Worktree setup

How to make a brand-new git worktree test-ready on a machine that is already set up. For a machine that has never run this project, use `docs/BUILD_AND_DEPLOY.md` first; this picks up after it.

## Why it is needed

A new worktree contains only tracked files. Everything gitignored is missing, so tests that pass in the main checkout fail in the worktree, often confusingly. The Scan Proxy returning 502 when its install is missing is one example (reported in #83).

## The step

From the root of the new worktree:

```
uv run scripts/worktree_setup.py
```

It runs, in order, and stops at the first failure:

| Step | What it creates | Inside the worktree |
|---|---|---|
| `uv sync` | `.venv` (Python 3.14 and the locked dependencies) | yes (the downloads go through `uv`'s and npm's shared caches) |
| `npm ci` in `web/` | `web/node_modules` | yes |
| `npm ci` in `workers/scan-proxy/` | `workers/scan-proxy/node_modules` | yes |

`npm ci` installs exactly what the lockfile says. The script is safe to re-run. It then prints which local-only files are missing.

## Then run the offline suites

```
uv run pytest
npm --prefix web test
npm --prefix workers/scan-proxy test
```

None of these makes a live or paid call, and none needs `web/.env.local`. (`uv run pytest` deselects the `external` tests by default, and `tests/conftest.py` fails any other test that reaches the real Anthropic client.) The full Python run takes a couple of minutes because it includes the `slow` real-photo OCR tests, which need Tesseract. Android's own tests are not covered here: it has its own toolchain, and its tickets share one emulator (`docs/agents/session-handoff.md`).

## Local-only files that are not carried into a worktree

| File | Needed by | Offline runs |
|---|---|---|
| `web/.env.local` | Web External suite (`npm --prefix web run test:external`) and the Scan Proxy live suites. It holds the Supabase test-user credentials; the public `VITE_*` values are committed in `web/.env.production`, and copied here for local and live runs. The Scan Proxy live suites also need provider keys from the shell environment (`ANTHROPIC_API_KEY`, `REVENUECAT_SECRET_KEY`), never from a file. | not needed |
| `android/local.properties` (Android SDK path) | The Gradle command checks in `tests/test_context_test_commands.py`. They need this file **or** the `ANDROID_HOME`/`ANDROID_SDK_ROOT` environment variable; with neither, they skip rather than fail (`uv run pytest -rs` shows which). On a machine with the variable set, as the primary one has, they run in a new worktree with nothing copied. | optional |
| `workers/scan-proxy/.dev.vars` | Also gitignored, but no test reads it. Only `wrangler dev` would. | not needed |

If you need `web/.env.local`, create it as `docs/BUILD_AND_DEPLOY.md` section 3 describes, or copy the main checkout's with:

```
uv run scripts/worktree_setup.py --copy-env
```

That copies only a missing file, never overwrites one, and never prints contents. The file is gitignored (`*.local`); do not add it to a commit, paste it into a ticket, or copy it anywhere tracked.

Machine-wide tools (`uv`, Node 24, Tesseract OCR, and for Android the SDK and JDK) are not per-worktree and are not touched.

## Removing a worktree on Windows

`git worktree remove` can fail with "Filename too long" when the worktree has `node_modules` deep under a long path. If it does, git has usually already forgotten the worktree and only the folder is left. Delete the folder with a long-path prefix, then clean up git (run these from outside the worktree, because a shell sitting inside it keeps the folder locked):

```
cmd /c rmdir /s /q "\\?\<full path to the worktree folder>"
git worktree prune
git branch -d <the worktree's branch>
```

A shorter worktree location (for example `G:\wt\<name>`) avoids the problem.

## Live and External suites

They are not part of the offline run. They need the file above and, for some, a deployed Worker or a billed provider call. Follow `TESTING.md` and the surface's own `TESTING.md`, and ask the owner before any paid run.
