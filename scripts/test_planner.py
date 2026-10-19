"""Advisory test planner (#60, #61; spec #51): which tests to run for a change.

Reads the changed files, the context config (scripts/test_planner_config.json),
the pytest markers declared in pyproject.toml and, at session end and
release, the External surface manifest, then prints the plan for a level
(rules 2 to 6 of docs/test-audit/rules.md):

  issue    1. any changed test file, first (the issue's own targeted test);
           2. the Minor suite of each touched context;
           3. the Major suite instead when a public interface of that
              context changed, or a dependency file changed;
           4. the interface tests of each changed interface, including the
              sharing contexts' side where the config names one.
  session  the whole file, context or application, by the size of the diff
           (scope ladder); stale surfaces of the touched contexts.
  release  everything for each releasable context (Android, Scan Proxy),
           the Web freshness gate, and every surface of those contexts.

Android instrumented (device) tests are planned only when the diff touches
code they cover, or at release. A stale paid surface is listed as needing
confirmation, never as something to run.

The `slow` pytest tests (tooling checks that start pytest, npm or Gradle; real
photo OCR; the Streamlit walkthrough; the Breakdown sweep) are left out of the
Python suites above and listed on their own, only when the diff touches what
their config group names (`slow` in scripts/test_planner_config.json), and
always at release (#129). A bare `uv run pytest` still runs them all.

Each listed suite is marked `already passed at <tree>` or `run` from the
verification ledger (#128): a suite passes only for the exact tree it ran at,
a dirty tree is never vouched for, and a missing or unreadable ledger means
`run`. A final `To run:` line lists the free suites still owed.

Downstream contexts (#66): a change to an interface's provider side (its `context`)
also queues the contexts in `shares_with`, and a change to a context also queues the
contexts that list it under `depends_on`. At the issue level a downstream context runs
its Major suite (or the interface's own `shares_tests` command where the config gives
one); at session end it runs its context suite. Docs-only changes (`docs_globs`) add
nothing.

`--since-verified` plans each context from the last commit the verification ledger
(#65) holds for it at the chosen level, instead of from --base, so committed but
unverified work is still planned. A context with no ledger entry, or whose recorded
commit git can no longer read, is planned from --base. Each file counts only for the
contexts it changed since their own last verified commit.

Usage: uv run scripts/test_planner.py [--level issue|session|release]
           [--files PATH ...] [--base REF] [--context NAME ...] [--since-verified]
Without --files the changed files come from `git diff --name-only <base>`
(default HEAD). The planner is advisory: it always exits 0.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tomllib
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path, PurePosixPath

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = Path(__file__).resolve().parent / "test_planner_config.json"
PYPROJECT = REPO_ROOT / "pyproject.toml"

LEVELS = ("issue", "session", "release")
DEFAULT_FILE_MAX_FILES = 2
# A second `-m` replaces addopts' `-m "not external"`, so each slow run says it again.
SLOW_PYTEST = 'uv run pytest -n auto -m "slow and not external"'


class GitError(Exception):
    pass


@dataclass
class Selection:
    kind: str  # "targeted" | "minor" | "major" | "interface" | "slow" | "device" | "file" | "context" | "downstream" | "application" | "release" | "gate" | "surface"
    command: str
    reason: str
    action: str = "run"  # "run" | "confirm" (owner confirms first; never run unprompted)
    # Contexts whose files can change this suite's result (#128); empty = unknown, so any change counts.
    contexts: tuple[str, ...] = ()


@dataclass
class Plan:
    level: str = "issue"
    scope: str | None = None  # session level: "file" | "context" | "application"
    selections: list[Selection] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def add(self, selection: Selection) -> None:
        for s in self.selections:
            if s.command == selection.command:
                # One command planned twice (the shared Python application run): it depends on both.
                s.contexts = tuple(dict.fromkeys(s.contexts + selection.contexts)) if s.contexts and selection.contexts else ()
                return
        self.selections.append(selection)


def load_config(path: Path = CONFIG_FILE) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_markers(pyproject: Path = PYPROJECT) -> set[str]:
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    declared = data["tool"]["pytest"]["ini_options"].get("markers", [])
    return {entry.split(":", 1)[0].strip() for entry in declared}


def surfaces_from_manifest(manifest: dict, verdicts) -> list[dict]:
    """Planner input from the External manifest and freshness verdicts."""
    by_name = {v.surface: v for v in verdicts}
    out = []
    for name, entry in manifest["surfaces"].items():
        verdict = by_name.get(name)
        out.append({
            "name": name,
            "state": verdict.state if verdict else "planned",
            "platforms": entry.get("platforms", []),
            "paid": entry.get("max_paid_calls", 0) > 0,
        })
    return out


def _normalise(path: str) -> str:
    return path.replace("\\", "/").removeprefix("./")


def _matches(path: str, patterns: list[str]) -> bool:
    return any(fnmatch(path, p) for p in patterns)


def _owners(path: str, contexts: dict) -> set[str]:
    return {n for n, c in contexts.items() if any(path.startswith(p) for p in c["paths"])}


def _is_python(ctx: dict) -> bool:
    return "marker" in ctx


def _fill(template: str, ctx: dict, path: str) -> str:
    """Fill {file}, {rel}, {fqcn} for a changed path (a source or test file)."""
    root = next((p for p in ctx["paths"] if path.startswith(p)), "")
    rel = path.removeprefix(root)
    fqcn = ""
    if "/java/" in path:
        fqcn = path.split("/java/", 1)[1].rsplit(".", 1)[0].replace("/", ".")
    return template.replace("{file}", path).replace("{rel}", rel).replace("{fqcn}", fqcn)


def _test_for(path: str, ctx: dict, file_exists) -> str | None:
    """The existing test file for a source file, by the context's test_for patterns."""
    p = PurePosixPath(path)
    directory = p.parent.as_posix()
    if ctx.get("dir_rewrite"):
        directory = directory.replace(*ctx["dir_rewrite"])
    for pattern in ctx.get("test_for", []):
        candidate = pattern.replace("{dir}", directory).replace("{stem}", p.stem)
        if file_exists(candidate):
            return candidate
    return None


