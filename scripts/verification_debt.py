"""Session-start verification debt report (#67; spec #51).

Prints what each context has changed since the commit the verification ledger (#65) last
recorded as verified at the session level: the changed files per context, the files that
reach a context from another one (an interface or dependency change upstream), and the
tests the planner (#66) says are owed. Once a context passes the size or age limit
it recommends a context-level catch-up run, as a command for the owner to run.

It is advisory and read-only. It never runs a test, never writes the ledger and never
fails: any problem is printed as a line of the report and the exit code stays 0, so a
Claude Code SessionStart hook can call it without ever blocking a session.

  uv run scripts/verification_debt.py            # plain text
  uv run scripts/verification_debt.py --hook     # the JSON a SessionStart hook prints

Limits live in scripts/test_planner_config.json under "debt" (a value of 0 switches that
limit off); `--max-files` and `--max-age-days` override them for one run:

  "debt": {"level": "session", "max_files": 15, "max_age_days": 7}

A context with no recorded pass has nothing to measure drift from, so it is named once
and never triggers the recommendation. Docs-only files never count (the planner's
`docs_globs`). Stale External surfaces are not part of this report (they need the
network); `uv run scripts/external_freshness.py` covers them. Setup of the hook:
docs/agents/verification-debt.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_planner as planner  # noqa: E402

DEFAULT_LEVEL = "session"
DEFAULT_MAX_FILES = 15
DEFAULT_MAX_AGE_DAYS = 7
LISTED_FILES = 5  # files named per context before "+N more"
LEDGER_RUN = "uv run scripts/verification_ledger.py run --context {context} --level {level} -- {command}"


@dataclass
class Limits:
    max_files: int = DEFAULT_MAX_FILES  # 0 = no size limit
    max_age_days: int = DEFAULT_MAX_AGE_DAYS  # 0 = no age limit


@dataclass
class ContextDebt:
    name: str
    since: str  # the verified commit the files are measured from
    age_days: float | None  # days since that pass; None if the ledger has no timestamp
    own: list[str] = field(default_factory=list)  # files inside the context's own paths
    inherited: dict[str, list[str]] = field(default_factory=dict)  # files from elsewhere, by where they live

    @property
    def count(self) -> int:
        return len(self.own) + sum(len(v) for v in self.inherited.values())


@dataclass
class Nudge:
    context: str
    reasons: list[str]
    command: str  # the context-level run


@dataclass
class Report:
    level: str
    debts: list[ContextDebt] = field(default_factory=list)
    no_record: list[str] = field(default_factory=list)
    owed: list[planner.Selection] = field(default_factory=list)
    nudges: list[Nudge] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def load_limits(config: dict) -> tuple[str, Limits]:
    section = config.get("debt", {})
    level = section.get("level", DEFAULT_LEVEL)
    return level, Limits(int(section.get("max_files", DEFAULT_MAX_FILES)),
                         int(section.get("max_age_days", DEFAULT_MAX_AGE_DAYS)))


def _age_days(stamp: str | None, now: datetime) -> float | None:
    if not stamp:
        return None
    try:
        then = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return max((now - then).total_seconds() / 86400, 0.0)


def build(
    config: dict,
    markers: set[str],
    *,
    level: str,
    limits: Limits,
    diff,
    verified,
    verified_at,
    base: str = "HEAD",
    now: datetime | None = None,
    passed_at=lambda command: None,
    file_exists=None,
) -> Report:
    """`diff(ref)`, `verified(context, level)` and `verified_at(context, level)` are the planner's
    git diff and the ledger's lookups (fakes in the tests); `passed_at(command)` is the planner's
    ledger answer for a suite (the tree it already passed at, else None)."""
    now = now or datetime.now(timezone.utc)
    contexts = config["contexts"]
    found = planner.unverified_since(config, level=level, diff=diff, verified=verified, base=base)
    report = Report(level=level)

    recorded = [name for name in contexts if found.since[name]]
    report.no_record = [name for name in contexts if not found.since[name]]
    for note in found.notes:
        if "ledger unavailable" in note or "is not readable" in note:
            report.notes.append(note)

    debt_by_file: dict[str, set[str]] = {}
    for name in recorded:
        files = found.files[name]
        if not files:
            continue
        try:
            age = _age_days(verified_at(name, level), now)
        except Exception:  # the age is a nicety; the size limit still works without it
            age = None
        entry = ContextDebt(name, found.since[name] or "", age)
        for f in files:
            debt_by_file.setdefault(f, set()).add(name)
            if name in planner._owners(f, contexts):
                entry.own.append(f)
            else:
                owners = sorted(planner._owners(f, contexts)) or ["shared files"]
                entry.inherited.setdefault(", ".join(owners), []).append(f)
        report.debts.append(entry)
        reasons = []
        if limits.max_files and entry.count >= limits.max_files:
            reasons.append(f"{entry.count} unverified files (limit {limits.max_files})")
        if limits.max_age_days and age is not None and age >= limits.max_age_days:
            reasons.append(f"last verified {_days(age)} ago (limit {limits.max_age_days} days)")
        if reasons:
            report.nudges.append(Nudge(name, reasons, planner._session_context_command(contexts[name])))

    if debt_by_file:
        plan = planner.plan(list(debt_by_file), config, markers, level=level, surfaces=None,
                            file_exists=file_exists, debt=debt_by_file)
        owed_now = {s.command for s in planner.run_list(plan, passed_at)}
        report.owed = [s for s in plan.selections if s.action != "run" or s.command in owed_now]
    return report


def _days(age: float) -> str:
    if age < 1:
        return "under a day"
    whole = int(age)
    return f"{whole} day{'s' if whole != 1 else ''}"


def _listing(files: list[str]) -> str:
    shown = ", ".join(files[:LISTED_FILES])
    return shown + (f" (+{len(files) - LISTED_FILES} more)" if len(files) > LISTED_FILES else "")


def render(report: Report, limits: Limits) -> str:
    lines = [f"Verification debt ({report.level} level; advisory, nothing was run)"]
    if not report.debts:
        lines.append("  none: no context has changes since its last recorded pass." if not report.no_record
                     else "  none to report for the contexts that have a recorded pass.")
    for d in report.debts:
        age = f", verified {_days(d.age_days)} ago" if d.age_days is not None else ""
        lines.append(f"  {d.name}: {d.count} file(s) changed since {d.since[:8]}{age}")
        if d.own:
            lines.append(f"      own: {_listing(d.own)}")
        for origin, files in d.inherited.items():
            lines.append(f"      from {origin}: {_listing(files)}")
    if report.owed:
        lines.append("  Tests owed:")
        for s in report.owed:
            tag = "[CONFIRM] " if s.action == "confirm" else ""
            lines.append(f"      {tag}{s.command}    # {s.reason}")
    for n in report.nudges:
        lines.append(f"  Recommended: catch up {n.context} with a context-level run, {' and '.join(n.reasons)}:")
        lines.append("      " + LEDGER_RUN.format(context=n.context, level=report.level, command=n.command))
        lines.append("      (the run records its pass, which clears the debt; this report never runs it)")
    if report.no_record:
        lines.append(f"  No recorded {report.level}-level pass for: {', '.join(report.no_record)}. Nothing to measure drift from, "
                     "so they are not counted. Start a record by running that context's suite through the ledger: "
                     + LEDGER_RUN.format(context="<context>", level=report.level, command="<its test command>"))
    lines.extend(f"  note: {note}" for note in report.notes)
    if limits.max_files or limits.max_age_days:
        parts = []
        if limits.max_files:
            parts.append(f"{limits.max_files} files")
        if limits.max_age_days:
            parts.append(f"{limits.max_age_days} days")
        lines.append(f"  (recommendation limits: {' or '.join(parts)}; scripts/test_planner_config.json, \"debt\")")
    return "\n".join(lines)


def hook_json(text: str) -> str:
    """What a SessionStart hook prints: the report for the owner (`systemMessage`) and for Claude."""
    return json.dumps({
        "systemMessage": text,
        "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text},
    })


def _live_verified_at(context: str, level: str) -> str | None:
    import verification_ledger as vl

    return vl.last_verified_at(context, level)


def main(argv: list[str] | None = None, *, out=print, git=planner.changed_files_from_git,
         verified=planner._live_verified, verified_at=_live_verified_at, ledger=planner._live_ledger,
         now: datetime | None = None) -> int:
    """Always returns 0: a report that cannot be built says so instead of failing."""
    hook = False
    try:
        parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
        parser.add_argument("--hook", action="store_true", help="print the JSON a Claude Code SessionStart hook expects")
        parser.add_argument("--level", choices=planner.LEVELS, help=f"ledger level to measure (default: config, else {DEFAULT_LEVEL})")
        parser.add_argument("--base", default="HEAD", help="ref a context with no recorded pass is measured from")
        parser.add_argument("--max-files", type=int, help="size limit for this run (0 = off)")
        parser.add_argument("--max-age-days", type=int, help="age limit for this run (0 = off)")
        args, _unknown = parser.parse_known_args(argv)  # a hook must not die on a stray argument
        hook = args.hook
        config = planner.load_config()
        level, limits = load_limits(config)
        level = args.level or level
        if args.max_files is not None:
            limits.max_files = args.max_files
        if args.max_age_days is not None:
            limits.max_age_days = args.max_age_days
        try:
            passed_at = ledger()
        except Exception:
            passed_at = lambda command: None  # noqa: E731
        report = build(config, planner.load_markers(), level=level, limits=limits, diff=git, verified=verified,
                       verified_at=verified_at, base=args.base, now=now, passed_at=passed_at)
        text = render(report, limits)
    except SystemExit as exc:  # argparse --help or a usage error: not a reason to fail a session
        if exc.code == 0:
            return 0
        text = "Verification debt report not shown (bad arguments)."
    except Exception as exc:
        text = f"Verification debt report unavailable ({type(exc).__name__}: {exc}). Nothing was run and nothing is blocked."
    out(hook_json(text) if hook else text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
