"""Function tests for scripts/external_gate.py (ADR-0008 release gate, #43): the verdict
from fake manifest, status and registry data, the force-with-a-reason override, and which
pushes are gated. Nothing here touches the network or the real status file."""

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.minor]

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))
for _name in ("external_freshness", "record_external_result", "external_gate"):
    _spec = importlib.util.spec_from_file_location(_name, _SCRIPTS / f"{_name}.py")
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[_name] = _module
    _spec.loader.exec_module(_module)

ef = sys.modules["external_freshness"]
eg = sys.modules["external_gate"]

PASS_TS = "2026-10-01T12:00:00Z"
ZERO = "0" * 40

MANIFEST = {
    "surfaces": {
        "web-auth": {
            "name": "web-auth", "status": "active", "platforms": ["web"],
            "boundary_files": ["web/src/auth.tsx"], "dependency_pins": [], "registry_packages": [],
        },
        "worker": {
            "name": "worker", "status": "active", "platforms": ["scan-proxy", "android", "web"],
            "boundary_files": ["workers/scan-proxy/src/index.ts"], "dependency_pins": [],
            "registry_packages": [{"ecosystem": "npm", "package": "wrangler"}],
        },
        "play-billing": {
            "name": "play-billing", "status": "planned", "platforms": ["android"],
            "boundary_files": [], "dependency_pins": [], "registry_packages": [],
        },
        "streamlit-only": {
            "name": "streamlit-only", "status": "active", "platforms": ["streamlit"],
            "boundary_files": [], "dependency_pins": [], "registry_packages": [],
        },
    }
}


def passed(sha="abc"):
    return {"result": "pass", "passed": True, "timestamp": PASS_TS, "commit": sha, "versions": {}}


ALL_FRESH = {"surfaces": {"web-auth": passed(), "worker": passed(), "streamlit-only": passed()}}
QUIET_REGISTRY = {"wrangler": {"4.0.0": "2026-09-01T00:00:00Z", "created": "2020-01-01T00:00:00Z"}}


class FakeGit:
    def __init__(self, changed=()):
        self.changed = list(changed)

    def changed_since(self, sha, paths):
        return [p for p in self.changed if p in paths]


class FakeRegistry:
    def __init__(self, times=None, down=False):
        self.times, self.down, self.calls = times or QUIET_REGISTRY, down, 0

    def __call__(self, ecosystem, package):
        self.calls += 1
        if self.down:
            raise ef.RegistryError("unreachable")
        return self.times[package]


def run_gate(platforms, status=ALL_FRESH, *, git=None, registry=None, force_reason=None):
    out, recorded = [], []
    code = eg.gate(
        platforms,
        force_reason=force_reason,
        out=out.append,
        manifest=MANIFEST,
        status=status,
        git=git or FakeGit(),
        registry=registry or FakeRegistry(),
        record=lambda surfaces, reason: recorded.append((surfaces, reason)),
    )
    return code, "\n".join(out), recorded


# --- the verdict -----------------------------------------------------------------------------


def test_every_surface_in_the_chain_fresh_passes():
    code, _, recorded = run_gate(["web"])

    assert code == 0
    assert recorded == []


def test_a_surface_changed_since_its_last_pass_blocks_and_is_named():
    code, out, _ = run_gate(["web"], git=FakeGit(changed=["web/src/auth.tsx"]))

    assert code == 1
    assert "web-auth" in out and "web/src/auth.tsx" in out


@pytest.mark.parametrize(
    "entry",
    [
        {"result": "fail", "passed": False, "timestamp": PASS_TS, "commit": "abc", "versions": {}},
        {"result": "skipped", "passed": False, "timestamp": PASS_TS, "commit": "abc", "versions": {}},
        None,
    ],
    ids=["failed", "only-skipped", "never-run"],
)
def test_a_failed_skipped_or_never_run_surface_blocks(entry):
    status = {"surfaces": {**ALL_FRESH["surfaces"]}}
    if entry is None:
        del status["surfaces"]["web-auth"]
    else:
        status["surfaces"]["web-auth"] = entry

    code, out, _ = run_gate(["web"], status)

    assert code == 1
    assert "web-auth" in out