def _is_test_file(path: str, ctx: dict) -> bool:
    return _matches(path, ctx.get("test_globs", []))


def _is_python_test(path: str) -> bool:
    """A file pytest collects (its default `test_*.py` / `*_test.py`); a helper such as
    tests/_release_test_helpers.py or conftest.py collects nothing, and pytest exits 5 on it."""
    name = PurePosixPath(path).name
    return path.startswith("tests/") and (fnmatch(name, "test_*.py") or fnmatch(name, "*_test.py"))


def _is_docs(path: str, config: dict) -> bool:
    return _matches(path, config.get("docs_globs", []))


def _depends(ctx: dict) -> dict[str, list[str]]:
    """A context's `depends_on` as {context: file globs}: a list of names means any file of that context;
    a mapping narrows it to the globs (the files the dependent really imports)."""
    raw = ctx.get("depends_on", {})
    return {name: [] for name in raw} if isinstance(raw, list) else raw


def _dependents(start: set[str], contexts: dict, path: str | None = None, direct: set[str] | None = None) -> dict[str, str]:
    """Contexts that depend (`depends_on`, transitively) on any of `start`, each with the context it depends
    on. A dependency with globs counts only when `path` matches them and the context depended on is in
    `direct` (the file's own contexts; later hops in the chain are not narrowed by the file)."""
    found: dict[str, str] = {}
    frontier = set(start)
    direct = set(start) if direct is None else direct
    while True:
        new: dict[str, str] = {}
        for name, ctx in contexts.items():
            if name in frontier:
                continue
            for on, globs in _depends(ctx).items():
                if on in frontier and (on not in direct or path is None or not globs or _matches(path, globs)):
                    new[name] = on
                    break
        if not new:
            return found
        found.update(new)
        frontier |= set(new)


