"""The External-test release gate (ADR-0008, #43).

A release needs every surface in its platform's dependency chain to be fresh
(scripts/external_freshness.py decides that from the recorded status, git and
the package registries; Android's chain includes the Worker's surfaces). The
gate only reads that status. It never runs a live test. It blocks on a stale,
failed, skipped or never-run surface and when a registry cannot be reached;
planned surfaces never block.

Three places run it:
  - the git pre-push hook (.githooks/pre-push), for a push to MPSkills (Pages'
    production branch) whose diff touches web/, workers/scan-proxy/ or android/;
    a docs-only push passes without contacting a registry
  - the Worker deploy wrapper (scripts/scan_proxy_deploy.py, `npm run deploy`)
  - the Worker and Android release commands (scripts/scan_proxy_release.py,
    scripts/android_release.py), before the step that deploys

Forcing it needs a reason: `--force --reason TEXT` on the commands above, or
EXTERNAL_GATE_FORCE_REASON="TEXT" in the environment (git passes a hook no
flags). The reason is recorded on each surface that was blocking and the
dashboard shows an overridden gate until that surface's next real pass.
`git push --no-verify` skips the hook entirely and records nothing; that is a
deliberate act, not an accident.

Usage:
    uv run scripts/external_gate.py check --platform android [--platform scan-proxy] [--force --reason TEXT]
    uv run scripts/external_gate.py pre-push REMOTE URL      (git runs this; ref lines arrive on stdin)
Exit code 1 means blocked.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, Iterator, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parent))
import external_freshness as ef  # noqa: E402
import record_external_result  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
FORCE_ENV = "EXTERNAL_GATE_FORCE_REASON"
GATED_BRANCH_REF = "refs/heads/MPSkills"
ZERO_SHA = "0" * 40

# A push is gated for the platform whose directory its diff touches, in this order.
GATED_DIRECTORIES = (("web/", "web"), ("workers/scan-proxy/", "scan-proxy"), ("android/", "android"))
ALL_GATED_PLATFORMS = [platform for _, platform in GATED_DIRECTORIES]


def platforms_for_paths(paths: list[str]) -> list[str]:
    return [platform for prefix, platform in GATED_DIRECTORIES if any(p.startswith(prefix) for p in paths)]


def gate(
    platforms: list[str],
    *,
    force_reason: str | None = None,
    out: Callable[[str], None] = print,
    manifest: dict | None = None,
    status: dict | None = None,
    git=None,
    registry=None,
    record: Callable[[list[str], str], object] | None = None,
) -> int:
    """0 when every surface in the platforms' chains is fresh (or the gate was forced with a reason); 1 when blocked."""
    manifest = manifest or ef.load_manifest()
    chain = sorted({n for p in platforms for n in ef.surfaces_for_platform(manifest, p)})
    verdicts = ef.evaluate(
        manifest,
        ef.load_status() if status is None else status,
        git or ef.GitHistory(),
        registry or ef.fetch_publish_times,
        chain,
    )
    blocked = [v for v in verdicts if v.blocking]
    scope = ", ".join(platforms)
    if not blocked:
        out(f"External gate ({scope}): {len(verdicts)} surface(s) checked, none stale.")
        return 0

    out(f"External gate ({scope}): {len(blocked)} surface(s) stale.")
    for v in blocked:
        out(f"  - {v.surface}: {'; '.join(v.reasons)}")

    if force_reason:
        (record or record_external_result.record_override)([v.surface for v in blocked], force_reason)
        out(f"External gate OVERRIDDEN: {force_reason!r}. Recorded on {', '.join(v.surface for v in blocked)}; "
            "the dashboard shows an overridden gate until each one's next real pass.")
        return 0

    out(
        "Run the External suite that covers each one (web\\test-external.ps1, workers\\scan-proxy\\test-external.ps1; "
        "`uv run scripts/external_freshness.py` lists the same surfaces), then try again.\n"
        f'To go ahead anyway, give a reason: {FORCE_ENV}="why" in the environment (or --force --reason "why" on the '
        "release and deploy commands). It is recorded and shown on the dashboard as an overridden gate.\n"
        "`git push --no-verify` skips the pre-push hook entirely and records nothing."
    )
    return 1


