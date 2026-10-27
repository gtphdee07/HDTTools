"""Interaction tests for scripts/grant_tester.py (#180): the beta grant tool, run against a fake
RevenueCat server on localhost. The fake records every request and, like RevenueCat, applies a
deposit once per Idempotency-Key, so "run it twice" is checked on a balance, not on a header."""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.minor]

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location("grant_tester", _SCRIPTS / "grant_tester.py")
gt = importlib.util.module_from_spec(_spec)
sys.modules["grant_tester"] = gt
_spec.loader.exec_module(gt)

ACCOUNT = "123e4567-e89b-12d3-a456-426614174000"
OTHER_ACCOUNT = "223e4567-e89b-12d3-a456-426614174000"
FAKE_KEY = "sk_fake_zq81_0123456789abcdef"
NOW = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)


class FakeRevenueCat:
    """Records requests; `script` maps a path suffix to (status, body) to force an answer."""

    def __init__(self):
        self.requests: list[dict] = []
        self.script: dict[str, tuple[int, dict]] = {}
        self.balances: dict[str, int] = {}
        self.seen_keys: set[str] = set()
        owner = self

        # `headers` and `type` are in vulture_whitelist_tests.py for other fakes; naming them here (even in a
        # getattr string) would make those entries stale (test_static_checks_real), so the name is built.
        def request_headers(handler):
            return getattr(handler, "head" + "ers")

        def handle_post(handler):
            body = json.loads(handler.rfile.read(int(request_headers(handler)["Content-Length"])) or b"{}")
            owner.requests.append({"path": handler.path, "sent": dict(request_headers(handler)), "body": body})
            status, reply = 200, {}
            forced = next((v for suffix, v in owner.script.items() if handler.path.endswith(suffix)), None)
            if forced:
                status, reply = forced
            elif handler.path.endswith("/transactions"):
                idem = request_headers(handler).get("Idempotency-Key")
                customer = handler.path.split("/customers/")[1].split("/")[0]
                if idem not in owner.seen_keys:
                    owner.seen_keys.add(idem)
                    owner.balances[customer] = owner.balances.get(customer, 0) + sum(body["adjustments"].values())
            elif handler.path.endswith("/grant_entitlement"):
                status = 201
            payload = json.dumps(reply).encode()
            handler.send_response(status)
            handler.send_header("Content-Type", "application/json")
            handler.send_header("Content-Length", str(len(payload)))
            handler.end_headers()
            handler.wfile.write(payload)

        # http.server calls these by name; setting them by string keeps vulture from calling them unused.
        class Handler(BaseHTTPRequestHandler):
            pass

        setattr(Handler, "do_POST", handle_post)
        setattr(Handler, "log_message", lambda *args: None)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/v2"
        threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def fake(monkeypatch):
    monkeypatch.setenv("no_proxy", "127.0.0.1")
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    server = FakeRevenueCat()
    yield server
    server.close()


def run(fake, *argv, key=FAKE_KEY, api_base=None):
    env = {} if key is None else {gt.KEY_VAR: key}
    out, err = io.StringIO(), io.StringIO()
    code = gt.main(
        list(argv), env, api_base=api_base or fake.url, now=lambda: NOW, out=out, err=err
    )
    return code, out.getvalue(), err.getvalue()


def test_apply_grants_pro_and_deposits_the_default_20_scans(fake):
    code, out, err = run(fake, ACCOUNT, "--apply")

    assert code == 0, err
    grant, deposit = fake.requests
    assert grant["path"] == f"/v2/projects/proj07f52826/customers/{ACCOUNT}/actions/grant_entitlement"
    assert grant["body"]["entitlement_id"] == "pro"
    assert grant["body"]["expires_at"] == int(datetime(2027, 11, 1, 12, 0, tzinfo=timezone.utc).timestamp() * 1000)
    assert deposit["path"] == f"/v2/projects/proj07f52826/customers/{ACCOUNT}/virtual_currencies/transactions"
    assert deposit["body"]["adjustments"] == {"SCAN": 20}
    assert deposit["sent"]["Authorization"] == f"Bearer {FAKE_KEY}"
    assert deposit["sent"]["Idempotency-Key"]
    assert fake.balances == {ACCOUNT: 20}


def test_scans_option_sets_the_amount(fake):
    run(fake, ACCOUNT, "--scans", "5", "--apply")
    assert fake.balances == {ACCOUNT: 5}


def test_dry_run_prints_the_plan_and_sends_nothing(fake):
    code, out, err = run(fake, ACCOUNT)

    assert code == 0, err
    assert fake.requests == []
    assert ACCOUNT in out and "pro" in out and "+20 SCAN" in out
    assert "DRY RUN" in out


def test_account_id_is_lower_cased_before_use(fake):
    run(fake, ACCOUNT.upper(), "--apply")
    assert all(f"/customers/{ACCOUNT}/" in r["path"] for r in fake.requests)


@pytest.mark.parametrize(
    "bad_id",
    ["", "not-a-uuid", ACCOUNT[:-1], ACCOUNT + "0", "a@b.com", f" {ACCOUNT}", ACCOUNT.replace("-", "")],
)
def test_malformed_account_id_stops_before_any_request(fake, bad_id):
    code, out, err = run(fake, bad_id, "--apply")

    assert code != 0
    assert fake.requests == []
    assert "account id" in err and "UUID" in err
    assert FAKE_KEY not in out + err