def _downstream(owners: set[str], hit: list[dict], contexts: dict, path: str) -> dict[str, str]:
    """Contexts a change to this file queues, with why: the `shares_with` side of each hit
    interface whose provider (`context`) changed, and every context that `depends_on` a changed one."""
    found: dict[str, str] = {}
    for iface in hit:
        if iface["context"] in owners:
            for other in iface.get("shares_with", []):
                if other in contexts and other not in owners:
                    found.setdefault(other, f"downstream of interface {iface['name']}")
    for name, on in _dependents(owners | set(found), contexts, path, direct=owners).items():
        found.setdefault(name, f"depends on {on}")
    return found


def _reaches(path: str, config: dict) -> set[str]:
    """Contexts that need re-verifying when this file changes: its owners, every context sharing an
    interface it belongs to, the contexts a dependency file feeds, and whatever depends on those."""
    contexts = config["contexts"]
    python = {n for n, c in contexts.items() if _is_python(c)}
    reached = _owners(path, contexts)
    direct = set(reached)
    for iface in config["interfaces"]:
        if _matches(path, iface["files"]):
            reached |= ({iface["context"]} | set(iface.get("shares_with", []))) & set(contexts)
    if path in config["dependency_files"] or _is_python_test(path):
        reached |= python
    reached |= {n for n, c in contexts.items() if path in c.get("dependency_files", [])}
    return reached | set(_dependents(reached, contexts, path, direct=direct))


def plan(
    changed_files: list[str],
    config: dict,
    markers: set[str],
    *,
    level: str = "issue",
    surfaces: list[dict] | None = None,
    release_contexts: list[str] | None = None,
    file_exists=None,
    debt: dict[str, set[str]] | None = None,
) -> Plan:
    """`debt` (from --since-verified) maps a changed file to the contexts it is unverified for; a file
    plans nothing for a context outside its set. Without it every changed file counts for every context."""
    file_exists = file_exists or (lambda p: (REPO_ROOT / p).is_file())
    files = [_normalise(f) for f in changed_files]
    result = Plan(level=level)
    if level == "release":
        _plan_release(result, files, config, surfaces, release_contexts)
        return result

    contexts = config["contexts"]
    docs = [f for f in files if _is_docs(f, config)]
    files = [f for f in files if f not in docs]

    def allowed(f: str) -> set[str]:
        return set(contexts) if debt is None else debt.get(f, set())

    python_names = {n for n, c in contexts.items() if _is_python(c)}
    touched: set[str] = set()
    interface_changed: set[str] = set()  # contexts whose public interface changed
    interfaces: list[dict] = []
    interface_debt: dict[str, set[str]] = {}  # interface name -> contexts it is unverified for
    downstream: dict[str, str] = {}  # context -> why it is queued by another's change
    for f in files:
        owners = _owners(f, contexts)
        hit = [i for i in config["interfaces"] if _matches(f, i["files"])]
        for iface in hit:
            if iface not in interfaces:
                interfaces.append(iface)
            interface_debt.setdefault(iface["name"], set()).update(allowed(f))
            if not owners and iface["context"] in contexts:
                owners.add(iface["context"])
        for name, why in _downstream(owners, hit, contexts, f).items():
            if name in allowed(f):
                downstream.setdefault(name, why)
        owners &= allowed(f)
        touched |= owners
        if hit:
            interface_changed |= owners
    downstream = {n: why for n, why in downstream.items() if n not in touched}

    dependency_files = set(config["dependency_files"])
    python_dependency_changed: set[str] = set()  # Python contexts a changed dependency file feeds
    context_dependency_changed: set[str] = set()
    for f in files:
        if f in dependency_files:
            python_dependency_changed |= python_names & allowed(f)
        context_dependency_changed |= {n for n, c in contexts.items()
                                       if f in c.get("dependency_files", []) and n in allowed(f)}
    touched |= python_dependency_changed | context_dependency_changed

    device_touched = [
        n for n, c in contexts.items()
        if "device" in c and any(_matches(f, c.get("device_covered", [])) for f in files if n in allowed(f))
    ]

    for f in files:
        for name, ctx in contexts.items():
            if _matches(f, ctx.get("live_globs", [])):
                result.notes.append(f"{f}: live test; not planned (it runs through the External surface suite)")
                break

    slow_groups = config.get("slow", []) if "slow" in markers else []
    if level == "issue":
        _plan_issue(result, files, config, markers, touched, interface_changed, interfaces,
                    python_dependency_changed, context_dependency_changed, exclude_slow=bool(slow_groups),
                    downstream=downstream, interface_debt=None if debt is None else interface_debt, allowed=allowed)
    else:
        _plan_session(result, files, config, markers, touched, python_dependency_changed,
                      context_dependency_changed, file_exists, surfaces, downstream, allowed)
    _plan_slow(result, [f for f in files if debt is None or allowed(f) & python_names], slow_groups,
               python_touched=any(_is_python(contexts[n]) for n in touched),
               python_names=tuple(n for n, c in contexts.items() if _is_python(c)))

    for name in device_touched:
        ctx = contexts[name]
        result.add(Selection("device", ctx["device"], f"{name}: diff touches code the instrumented tests cover (needs a device)",
                             contexts=(name,)))
    skipped_device = [n for n, c in contexts.items() if "device" in c and n in touched and n not in device_touched]
    for name in skipped_device:
        result.notes.append(f"{name}: instrumented (device) tests excluded; the diff touches no code they cover")

    if not changed_files:
        result.notes.append("no changed files; nothing planned")
    elif docs and not files:
        result.notes.append("docs-only change; no tests planned")
    elif not result.selections and not result.notes:
        result.notes.append("no test context touched; no tests planned")
    return result


