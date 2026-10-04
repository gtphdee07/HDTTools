"""Reports which External-test surfaces are fresh or stale (ADR-0008).

A surface is one provider interface (e.g. "supabase-auth"). It is stale
when it has never passed, its last run failed, a boundary file or
dependency pin differs from the commit recorded at its last pass, a newer
STABLE release of a watched package was published after that pass, or a
registry could not be reached. "planned" surfaces are listed but never
block. A recorded "skipped" run never counts as a pass.

Usage: uv run scripts/external_freshness.py [--json] [--surface NAME]...
                                            [--platform NAME]
Exit code is 1 when any active surface is stale, so a release gate can
call this directly; it only reads git, the status file and the registries.

Manifest: scripts/external_manifest/surfaces/<name>.json, one file per
surface so parallel branches adding surfaces never edit the same file.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_DIR = Path(__file__).resolve().parent / "external_manifest"
STATUS_FILE = Path(__file__).resolve().parent / "dashboard_data" / "external_status.json"

_STABLE_VERSION = re.compile(r"^\d+\.\d+\.\d+$")


class GitError(Exception):
    pass


class RegistryError(Exception):
    pass


@dataclass
class Verdict:
    surface: str
    state: str  # "fresh" | "stale" | "planned"
    reasons: list[str] = field(default_factory=list)
    versions: dict[str, str] = field(default_factory=dict)

    @property
    def blocking(self) -> bool:
        return self.state == "stale"


def load_manifest(manifest_dir: Path = MANIFEST_DIR) -> dict:
    surfaces: dict[str, dict] = {}
    for path in sorted((manifest_dir / "surfaces").glob("*.json")):
        entry = json.loads(path.read_text(encoding="utf-8"))
        if entry.get("name") != path.stem:
            raise ValueError(f"{path.name}: surface name {entry.get('name')!r} must match the filename")
        surfaces[entry["name"]] = entry
    return {"surfaces": surfaces}


def surfaces_for_platform(manifest: dict, platform: str) -> list[str]:
    return [n for n, s in manifest["surfaces"].items() if platform in s.get("platforms", [])]


def _default_opener(url: str, timeout: float) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.read()


def fetch_npm_times(package: str, *, opener=_default_opener, timeout: float = 20) -> dict[str, str]:
    url = "https://registry.npmjs.org/" + package.replace("/", "%2F")
    try:
        return json.loads(opener(url, timeout))["time"]
    except Exception as exc:
        raise RegistryError(f"npm registry lookup for {package} failed: {exc}") from exc


_FETCHERS = {"npm": fetch_npm_times}


def fetch_publish_times(ecosystem: str, package: str) -> dict[str, str]:
    fetcher = _FETCHERS.get(ecosystem)
    if fetcher is None:
        raise RegistryError(f"no registry fetcher for ecosystem {ecosystem!r}")
    return fetcher(package)


class GitHistory:
    def changed_since(self, sha: str, paths: list[str]) -> list[str]:
        # Diff against the working tree so uncommitted edits to a boundary file count too.
        proc = subprocess.run(
            ["git", "diff", "--name-only", sha, "--", *paths],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        if proc.returncode != 0:
            raise GitError(proc.stderr.strip() or f"git diff against {sha} failed")
        return [line for line in proc.stdout.splitlines() if line]


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def _stable_versions(times: dict[str, str]) -> dict[str, str]:
    return {v: t for v, t in times.items() if _STABLE_VERSION.match(v)}


def _semver_key(version: str) -> tuple[int, ...]:
    return tuple(int(p) for p in version.split("."))


def _last_pass(status: dict, name: str) -> dict | None:
    entry = status.get("surfaces", {}).get(name)
    if entry and entry.get("result") == "pass":
        return entry
    return None


def _evaluate_one(surface: dict, status: dict, git, registry) -> Verdict:
    name = surface["name"]
    if surface.get("status") == "planned":
        return Verdict(name, "planned")

    reasons: list[str] = []
    versions: dict[str, str] = {}
    entry = status.get("surfaces", {}).get(name)
    last_pass = _last_pass(status, name)

    if last_pass is None:
        if entry and entry.get("result") == "fail":
            reasons.append("last run failed")
        else:
            reasons.append("never passed")
    else:
        paths = [*surface.get("boundary_files", []), *surface.get("dependency_pins", [])]
        try:
            if not last_pass.get("commit"):
                raise GitError("pass has no commit recorded")
            changed = git.changed_since(last_pass["commit"], paths)
        except GitError as exc:
            reasons.append(f"recorded commit unusable: {exc}")
        else:
            if changed:
                reasons.append("changed since last pass: " + ", ".join(changed))

    for pkg in surface.get("registry_packages", []):
        try:
            stable = _stable_versions(registry(pkg["ecosystem"], pkg["package"]))
        except RegistryError as exc:
            reasons.append(f"registry unreachable: {exc}")
            continue
        if stable:
            versions[pkg["package"]] = max(stable, key=_semver_key)
        if last_pass is not None:
            cutoff = _parse(last_pass["timestamp"])
            newer = sorted((v for v, t in stable.items() if _parse(t) > cutoff), key=_semver_key)
            if newer:
                reasons.append(f"{pkg['package']} published after last pass: " + ", ".join(newer))

    return Verdict(name, "stale" if reasons else "fresh", reasons, versions)


def evaluate(manifest: dict, status: dict, git, registry, only: list[str] | None = None) -> list[Verdict]:
    names = [n for n in manifest["surfaces"] if only is None or n in only]
    return [_evaluate_one(manifest["surfaces"][n], status, git, registry) for n in names]


def load_status(status_file: Path = STATUS_FILE) -> dict:
    if not status_file.exists():
        return {}
    return json.loads(status_file.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None, *, git=None, registry=None, status_file: Path | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--surface", action="append", help="limit to this surface (repeatable)")
    parser.add_argument("--platform", help="limit to the surfaces in this platform's dependency chain")
    args = parser.parse_args(argv)

    manifest = load_manifest()
    only = args.surface
    if args.platform:
        chain = surfaces_for_platform(manifest, args.platform)
        only = chain if only is None else [n for n in only if n in chain]

    verdicts = evaluate(
        manifest,
        load_status(status_file or STATUS_FILE),
        git or GitHistory(),
        registry or fetch_publish_times,
        only,
    )
    stale = [v.surface for v in verdicts if v.blocking]

    if args.json:
        print(json.dumps({
            "surfaces": {
                v.surface: {"state": v.state, "reasons": v.reasons, "versions": v.versions}
                for v in verdicts
            },
            "stale": stale,
        }, indent=2))
    else:
        for v in verdicts:
            suffix = f": {'; '.join(v.reasons)}" if v.reasons else ""
            note = " (planned, not blocking)" if v.state == "planned" else ""
            print(f"{v.surface}: {v.state}{note}{suffix}")
    return 1 if stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