def test_an_unreachable_registry_blocks_even_when_everything_else_is_fresh():
    code, out, _ = run_gate(["scan-proxy"], registry=FakeRegistry(down=True))

    assert code == 1
    assert "registry" in out


def test_a_new_stable_release_of_a_watched_package_blocks():
    newer = {"wrangler": {"4.1.0": "2026-10-10T00:00:00Z", "created": "2020-01-01T00:00:00Z"}}

    code, out, _ = run_gate(["scan-proxy"], registry=FakeRegistry(newer))

    assert code == 1
    assert "wrangler" in out and "4.1.0" in out


def test_a_planned_surface_never_blocks_even_with_no_record():
    # play-billing is planned and has no status entry at all.
    code, _, _ = run_gate(["android"])

    assert code == 0


def test_androids_gate_includes_the_workers_surfaces():
    status = {"surfaces": {**ALL_FRESH["surfaces"], "worker": passed("old")}}

    code, out, _ = run_gate(["android"], status, git=FakeGit(changed=["workers/scan-proxy/src/index.ts"]))

    assert code == 1
    assert "worker" in out


def test_a_stale_surface_outside_the_chain_does_not_block():
    status = {"surfaces": {**ALL_FRESH["surfaces"]}}
    del status["surfaces"]["streamlit-only"]  # never run, but not in web's or android's chain

    assert run_gate(["web"], status)[0] == 0
    assert run_gate(["android"], status)[0] == 0


def test_the_report_says_how_to_unlock_the_gate():
    _, out, _ = run_gate(["web"], git=FakeGit(changed=["web/src/auth.tsx"]))

    assert eg.FORCE_ENV in out
    assert "--no-verify" in out


# --- forcing it with a reason ----------------------------------------------------------------


def test_forcing_with_a_reason_passes_and_marks_only_the_blocked_surfaces():
    code, out, recorded = run_gate(
        ["android"], git=FakeGit(changed=["workers/scan-proxy/src/index.ts"]), force_reason="hotfix for a crash"
    )

    assert code == 0
    assert recorded == [(["worker"], "hotfix for a crash")]
    assert "OVERRIDDEN" in out and "hotfix for a crash" in out


def test_forcing_a_gate_that_would_have_passed_records_nothing():
    code, _, recorded = run_gate(["web"], force_reason="just in case")

    assert code == 0
    assert recorded == []


def _parse(argv, env=None):
    parser = argparse.ArgumentParser()
    eg.add_force_arguments(parser)
    return eg.force_reason(parser.parse_args(argv), parser, env or {})


def test_force_needs_a_reason_and_a_reason_needs_force():
    assert _parse([]) is None
    assert _parse(["--force", "--reason", "  hotfix  "]) == "hotfix"
    for argv in (["--force"], ["--force", "--reason", "   "], ["--reason", "hotfix"]):
        with pytest.raises(SystemExit):
            _parse(argv)


def test_the_environment_variable_forces_with_its_value_as_the_reason():
    assert _parse([], {eg.FORCE_ENV: "pushing from a ticket merge"}) == "pushing from a ticket merge"
    assert _parse([], {eg.FORCE_ENV: "   "}) is None


def test_exported_force_sets_the_variable_for_child_processes_and_restores_it(monkeypatch):
    monkeypatch.delenv(eg.FORCE_ENV, raising=False)
    import os

    with eg.exported_force("because"):
        assert os.environ[eg.FORCE_ENV] == "because"
    assert eg.FORCE_ENV not in os.environ
    with eg.exported_force(None):
        assert eg.FORCE_ENV not in os.environ


# --- which pushes are gated ------------------------------------------------------------------


@pytest.mark.parametrize(
    "paths, platforms",
    [
        (["README.md", "docs/adr/0008.md", "scripts/external_gate.py", "tests/test_x.py", "src/hdttools/a.py"], []),
        (["web/src/App.tsx"], ["web"]),
        (["workers/scan-proxy/src/index.ts"], ["scan-proxy"]),
        (["android/app/build.gradle.kts"], ["android"]),
        (["android/a.kt", "README.md", "web/b.ts", "workers/scan-proxy/c.ts", "web/d.ts"], ["web", "scan-proxy", "android"]),
        (["webhook/a.py", "workers/scan-proxy-docs/a.md", "androidx/a.kt", "workers/other/a.ts"], []),
    ],
)
def test_only_pushes_touching_web_the_worker_or_android_are_gated(paths, platforms):
    assert eg.platforms_for_paths(paths) == platforms