def _pytest_marker_run(expression: str, exclude_slow: bool) -> str:
    if exclude_slow:
        return f'uv run pytest -m "{expression} and not slow"'
    return f'uv run pytest -m "{expression}"' if " " in expression else f"uv run pytest -m {expression}"


def _plan_slow(result: Plan, files: list[str], groups: list[dict], *, python_touched: bool, python_names: tuple[str, ...] = ()) -> None:
    """List the slow tests of each group whose triggers the diff touches; say so when none is owed."""
    owed = False
    for group in groups:
        hit = next((f for f in files if _matches(f, group["triggers"])), None)
        if hit is not None:
            owed = True
            result.add(Selection("slow", f"{SLOW_PYTEST} {' '.join(group['tests'])}",
                                 f"slow tests owed: {group['name']} (diff touches {hit})", contexts=python_names))
    if groups and python_touched and not owed:
        result.notes.append("slow tests left out; the diff touches nothing they check (a bare `uv run pytest` runs them)")


def _plan_issue(result, files, config, markers, touched, interface_changed, interfaces,
                python_dependency_changed, context_dependency_changed, exclude_slow=False,
                downstream=None, interface_debt=None, allowed=lambda f: set()) -> None:
    contexts = config["contexts"]
    downstream = downstream or {}
    python_names = {n for n, c in contexts.items() if _is_python(c)}
    for f in files:
        if _is_python_test(f):
            if allowed(f) & python_names:
                result.add(Selection("targeted", f"uv run pytest {f}", "changed test file, runs first"))
            continue
        for name, ctx in contexts.items():
            if (not _is_python(ctx) and _is_test_file(f, ctx) and name in allowed(f)
                    and not _matches(f, ctx.get("live_globs", []))):
                result.add(Selection("targeted", _fill(ctx["file"], ctx, f), "changed test file, runs first"))

    def add_suite(name: str, major: bool, why: str) -> None:
        ctx = contexts[name]
        if _is_python(ctx):
            marker = ctx["marker"]
            missing = ({marker} if major else {marker, "minor"}) - markers
            if missing:
                result.notes.append(f"{name}: marker(s) {sorted(missing)} not declared in pyproject.toml; skipped")
            elif major:
                result.add(Selection("major", _pytest_marker_run(marker, exclude_slow), f"{name} Major ({why}; includes Minor)"))
            else:
                result.add(Selection("minor", _pytest_marker_run(f"minor and {marker}", exclude_slow), f"{name} Minor"))
        elif major:
            result.add(Selection("major", ctx["commands"]["major"], f"{name} Major ({why}; includes Minor)"))
        else:
            result.add(Selection("minor", ctx["commands"]["minor"], f"{name} Minor"))

    def reaches(iface: dict, name: str) -> bool:  # is this interface unverified for the context (always, without --since-verified)
        return interface_debt is None or name in interface_debt.get(iface["name"], set())

    # An interface can name the one test that covers a sharing context's side; that stands in for its Major suite.
    precise = {other for iface in interfaces for other in iface.get("shares_with", [])
               if iface.get("shares_tests", {}).get(other) and reaches(iface, other)}
    for name in contexts:  # config order keeps the output stable
        if name in touched:
            dependency = name in python_dependency_changed or name in context_dependency_changed
            add_suite(name, dependency or name in interface_changed,
                      "dependency changed" if dependency else "public interface changed")
        elif name in downstream and name not in precise:
            add_suite(name, True, downstream[name])

    for iface in interfaces:
        if reaches(iface, iface["context"]):
            for test in iface["tests"]:
                result.add(Selection("interface", f"uv run pytest {test}", f"interface {iface['name']}"))
        outside = []
        for other in iface.get("shares_with", []):
            command = iface.get("shares_tests", {}).get(other)
            if other in contexts and command:
                if reaches(iface, other):
                    result.add(Selection("interface", command, f"interface {iface['name']} ({other} side)"))
            elif other not in contexts:
                outside.append(other)
        if outside:
            result.notes.append(
                f"interface {iface['name']} is shared with {', '.join(outside)}; those contexts' tests are not planned here"
            )


