"""Makes a brand-new git worktree test-ready in one step (#83).

A fresh worktree holds only tracked files, so everything gitignored is
missing: the Python virtual environment, the Web and Scan Proxy
`node_modules`, and local-only config such as `web/.env.local`. This installs
the first three from their lockfiles and reports on the last. After it, the
offline suites (`uv run pytest`, `npm --prefix web test`,
`npm --prefix workers/scan-proxy test`) pass without a live or paid call.

Usage (from inside the new worktree):
    uv run scripts/worktree_setup.py                 # install + report
    uv run scripts/worktree_setup.py --copy-env      # also copy missing local-only
                                                     # files from the main checkout

Everything it touches is inside the worktree. It never prints a local-only
file's contents, never overwrites one that is already there, and never writes
one into a tracked path (they are gitignored by `*.local`). Steps are
idempotent: re-running it on a set-up worktree just re-syncs.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Step:
    name: str
    cwd: Path
    command: list[str]


@dataclass(frozen=True)
class LocalFile:
    path: str  # relative to the worktree root, forward slashes
    needed_by: str


@dataclass(frozen=True)
class LocalFileStatus:
    path: str
    present: bool
    needed_by: str


# Gitignored files a worktree does not inherit and that some suite reads.
# None of them are needed by the offline runs.
LOCAL_FILES = [
    LocalFile(
        "web/.env.local",
        "External suites only (Web `test:external`, Scan Proxy live suites): "
        "test-user credentials and the public VITE_* values. No offline suite reads it.",
    ),
]


def plan_steps(root: Path) -> list[Step]:
    return [
        Step("Python environment", root, ["uv", "sync"]),
        Step("Web dependencies", root / "web", ["npm", "ci"]),
        Step("Scan Proxy dependencies", root / "workers" / "scan-proxy", ["npm", "ci"]),
    ]


def local_file_status(root: Path) -> list[LocalFileStatus]:
    return [LocalFileStatus(f.path, (root / f.path).is_file(), f.needed_by) for f in LOCAL_FILES]


def copy_local_files(src_root: Path, dst_root: Path) -> list[str]:
    """Copies each local-only file the source has and the destination lacks.

    Never overwrites. Returns the relative paths copied, never any contents.
    """
    copied = []
    for f in LOCAL_FILES:
        src, dst = src_root / f.path, dst_root / f.path
        if src.is_file() and not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            copied.append(f.path)
    return copied


def main_checkout_from(git_common_dir: Path) -> Path:
    """The main checkout is the parent of the git dir every worktree shares."""
    return git_common_dir.parent


def find_main_checkout(root: Path) -> Path | None:
    result = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        cwd=root, capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    main = main_checkout_from(Path(result.stdout.strip()))
    return None if main.resolve() == root.resolve() else main


def _run_step(step: Step) -> int:
    # npm is npm.cmd on Windows; subprocess needs the resolved name.
    executable = shutil.which(step.command[0]) or step.command[0]
    return subprocess.run([executable, *step.command[1:]], cwd=step.cwd).returncode


def run(root: Path, *, runner: Callable[[Step], int] = _run_step, copy_from: Path | None) -> int:
    for step in plan_steps(root):
        print(f"==> {step.name}: {' '.join(step.command)}  (in {step.cwd.relative_to(root)})")
        code = runner(step)
        if code != 0:
            print(f"FAILED: {step.name} exited {code}. Nothing after it was run.", file=sys.stderr)
            return code

    if copy_from is not None:
        for path in copy_local_files(copy_from, root):
            print(f"copied {path} from the main checkout")

    print("\nLocal-only files (gitignored, not carried into a worktree):")
    for status in local_file_status(root):
        print(f"  {status.path}: {'present' if status.present else 'MISSING'} - {status.needed_by}")
    print("\nOffline suites are ready: uv run pytest | npm --prefix web test | npm --prefix workers/scan-proxy test")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--copy-env",
        action="store_true",
        help="copy missing local-only files (e.g. web/.env.local) from the main checkout; never overwrites",
    )
    args = parser.parse_args(argv)

    copy_from = None
    if args.copy_env:
        copy_from = find_main_checkout(ROOT)
        if copy_from is None:
            print("--copy-env: could not find a separate main checkout; nothing copied.", file=sys.stderr)
    return run(ROOT, copy_from=copy_from)


if __name__ == "__main__":
    sys.exit(main())