class PushHarness:
    def __init__(self, paths=None, gate_code=0):
        self.paths, self.gate_code = paths, gate_code
        self.gated, self.diffed = [], []

    def changed_paths(self, remote_sha, local_sha):
        self.diffed.append((remote_sha, local_sha))
        return self.paths

    def gate(self, platforms):
        self.gated.append(platforms)
        return self.gate_code

    def run(self, *lines):
        return eg.pre_push("".join(lines), changed_paths=self.changed_paths, gate=self.gate)


def push_line(remote_ref="refs/heads/MPSkills", local_sha="a" * 40, remote_sha="b" * 40):
    return f"refs/heads/MPSkills {local_sha} {remote_ref} {remote_sha}\n"


def test_a_push_of_another_branch_is_not_gated_and_not_even_diffed():
    harness = PushHarness(["web/src/App.tsx"])

    assert harness.run(push_line("refs/heads/ticket-43")) == 0
    assert harness.gated == [] and harness.diffed == []


def test_a_docs_only_push_to_mpskills_passes_without_running_the_gate():
    harness = PushHarness(["README.md", "docs/a.md"])

    assert harness.run(push_line()) == 0
    assert harness.gated == []


def test_a_push_touching_web_is_gated_for_web_and_the_verdict_decides():
    assert PushHarness(["web/src/App.tsx"], gate_code=0).run(push_line()) == 0
    harness = PushHarness(["web/src/App.tsx"], gate_code=1)
    assert harness.run(push_line()) == 1
    assert harness.gated == [["web"]]


def test_deleting_the_branch_is_not_gated():
    harness = PushHarness(["web/src/App.tsx"])

    assert harness.run(push_line(local_sha=ZERO)) == 0
    assert harness.diffed == []


def test_a_diff_that_cannot_be_computed_gates_every_platform():
    harness = PushHarness(None)

    harness.run(push_line())

    assert harness.gated == [["web", "scan-proxy", "android"]]


def test_several_refs_in_one_push_are_gated_once_for_the_union_of_platforms():
    class PerSha(PushHarness):
        def changed_paths(self, remote_sha, local_sha):
            return {"1" * 40: ["web/a.ts"], "2" * 40: ["android/a.kt"]}[local_sha]

    harness = PerSha()

    harness.run(push_line(local_sha="1" * 40), push_line(local_sha="2" * 40))

    assert harness.gated == [["web", "android"]]


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def test_changed_paths_reads_the_pushed_diff_from_a_real_repo(tmp_path):
    _git(tmp_path, "init", "-q", "-b", "MPSkills")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "docs").mkdir()
    (tmp_path / "web").mkdir()
    (tmp_path / "docs" / "a.md").write_text("a\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "first")
    first = _git(tmp_path, "rev-parse", "HEAD")
    (tmp_path / "web" / "b.ts").write_text("b\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "second")
    second = _git(tmp_path, "rev-parse", "HEAD")
    git = eg.GitPush(cwd=tmp_path)

    assert git.changed_paths(first, second) == ["web/b.ts"]
    # Moving a file out of a gated directory still counts as touching it (no rename detection).
    _git(tmp_path, "mv", "web/b.ts", "docs/b.ts")
    _git(tmp_path, "commit", "-q", "-m", "move out")
    third = _git(tmp_path, "rev-parse", "HEAD")
    assert sorted(git.changed_paths(second, third)) == ["docs/b.ts", "web/b.ts"]
    # A branch the remote does not have yet: everything is new.
    assert sorted(git.changed_paths(ZERO, second)) == ["docs/a.md", "web/b.ts"]
    # A remote commit this clone does not have: the diff cannot be computed.
    assert git.changed_paths("f" * 40, second) is None