def _plan_session(result, files, config, markers, touched, python_dependency_changed,
                  context_dependency_changed, file_exists, surfaces, downstream=None, allowed=lambda f: set()) -> None:
    """Scope ladder: one small context -> file, one context -> context, several -> application.
    Downstream contexts (#66) add their context run on top; the ladder counts only the contexts the diff touches."""
    contexts = config["contexts"]
    downstream = downstream or {}
    python_names = tuple(n for n, c in contexts.items() if _is_python(c))
    for f in files:
        if _is_python_test(f) and set(python_names) & allowed(f):
            result.add(Selection("file", f"uv run pytest {f}", "changed test file", contexts=python_names))
    if not touched and not downstream:
        return
    file_max = config.get("scope", {}).get("file_max_files", DEFAULT_FILE_MAX_FILES)
    dependency = bool(python_dependency_changed) or bool(context_dependency_changed)
    if not touched:
        result.scope = "context"
    elif len(touched) > 1:
        result.scope = "application"
    elif dependency or sum(1 for f in files if _owners(f, contexts) & allowed(f)) > file_max:
        result.scope = "context"
    else:
        result.scope = "file"

    if result.scope == "application":
        for name, ctx in contexts.items():
            command = ctx.get("application", ctx["context"])
            result.add(Selection("application", command, f"application run ({name}; diff spans {', '.join(sorted(touched))})",
                                 contexts=(name,)))
    elif not touched:
        pass  # only downstream contexts, planned below
    elif result.scope == "context":
        (name,) = touched
        result.add(Selection("context", contexts[name]["context"], f"{name} context run (diff is larger than a file)",
                             contexts=(name,)))
    else:
        (name,) = touched
        ctx = contexts[name]
        planned_any = False
        for f in files:
            if name not in allowed(f) or _matches(f, ctx.get("live_globs", [])):
                continue
            target = f if _is_test_file(f, ctx) or (_is_python(ctx) and _is_python_test(f)) else _test_for(f, ctx, file_exists)
            if target is None:
                if _owners(f, contexts):
                    result.notes.append(f"{name}: no test file found for {f}; running the context instead")
                    result.add(Selection("context", ctx["context"], f"{name} context run (no file-level test for {f})",
                                         contexts=(name,)))
                    planned_any = True
                continue
            result.add(Selection("file", _fill(ctx["file"], ctx, target), f"file run: {target}", contexts=(name,)))
            planned_any = True
        if not planned_any:
            result.add(Selection("context", ctx["context"], f"{name} context run", contexts=(name,)))
    if result.scope != "application":  # an application run already covers every context
        for name in contexts:
            if name in downstream:
                result.add(Selection("downstream", contexts[name]["context"], f"{name} context run ({downstream[name]})",
                                     contexts=(name,)))
    _plan_surfaces(result, config, surfaces, {contexts[n].get("platform") for n in
                   (contexts if result.scope == "application" else touched | set(downstream))})


