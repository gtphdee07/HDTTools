"""Moves the release branch to a chosen MPSkills commit (#175).

Cloudflare Pages publishes Web from the `release` branch, not from MPSkills, so a push of
MPSkills only makes a preview and cannot change the live site. This command is the deliberate
way to change it: it fast-forwards `release` on origin to a commit that is on MPSkills.

What it refuses (nothing is pushed in any of these):
  - a commit that is not on MPSkills
  - a move that is not a fast-forward (it never rewrites `release`, and never forces a push)
  - a `release` branch that does not exist on origin yet, unless --create is given
  - a run that nobody confirmed: it asks `Push? [y/N]` on a terminal, and without one
    it stops after printing the plan unless --yes is given

Before it asks, it prints what goes live: the files under web/ that differ between the
release branch's current tip and the commit, or that nothing under web/ changed.

The push is an ordinary `git push`, so the pre-push hook runs and gates it (a push of the
release branch is the one the External release gate guards; scripts/external_gate.py). Run it
from the checkout that has MPSkills checked out: the gate judges that checkout's status file.

Usage:
    uv run scripts/promote_release.py [COMMIT] [--create] [--yes] [--remote origin]
COMMIT defaults to the tip of MPSkills. Exit codes: 0 pushed (or already there), 1 refused,
2 not confirmed.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
from external_gate import RELEASE_BRANCH, ZERO_SHA  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_BRANCH = "MPSkills"
WEB_PREFIX = "web/"
SHOWN_FILES = 40


class Git:
    """Runs git in one repository; every call returns (exit code, stdout lines)."""

    def __init__(self, cwd: Path = REPO_ROOT):
        self.cwd = cwd

    def run(self, *args: str) -> tuple[int, list[str]]:
        proc = subprocess.run(["git", *args], cwd=self.cwd, capture_output=True, text=True)
        return proc.returncode, [line for line in proc.stdout.splitlines() if line]

    def one(self, *args: str) -> str | None:
        code, lines = self.run(*args)
        return lines[0] if code == 0 and lines else None

    def is_ancestor(self, older: str, newer: str) -> bool:
        return self.run("merge-base", "--is-ancestor", older, newer)[0] == 0


def remote_release_tip(git: Git, remote: str) -> tuple[str | None, str | None]:
    """(tip sha or ZERO_SHA when the branch is absent, error). Asks the remote itself, then fetches the commit."""
    code, lines = git.run("ls-remote", "--heads", remote, f"refs/heads/{RELEASE_BRANCH}")
    if code != 0:
        return None, f"could not read {remote}'s {RELEASE_BRANCH} branch (git ls-remote failed)"
    if not lines:
        return ZERO_SHA, None
    tip = lines[0].split()[0]
    if git.run("cat-file", "-e", f"{tip}^{{commit}}")[0] != 0:
        git.run("fetch", "--quiet", remote, f"refs/heads/{RELEASE_BRANCH}")
        if git.run("cat-file", "-e", f"{tip}^{{commit}}")[0] != 0:
            return None, f"{remote}'s {RELEASE_BRANCH} tip {tip[:9]} is not in this clone and could not be fetched"
    return tip, None


def promote(
    commit: str,
    *,
    git: Git,
    remote: str = "origin",
    create: bool = False,
    yes: bool = False,
    ask: Callable[[str], str] | None = None,
    out: Callable[[str], None] = print,
) -> int:
    """0 pushed or already there, 1 refused, 2 not confirmed. `ask` is None when nobody can answer."""
    sha = git.one("rev-parse", "--verify", "--quiet", f"{commit}^{{commit}}")
    if sha is None:
        out(f"Refused: {commit!r} is not a commit in this repository.")
        return 1
    if git.run("rev-parse", "--verify", "--quiet", f"refs/heads/{SOURCE_BRANCH}")[0] != 0:
        out(f"Refused: there is no local {SOURCE_BRANCH} branch to check the commit against.")
        return 1
    if not git.is_ancestor(sha, f"refs/heads/{SOURCE_BRANCH}"):
        out(f"Refused: {sha[:9]} is not on {SOURCE_BRANCH}. Only a {SOURCE_BRANCH} commit can go live.")
        return 1

    tip, error = remote_release_tip(git, remote)
    if tip is None:
        out(f"Refused: {error}.")
        return 1
    creating = tip == ZERO_SHA
    if creating and not create:
        out(f"Refused: {remote} has no {RELEASE_BRANCH} branch yet. Pass --create to make it at {sha[:9]}.")
        return 1
    if not creating and tip == sha:
        out(f"{RELEASE_BRANCH} on {remote} is already at {sha[:9]}. Nothing to do.")
        return 0
    if not creating and not git.is_ancestor(tip, sha):
        out(
            f"Refused: moving {RELEASE_BRANCH} from {tip[:9]} to {sha[:9]} is not a fast-forward, which would rewrite "
            f"{RELEASE_BRANCH}. This command never does that."
        )
        return 1

    subject = git.one("log", "-1", "--format=%s", sha) or ""
    out(f"Promote {sha[:9]} ({subject}) to {remote}/{RELEASE_BRANCH}.")
    if creating:
        out(
            f"{RELEASE_BRANCH} does not exist on {remote}: this creates it (the External gate then checks the whole tree). "
            "Nothing goes live until Pages' production branch is set to it."
        )
    else:
        code, files = git.run("diff", "--name-only", "--no-renames", tip, sha, "--", WEB_PREFIX)
        if code != 0:
            out(f"Refused: could not list the files that differ under {WEB_PREFIX} (git diff failed).")
            return 1
        if files:
            out(f"{len(files)} file(s) under {WEB_PREFIX} differ from the live tip {tip[:9]} and go live:")
            for name in files[:SHOWN_FILES]:
                out(f"  {name}")
            if len(files) > SHOWN_FILES:
                out(f"  ... and {len(files) - SHOWN_FILES} more")
        else:
            out(f"Nothing under {WEB_PREFIX} changed since {tip[:9]}: the live site stays the same.")

    if not yes:
        answer = ask("Push? [y/N] ") if ask else None
        if answer is None:
            out("Not pushed: nobody confirmed. Run it in a terminal, or pass --yes once the plan above is right.")
            return 2
        if answer.strip().lower() not in ("y", "yes"):
            out("Not pushed.")
            return 2

    # A plain push, no force: git itself refuses a non-fast-forward, and the pre-push hook gates it.
    proc = subprocess.run(["git", "push", remote, f"{sha}:refs/heads/{RELEASE_BRANCH}"], cwd=git.cwd)
    if proc.returncode != 0:
        out(f"Push failed (exit {proc.returncode}); {RELEASE_BRANCH} is unchanged.")
        return 1
    out(f"{remote}/{RELEASE_BRANCH} is now at {sha[:9]}.")
    return 0


def main(argv: list[str] | None = None, *, git: Git | None = None, stdin=None, out=print) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("commit", nargs="?", default=SOURCE_BRANCH, help=f"a {SOURCE_BRANCH} commit (default: its tip)")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--create", action="store_true", help=f"allow creating {RELEASE_BRANCH} on the remote")
    parser.add_argument("--yes", action="store_true", help="push without asking (after reading the plan)")
    args = parser.parse_args(argv)
    stream = stdin or sys.stdin
    ask = (lambda prompt: input(prompt)) if stream.isatty() else None
    return promote(
        args.commit, git=git or Git(), remote=args.remote, create=args.create, yes=args.yes, ask=ask, out=out
    )


if __name__ == "__main__":
    raise SystemExit(main())