# --- forcing it with a reason ----------------------------------------------------------------


def add_force_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--force", action="store_true", help="go ahead past a blocked gate (needs --reason)")
    parser.add_argument("--reason", help="why the gate is being forced; recorded on the dashboard")


def force_reason(args: argparse.Namespace, parser: argparse.ArgumentParser, environ: Mapping[str, str]) -> str | None:
    """The reason the gate is being forced, or None. --force without a reason (or a reason without --force) is an error."""
    reason = (getattr(args, "reason", None) or "").strip()
    forced = getattr(args, "force", False)
    if forced and not reason:
        parser.error("--force needs --reason TEXT: say why the gate is being forced")
    if reason and not forced:
        parser.error("--reason only goes with --force")
    if forced:
        return reason
    return (environ.get(FORCE_ENV) or "").strip() or None


@contextlib.contextmanager
def exported_force(reason: str | None) -> Iterator[None]:
    """Makes the force reason visible to child processes (the deploy gate inside a release run)."""
    previous = os.environ.get(FORCE_ENV)
    if reason:
        os.environ[FORCE_ENV] = reason
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(FORCE_ENV, None)
        else:
            os.environ[FORCE_ENV] = previous


# --- the pre-push hook -----------------------------------------------------------------------


class GitPush:
    """The files a push would change on the remote, from git."""

    def __init__(self, cwd: Path = REPO_ROOT):
        self.cwd = cwd

    def _lines(self, *args: str) -> list[str] | None:
        proc = subprocess.run(["git", *args], cwd=self.cwd, capture_output=True, text=True)
        return [line for line in proc.stdout.splitlines() if line] if proc.returncode == 0 else None

    def changed_paths(self, remote_sha: str, local_sha: str) -> list[str] | None:
        """None when the diff cannot be computed (a remote commit this clone lacks)."""
        if remote_sha == ZERO_SHA:  # the remote has no such branch: everything is new
            return self._lines("ls-tree", "-r", "--name-only", local_sha)
        # --no-renames: a file moved out of web/ must still list its old path there.
        return self._lines("diff", "--name-only", "--no-renames", remote_sha, local_sha)


def pre_push(
    stdin_text: str,
    *,
    changed_paths: Callable[[str, str], list[str] | None],
    gate: Callable[[list[str]], int],
) -> int:
    """Gates a push of MPSkills that touches web/, workers/scan-proxy/ or android/. Every other push passes."""
    platforms: set[str] = set()
    for line in stdin_text.splitlines():
        parts = line.split()
        if len(parts) != 4:
            continue
        _local_ref, local_sha, remote_ref, remote_sha = parts
        if remote_ref != GATED_BRANCH_REF or local_sha == ZERO_SHA:
            continue
        paths = changed_paths(remote_sha, local_sha)
        # Cannot tell what changed: gate everything rather than let a push through unchecked.
        platforms.update(ALL_GATED_PLATFORMS if paths is None else platforms_for_paths(paths))
    if not platforms:
        return 0
    return gate([p for p in ALL_GATED_PLATFORMS if p in platforms])


def main(argv: list[str] | None = None, *, stdin=None, environ: Mapping[str, str] | None = None) -> int:
    environ = os.environ if environ is None else environ
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="check the chains of the given platforms")
    check.add_argument("--platform", action="append", required=True)
    add_force_arguments(check)
    push = commands.add_parser("pre-push", help="the git pre-push hook")
    push.add_argument("remote", nargs="?")
    push.add_argument("url", nargs="?")
    args = parser.parse_args(argv)

    reason = force_reason(args, parser, environ)
    if args.command == "check":
        return gate(args.platform, force_reason=reason)

    def report(message: str) -> None:  # a hook's stderr reaches the person pushing
        print(message, file=sys.stderr)

    return pre_push(
        (stdin or sys.stdin).read(),
        changed_paths=GitPush().changed_paths,
        gate=lambda platforms: gate(platforms, force_reason=reason, out=report),
    )


if __name__ == "__main__":
    raise SystemExit(main())