def _plan_surfaces(result: Plan, config: dict, surfaces: list[dict] | None, platforms: set) -> None:
    """Stale free surfaces run; stale paid surfaces need confirmation, never run."""
    if surfaces is None:
        return
    by_platform = {c["platform"]: c for c in config["contexts"].values() if "platform" in c}
    for surface in surfaces:
        shared = [p for p in surface["platforms"] if p in platforms]
        if not shared or surface["state"] == "fresh":
            continue
        if surface["state"] == "planned":
            result.notes.append(f"surface {surface['name']}: planned, no test yet")
            continue
        runner = next((by_platform[p]["external"] for p in shared if "external" in by_platform.get(p, {})), None)
        command = runner or f"(no wrapper configured for {', '.join(shared)})"
        if surface["paid"]:
            result.add(Selection("surface", command, f"surface {surface['name']} is stale and paid: needs confirmation, not run",
                                 action="confirm"))
        elif runner:
            result.add(Selection("surface", command, f"surface {surface['name']} is stale (free): runs"))
        else:
            result.notes.append(f"surface {surface['name']} is stale but {command}")


def _plan_release(result, files, config, surfaces, release_contexts) -> None:
    contexts = config["contexts"]
    releasable = [n for n, c in contexts.items() if "release" in c or "gate" in c]
    chosen = [n for n in (release_contexts or releasable) if n in contexts]
    for name in release_contexts or []:
        if name not in contexts:
            result.notes.append(f"{name}: not a known context")
        elif name not in releasable:
            result.notes.append(f"{name}: no full-run release; {'covered through the apps that use it' if name == 'core' else 'run the session-end level instead'}")
    for name in chosen:
        ctx = contexts[name]
        for item in ctx.get("release", []):
            confirm = item.get("confirm", False)
            result.add(Selection("release", item["command"],
                                 f"{name} release: {item['reason']}" + ("; confirm before running" if confirm else ""),
                                 action="confirm" if confirm else "run"))
        if "gate" in ctx:
            result.add(Selection("gate", ctx["gate"], f"{name} deploy keeps the External freshness gate (no full run)"))
    if config.get("slow"):
        result.add(Selection("slow", SLOW_PYTEST, "slow tests are always owed at release (tooling checks, real-photo OCR, walkthrough, sweep)"))
    if release_contexts is None:
        result.notes.append("web, streamlit and core have no full-run release; core is covered through the apps that use it")
    platforms = {contexts[n].get("platform") for n in chosen}
    _plan_surfaces(result, config, surfaces, platforms)


@dataclass
class Verdict:
    selection: Selection
    passed_tree: str | None  # the tree the suite already passed at (the current one), else None -> run


def verdicts(result: Plan, passed_at) -> list[Verdict]:
    """Pair each planned suite with the ledger's answer. `passed_at(command)` returns the
    current tree when the suite already passed at it, else None."""
    return [Verdict(s, passed_at(s.command)) for s in result.selections]