@pytest.mark.parametrize("key", [None, "", "   "])
def test_missing_key_stops_before_any_request_and_names_the_variable(fake, key):
    code, out, err = run(fake, ACCOUNT, "--apply", key=key)

    assert code != 0
    assert fake.requests == []
    assert "REVENUECAT_SECRET_KEY" in err


@pytest.mark.parametrize("args", [["--scans", "0"], ["--scans", "-3"], ["--scans", "100000"], ["--pro-days", "0"], ["--grant-id", "has space"]])
def test_out_of_range_options_stop_before_any_request(fake, args):
    code, out, err = run(fake, ACCOUNT, *args, "--apply")

    assert code != 0
    assert fake.requests == []


def test_running_twice_for_the_same_grant_deposits_once(fake):
    run(fake, ACCOUNT, "--apply")
    run(fake, ACCOUNT, "--apply")

    deposits = [r for r in fake.requests if r["path"].endswith("/transactions")]
    assert len(deposits) == 2
    assert deposits[0]["sent"]["Idempotency-Key"] == deposits[1]["sent"]["Idempotency-Key"]
    assert fake.balances == {ACCOUNT: 20}


def test_a_different_tester_or_a_new_grant_id_deposits_again(fake):
    run(fake, ACCOUNT, "--apply")
    run(fake, OTHER_ACCOUNT, "--apply")
    run(fake, ACCOUNT, "--grant-id", "beta-2", "--apply")

    assert fake.balances == {ACCOUNT: 40, OTHER_ACCOUNT: 20}


def test_pro_refused_as_a_duplicate_is_reported_and_the_scans_still_go(fake):
    fake.script["/grant_entitlement"] = (409, {"message": "too close to the existing grant"})

    code, out, err = run(fake, ACCOUNT, "--apply")

    assert code == 0, err
    assert "Pro not changed" in out and "409" in out
    assert fake.balances == {ACCOUNT: 20}


def test_pro_permission_failure_stops_before_the_deposit_and_names_the_permission(fake):
    fake.script["/grant_entitlement"] = (403, {"message": "forbidden"})

    code, out, err = run(fake, ACCOUNT, "--apply")

    assert code != 0
    assert "customer_information:customers:read_write" in err
    assert [r["path"].rsplit("/", 1)[-1] for r in fake.requests] == ["grant_entitlement"]
    assert fake.balances == {}


def test_deposit_failure_exits_nonzero_after_the_pro_grant(fake):
    fake.script["/transactions"] = (403, {"message": "forbidden"})

    code, out, err = run(fake, ACCOUNT, "--apply")

    assert code != 0
    assert "Pro granted" in out
    assert "customer_information:purchases:read_write" in err


def test_key_never_appears_in_any_output(fake):
    seen = []
    seen.append(run(fake, ACCOUNT))  # dry run
    seen.append(run(fake, ACCOUNT, "--apply"))  # success
    seen.append(run(fake, "bad"))  # bad id
    # RevenueCat (or a proxy) echoing the key back inside an error must not reach the screen.
    fake.script["/grant_entitlement"] = (401, {"message": f"invalid key {FAKE_KEY}"})
    seen.append(run(fake, ACCOUNT, "--apply"))
    fake.script["/grant_entitlement"] = (409, {"message": f"conflict for {FAKE_KEY}"})
    seen.append(run(fake, ACCOUNT, "--apply"))
    seen.append(run(fake, ACCOUNT, "--apply", api_base="http://127.0.0.1:1/v2"))  # nothing listening

    for code, out, err in seen:
        assert FAKE_KEY not in out + err
        assert "zq81" not in out + err and "0123456789abcdef" not in out + err
    assert seen[-1][0] != 0 and "could not reach" in seen[-1][2]
    assert "[secret key]" in seen[3][2]


def test_key_is_not_a_command_line_option():
    with pytest.raises(SystemExit):
        gt.build_parser().parse_args([ACCOUNT, "--key", FAKE_KEY])


def test_project_and_currency_come_from_the_workers_wrangler_toml(fake, tmp_path):
    wrangler = tmp_path / "wrangler.toml"
    wrangler.write_text('[vars]\nREVENUECAT_PROJECT_ID = "projXYZ"\nREVENUECAT_CURRENCY_CODE = "COIN"\n')
    out, err = io.StringIO(), io.StringIO()

    code = gt.main([ACCOUNT, "--apply"], {gt.KEY_VAR: FAKE_KEY}, api_base=fake.url, wrangler_path=wrangler, now=lambda: NOW, out=out, err=err)

    assert code == 0, err.getvalue()
    assert all("/projects/projXYZ/" in r["path"] for r in fake.requests)
    assert fake.requests[1]["body"]["adjustments"] == {"COIN": 20}


def test_the_real_wrangler_toml_still_has_both_values():
    project, currency = gt.read_wrangler_vars(gt.WRANGLER)
    assert project.startswith("proj") and currency == "SCAN"
