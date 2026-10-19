"""Shared fakes for the suite-skipping tests of /ticket-finish and /ticket-merge (#128):
a small planner config, a fake suite runner, and the real ledger module pointed at a
ledger file in tmp_path."""

from __future__ import annotations

from types import SimpleNamespace

SUITE_CONTEXTS = {
    "core": {"marker": "core", "paths": ["src/hdttools/"], "file": "core-file {file}", "test_for": [],
             "context": "core-suite", "application": "core-suite"},
    "web": {"paths": ["web/"], "commands": {"minor": "web-suite", "major": "web-suite"},
            "file": "web-file {rel}", "test_for": [], "context": "web-suite"},
    "proxy": {"paths": ["workers/scan-proxy/"], "commands": {"minor": "proxy-suite", "major": "proxy-suite"},
              "file": "proxy-file {rel}", "test_for": [], "context": "proxy-suite"},
}


def suite_config(*names: str) -> dict:
    """A planner config with just these contexts (all three by default)."""
    return {"dependency_files": [], "interfaces": [],
            "contexts": {n: c for n, c in SUITE_CONTEXTS.items() if not names or n in names}}


class Runner:
    """A suite runner that records what it ran; `failing` names the commands that exit 1."""

    def __init__(self, failing=()):
        self.failing = set(failing)
        self.calls: list[str] = []

    def __call__(self, command, cwd=None):
        text = " ".join(command)
        self.calls.append(text)
        return SimpleNamespace(returncode=1 if text in self.failing else 0)


class LedgerAt:
    """The real verification ledger module, writing to a ledger file chosen by the test."""

    def __init__(self, vl, path):
        self.vl = vl
        self.path = path
        self.Revision = vl.Revision
        self.LedgerError = vl.LedgerError
        self.GitError = vl.GitError
        self.current_revision = vl.current_revision

    def suite_verdict(self, command, revision, git=None):
        return self.vl.suite_verdict(command, revision, path=self.path, git=git)

    def last_suite_pass_tree(self, command, git=None):
        return self.vl.last_suite_pass_tree(command, path=self.path, git=git)

    def record_suite(self, command, outcome, **kw):
        return self.vl.record_suite(command, outcome, path=self.path, **kw)

    def run_suite_and_record(self, command, **kw):
        return self.vl.run_suite_and_record(command, path=self.path, **kw)