def run_list(result: Plan, passed_at) -> list[Selection]:
    """What is left to run: free suites the ledger does not show as passed at this tree."""
    return [v.selection for v in verdicts(result, passed_at) if v.selection.action == "run" and v.passed_tree is None]


# Files that never belong to a context's paths but can still change a suite: tests and the docs and
# skills they read are Python; anything else unowned (shared fixtures, root files) could affect anything.
_PYTHON_ONLY_PREFIXES = ("tests/", "docs/", ".claude/")


def _affected_contexts(path: str, config: dict) -> set[str] | None:
    """Contexts whose suites the file can change; None means every context."""
    contexts = config["contexts"]
    python = {n for n, c in contexts.items() if _is_python(c)}
    hit = _owners(path, contexts)
    direct = set(hit)
    for iface in config.get("interfaces", []):
        if _matches(path, iface["files"]):
            hit |= ({iface["context"]} | set(iface.get("shares_with", []))) & set(contexts)
    if path in config.get("dependency_files", []):
        hit |= python
    if hit:
        hit |= set(_dependents(hit, contexts, path, direct=direct))
        return hit | python if hit & python else hit
    if path.startswith(_PYTHON_ONLY_PREFIXES) or path.endswith(".md"):
        return python
    return None


def suite_affected(selection: Selection, changed: list[str], config: dict) -> bool:
    """Can any of these changed files alter the suite's result? True whenever unsure."""
    if not selection.contexts:
        return True
    contexts = config["contexts"]
    if any(_is_python(contexts[n]) for n in selection.contexts if n in contexts):
        return True  # Python tests read web, Android, fixture and doc files too (wording scans, the tooling checks)
    wanted = set(selection.contexts)
    for path in map(_normalise, changed):
        hit = _affected_contexts(path, config)
        if hit is None or hit & wanted:
            return True
    return False


def plan_since_verified(
    config: dict,
    markers: set[str],
    *,
    level: str,
    diff,
    verified,
    base: str,
    surfaces: list[dict] | None = None,
    file_exists=None,
) -> Plan:
    """Plan each context from the last commit the ledger holds for it at `level` (#66).

    `diff(ref)` lists the files changed from `ref` to the working tree; `verified(context, level)`
    returns the context's last verified commit or None. A context with no commit, or one `diff` cannot
    read, is planned from `base`. A file counts only for the contexts it changed since their own commit."""
    debt: dict[str, set[str]] = {}
    notes: list[str] = []
    cache: dict[str, list[str]] = {}

    def changed_from(ref: str) -> list[str]:
        if ref not in cache:
            cache[ref] = diff(ref)
        return cache[ref]

    for name in config["contexts"]:
        try:
            ref = verified(name, level)
        except Exception as exc:  # an unreadable ledger is the same as nothing verified
            ref = None
            notes.append(f"{name}: ledger unavailable ({exc})")
        source = base
        if ref:
            try:
                changed_from(ref)
                source = ref
            except GitError:
                notes.append(f"{name}: last verified commit {ref[:8]} is not readable; planned from {base}")
        else:
            notes.append(f"{name}: never verified at the {level} level; planned from {base}")
        files = [_normalise(f) for f in changed_from(source)]
        mine = [f for f in files if name in _reaches(f, config)]
        for f in mine:
            debt.setdefault(f, set()).add(name)
        label = source[:8] if source != base else base
        notes.append(f"{name}: " + (f"{len(mine)} file(s) changed since {label}" if mine else f"nothing to verify since {label}"))
    result = plan(list(debt), config, markers, level=level, surfaces=surfaces, file_exists=file_exists, debt=debt)
    result.notes = notes + [n for n in result.notes if n != "no changed files; nothing planned"]
    if not debt:
        result.notes.append("every context is verified up to date; nothing planned")
    return result


