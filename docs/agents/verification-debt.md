# Verification debt report (session start)

`scripts/verification_debt.py` (#67, spec #51) tells you at the start of a session how much code has changed since each context's tests last passed. It is advisory: it reads git and the verification ledger, prints, and exits 0. It never runs a test, never writes the ledger and never blocks a session.

```
uv run scripts/verification_debt.py
```

Example output:

```
Verification debt (session level; advisory, nothing was run)
  core: 4 file(s) changed since 1a2b3c4d, verified 3 days ago
      own: src/hdttools/breakdown.py, scripts/pass_pool.py, tests/test_breakdown.py (+1 more)
  web: 2 file(s) changed since 9f8e7d6c, verified 12 days ago
      from core: web/src/breakdown.ts, test-vectors/breakdown_cases.json
  Tests owed:
      uv run pytest -n auto -m "core and not slow"    # core context run (diff is larger than a file)
      npm --prefix web test    # web Major (public interface changed; includes Minor)
  Recommended: catch up web with a context-level run, last verified 12 days ago (limit 7 days):
      uv run scripts/verification_ledger.py run --context web --level session -- npm --prefix web test
      (the run records its pass, which clears the debt; this report never runs it)
```

## What it shows

- **Changed files per context**, measured from the commit the ledger last recorded as verified for that context at the session level (`scripts/verification_ledger.py`, #65). Each context has its own starting point. Docs-only files (the planner's `docs_globs`) never count.
- **Downstream contexts**: files that reach a context from another one, through a shared interface or a `depends_on` link in `scripts/test_planner_config.json`, are listed under `from <where they live>`. A change in Core therefore shows up as debt for Streamlit.
- **Tests owed**: the session-level plan the planner (#66) makes for that debt, minus any suite the ledger shows as already passed at the current tree. Stale External surfaces are not in it (they need the network); `uv run scripts/external_freshness.py` covers them.
- **No recorded pass**: a context the ledger has no session-level pass for has nothing to measure drift from. It is named in one line and never triggers the recommendation. Today nothing records context-level passes by itself; running a context's suite through `verification_ledger.py run --context <context> --level session -- <test command>` starts the record. If every context is in this state the report says so instead of claiming everything is verified.
- With no debt it prints `none` and still names any context without a record.

## The recommendation and its limits

A context gets a context-level catch-up recommendation when it has unverified changes **and** passes either limit:

| Limit | Meaning | Default |
|---|---|---|
| `max_files` | unverified changed files in the context | 15 |
| `max_age_days` | days since the context's last recorded pass | 7 |

The owner sets them in `scripts/test_planner_config.json`:

```json
"debt": {"level": "session", "max_files": 15, "max_age_days": 7}
```

A value of `0` switches that limit off. `--max-files N` and `--max-age-days N` override the config for one run (`uv run scripts/verification_debt.py --max-files 5`). `level` is the ledger level the report measures (`session` unless you record catch-up passes at another level). The recommended command is the context's whole session-end run (for Android, the device-free `uv run scripts/android_session_end.py`), wrapped in `verification_ledger.py run` so that a pass is recorded and clears the debt. Run it yourself; the report only prints it.

## Hooking it up to Claude Code

Changing Claude Code settings needs the owner's approval, so the repo does not ship this change. To print the report at the start of every session, add this to the project's `.claude/settings.json` (shared) or `.claude/settings.local.json` (just you):

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume",
        "hooks": [
          {
            "type": "command",
            "command": "uv run \"$CLAUDE_PROJECT_DIR/scripts/verification_debt.py\" --hook",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
```

`--hook` prints the one JSON object a SessionStart hook expects: the report as `systemMessage` (you see it) and as `additionalContext` (Claude sees it). Without `--hook` the output is plain text, which Claude Code adds to Claude's context but does not show to you.

The hook cannot block a session: the script always exits 0 (a git or ledger problem becomes a line in the report), an unknown argument is ignored, and a SessionStart hook cannot block in any case. The `timeout` (seconds) stops a slow git call from holding a session start. Inside a ticket worktree the report measures that worktree's files against the ledger shared by every worktree.
