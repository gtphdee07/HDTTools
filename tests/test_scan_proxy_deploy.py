"""Function tests for scripts/scan_proxy_deploy.py (#43): the Worker deploy refuses while a
surface in its chain is stale, unless forced with a reason. A fake gate and a fake command
runner stand in for the registries, the status file and wrangler."""

import importlib.util
import sys
from pathlib import Path

import pytest

from tests._release_test_helpers import FakeGate, FakeRunner

pytestmark = [pytest.mark.core, pytest.mark.minor]

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))
for _name in ("external_freshness", "record_external_result", "external_gate", "paid_call_budget", "release_steps", "scan_proxy_deploy"):
    _spec = importlib.util.spec_from_file_location(_name, _SCRIPTS / f"{_name}.py")
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[_name] = _module
    _spec.loader.exec_module(_module)

spd = sys.modules["scan_proxy_deploy"]


def deploy(argv, gate, runner, environ=None):
    return spd.run(argv, gate=gate, run_command=runner, environ=environ or {}, out=lambda _: None)


def test_a_fresh_chain_deploys_with_wrangler():
    gate, runner = FakeGate(0), FakeRunner()

    assert deploy([], gate, runner) == 0
    assert gate.calls == [(["scan-proxy"], None)]
    assert runner.calls == ["npx --no-install wrangler deploy"]


def test_a_blocked_gate_stops_before_wrangler_runs():
    gate, runner = FakeGate(1), FakeRunner()

    assert deploy([], gate, runner) == 1
    assert runner.calls == []


def test_forcing_with_a_reason_hands_it_to_the_gate_and_then_deploys():
    gate, runner = FakeGate(0), FakeRunner()

    assert deploy(["--force", "--reason", "deploying to test it"], gate, runner) == 0
    assert gate.calls == [(["scan-proxy"], "deploying to test it")]
    assert runner.calls == ["npx --no-install wrangler deploy"]


def test_forcing_without_a_reason_is_refused_before_anything_runs():
    gate, runner = FakeGate(0), FakeRunner()

    with pytest.raises(SystemExit):
        deploy(["--force"], gate, runner)
    assert gate.calls == [] and runner.calls == []


def test_a_release_run_that_was_forced_carries_its_reason_to_the_deploy_through_the_environment():
    gate, runner = FakeGate(0), FakeRunner()

    deploy([], gate, runner, environ={"EXTERNAL_GATE_FORCE_REASON": "release run was forced"})

    assert gate.calls == [(["scan-proxy"], "release run was forced")]


def test_arguments_the_gate_does_not_know_still_reach_wrangler():
    runner = FakeRunner()

    # `npm run deploy -- --dry-run` worked before the gate; --re is not an abbreviation of --reason.
    assert deploy(["--dry-run", "--re"], FakeGate(0), runner) == 0
    assert runner.calls == ["npx --no-install wrangler deploy --dry-run --re"]


def test_wranglers_own_failure_is_the_deploys_exit_code():
    runner = FakeRunner(exit_codes={"npx --no-install wrangler deploy": 3})

    assert deploy([], FakeGate(0), runner) == 3