def changed_files_from_git(base: str) -> list[str]:
    try:
        out = subprocess.run(
            ["git", "diff", "--name-only", base], cwd=REPO_ROOT, capture_output=True, text=True, check=True
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise GitError(str(exc)) from exc
    return [line for line in out.splitlines() if line.strip()]


def _live_surfaces() -> list[dict] | None:
    """Surface states for session end and release; None (with no surface plan) if unreadable."""
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import external_freshness as ef

    manifest = ef.load_manifest()
    verdicts = ef.evaluate(manifest, ef.load_status(), ef.GitHistory(), ef.fetch_publish_times)
    return surfaces_from_manifest(manifest, verdicts)


def _live_ledger():
    """`passed_at` backed by the verification ledger (#128): the current tree when the suite already
    passed at it. A dirty tree is never vouched for; a missing or unreadable ledger answers "run"."""
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import verification_ledger as vl

    real_git = vl.RealGit()
    if not real_git.is_clean():
        return lambda command: None
    revision = vl.current_revision(real_git)
    return lambda command: revision.tree if vl.suite_verdict(command, revision).skip else None


def _live_verified(context: str, level: str) -> str | None:
    """The ledger's last verified commit for a context at a level (#65)."""
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import verification_ledger as vl

    return vl.last_verified(context, level)


TITLES = {"issue": "Per-issue", "session": "Session-end", "release": "Release"}


def main(argv: list[str] | None = None, *, git=changed_files_from_git, surfaces=_live_surfaces, ledger=_live_ledger,
         verified=_live_verified) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--level", choices=LEVELS, default="issue", help="issue (default), session or release")
    parser.add_argument("--files", nargs="*", help="changed files (default: git diff --name-only)")
    parser.add_argument("--base", default="HEAD", help="git ref to diff against (default HEAD)")
    parser.add_argument("--context", nargs="*", help="release level: limit to these contexts")
    parser.add_argument("--since-verified", action="store_true",
                        help="plan each context from its last verified commit in the ledger instead of --base")
    args = parser.parse_args(argv)

    try:
        notes: list[str] = []
        surface_states = None
        if args.level != "issue":
            try:
                surface_states = surfaces()
            except Exception as exc:
                notes.append(f"surface freshness unavailable ({exc}); surfaces not planned")
        since_verified = args.since_verified
        if since_verified and args.level == "release":
            notes.append("--since-verified ignored: a release plans everything")
            since_verified = False
        elif since_verified and args.files is not None:
            notes.append("--since-verified ignored: --files names the changed files")
            since_verified = False
        if since_verified:
            result = plan_since_verified(load_config(), load_markers(), level=args.level, diff=git,
                                         verified=verified, base=args.base, surfaces=surface_states)
        else:
            files = [] if args.level == "release" and args.files is None else (
                args.files if args.files is not None else git(args.base))
            result = plan(files, load_config(), load_markers(), level=args.level,
                          surfaces=surface_states, release_contexts=args.context)
        result.notes.extend(notes)
    except Exception as exc:  # advisory: never block
        print(f"Planner could not plan ({exc}); no tests planned. git or config problems never block.")
        return 0

    try:
        passed_at = ledger()
    except Exception as exc:  # advisory: no ledger means every suite is "run"
        passed_at = lambda command: None  # noqa: E731
        result.notes.append(f"ledger unavailable ({exc}); every suite is marked run")

    scope = f", scope: {result.scope}" if result.scope else ""
    print(f"{TITLES[args.level]} test plan (advisory{scope})")
    for i, v in enumerate(verdicts(result, passed_at), 1):
        sel = v.selection
        tag = "" if sel.action == "run" else f"[{sel.action.upper()}] "
        verdict = f"already passed at {v.passed_tree[:8]}" if v.passed_tree else "run"
        print(f"  {i}. {tag}{sel.command}    # {sel.reason}    -> {verdict}")
    for note in result.notes:
        print(f"  note: {note}")
    remaining = run_list(result, passed_at)
    if result.selections:
        print("To run: " + ("; ".join(s.command for s in remaining) if remaining else "nothing (every free suite already passed at this tree)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
