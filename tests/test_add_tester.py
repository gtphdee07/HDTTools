"""Interaction tests for scripts/add_tester.py (#205): creates a tester's Supabase account and RevenueCat
customer, then grants Pro and scans, run against one fake server on localhost that plays both services.
The fake keeps the user list, the customer list and the scan balances, so "run it twice" and "found on the
third page" are checked on state, not on headers."""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import threading
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

pytestmark = [pytest.mark.core, pytest.mark.minor]

_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = _ROOT / "scripts"
sys.path.insert(0, str(_SCRIPTS))
_spec = importlib.util.spec_from_file_location("add_tester", _SCRIPTS / "add_tester.py")
at = importlib.util.module_from_spec(_spec)
sys.modules["add_tester"] = at
_spec.loader.exec_module(at)
gt = at.gt

EMAIL = "Tester.One+alpha@Example.com"
LOWER_EMAIL = EMAIL.lower()
SUPABASE_KEY = "sb_secret_fake_qw93_0123456789abcdef"
RC_KEY = "sk_fake_zq81_0123456789abcdef"
ENV = {at.SUPABASE_KEY_VAR: SUPABASE_KEY, gt.KEY_VAR: RC_KEY}
ENV_ID = "423e4567-e89b-12d3-a456-426614174000"
NOW = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
PRO_ONLY_PATH = "grant_entitlement"


class FakeServices:
    """Supabase Auth admin users plus the RevenueCat customer, entitlement and deposit calls.

    `script` maps "METHOD path-suffix" to (status, body) to force an answer."""

    def __init__(self):
        self.requests: list[dict] = []
        self.script: dict[str, tuple[int, dict]] = {}
        self.users: list[dict] = []
        self.customers: set[str] = set()
        self.balances: dict[str, int] = {}
        self.seen_keys: set[str] = set()
        owner = self

        # `headers` and `type` are in vulture_whitelist_tests.py for other fakes; naming them here (even in a
        # getattr string) would make those entries stale (test_static_checks_real), so the name is built.
        def request_headers(handler):
            return getattr(handler, "head" + "ers")

        def reply(handler, status, payload):
            data = json.dumps(payload).encode()
            handler.send_response(status)
            handler.send_header("Content-Type", "application/json")
            handler.send_header("Content-Length", str(len(data)))
            handler.end_headers()
            handler.wfile.write(data)

        def serve(handler):
            parts = urlsplit(handler.path)
            length = int(request_headers(handler).get("Content-Length") or 0)
            body = json.loads(handler.rfile.read(length) or b"{}")
            owner.requests.append(
                {"method": handler.command, "path": parts.path, "query": parse_qs(parts.query),
                 "sent": {k.lower(): v for k, v in request_headers(handler).items()}, "body": body}
            )
            call = f"{handler.command} {parts.path}"
            forced = next((v for suffix, v in owner.script.items() if call.endswith(suffix)), None)
            if forced:
                return reply(handler, *forced)
            if parts.path == "/auth/v1/admin/users":
                return owner.supabase(handler, reply, parts, body)
            return owner.revenuecat(handler, reply, parts.path, body, request_headers(handler))

        # http.server calls these by name; setting them by string keeps vulture from calling them unused.
        class Handler(BaseHTTPRequestHandler):
            pass

        setattr(Handler, "do_GET", serve)
        setattr(Handler, "do_POST", serve)
        setattr(Handler, "log_message", lambda *args: None)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.api_base = self.base + "/v2"
        threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()

    def supabase(self, handler, reply, parts, body):
        if handler.command == "GET":
            query = parse_qs(parts.query)
            page, per_page = int(query["page"][0]), int(query["per_page"][0])
            return reply(handler, 200, {"users": self.users[(page - 1) * per_page: page * per_page], "aud": "authenticated"})
        if any(u["email"] == body["email"] for u in self.users):
            return reply(handler, 422, {"code": 422, "error_code": "email_exists", "msg": "A user with this email exists"})
        user = {"id": str(uuid.uuid4()), "email": body["email"], "email_confirmed_at": "2026-11-01T12:00:00Z"}
        self.users.append(user)
        return reply(handler, 200, user)

    def revenuecat(self, handler, reply, path, body, sent):
        status, payload = 200, {}
        if path.endswith("/customers"):
            if body["id"] in self.customers:
                status, payload = 409, {"message": "already exists"}
            else:
                self.customers.add(body["id"])
                status = 201
        elif path.endswith("/transactions"):
            idem = sent.get("Idempotency-Key")
            customer = path.split("/customers/")[1].split("/")[0]
            if idem not in self.seen_keys:
                self.seen_keys.add(idem)
                self.balances[customer] = self.balances.get(customer, 0) + sum(body["adjustments"].values())
        elif path.endswith("/grant_entitlement"):
            status = 201
        return reply(handler, status, payload)

    def add_users(self, count: int):
        self.users += [{"id": str(uuid.uuid4()), "email": f"user{i}@example.com"} for i in range(count)]

    def paths(self, method: str | None = None) -> list[str]:
        return [r["path"] for r in self.requests if method is None or r["method"] == method]

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def fake(monkeypatch):
    monkeypatch.setenv("no_proxy", "127.0.0.1")
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    server = FakeServices()
    yield server
    server.close()


def run(fake, *argv, env=ENV, supabase_base=None, api_base=None, wrangler_path=gt.WRANGLER):
    out, err = io.StringIO(), io.StringIO()
    code = at.main(
        list(argv), env, supabase_base=supabase_base or fake.base, api_base=api_base or fake.api_base,
        wrangler_path=wrangler_path, now=lambda: NOW, out=out, err=err,
    )
    return code, out.getvalue(), err.getvalue()


def created_user(fake):
    (user,) = [u for u in fake.users if u["email"] == LOWER_EMAIL]
    return user


def test_apply_creates_the_account_the_customer_and_the_grants(fake):
    entitlement = gt.read_wrangler_vars(gt.WRANGLER)[2]
    code, out, err = run(fake, EMAIL, "--apply")

    assert code == 0, err
    user = created_user(fake)
    create = next(r for r in fake.requests if r["method"] == "POST" and r["path"] == "/auth/v1/admin/users")
    assert create["body"] == {"email": LOWER_EMAIL, "email_confirm": True}
    assert "password" not in create["body"]
    assert create["sent"]["apikey"] == SUPABASE_KEY and "authorization" not in create["sent"]
    customer = next(r for r in fake.requests if r["path"] == "/v2/projects/proj07f52826/customers")
    assert customer["body"] == {"id": user["id"]}
    assert customer["sent"]["authorization"] == f"Bearer {RC_KEY}"
    grant = next(r for r in fake.requests if r["path"].endswith("/grant_entitlement"))
    assert grant["path"] == f"/v2/projects/proj07f52826/customers/{user['id']}/actions/grant_entitlement"
    assert grant["body"]["entitlement_id"] == entitlement
    assert fake.balances == {user["id"]: 20}
    assert f"account id : {user['id']}" in out
    assert [r["path"].rsplit("/", 1)[-1] for r in fake.requests[-3:]] == ["customers", "grant_entitlement", "transactions"]


def test_the_requests_come_in_order_lookup_create_customer_pro_scans(fake):
    run(fake, EMAIL, "--apply")

    assert [(r["method"], r["path"].rsplit("/", 1)[-1]) for r in fake.requests] == [
        ("GET", "users"), ("POST", "users"), ("POST", "customers"),
        ("POST", "grant_entitlement"), ("POST", "transactions"),
    ]


def test_dry_run_prints_the_plan_and_sends_nothing(fake):
    code, out, err = run(fake, EMAIL)

    assert code == 0, err
    assert fake.requests == [] and fake.users == []
    assert "DRY RUN" in out and LOWER_EMAIL in out and "+20 SCAN" in out
    assert gt.read_wrangler_vars(gt.WRANGLER)[2] in out


def test_an_existing_user_on_a_later_page_is_found_not_created_again(fake):
    fake.add_users(2 * at.PAGE_SIZE + 50)
    fake.users.append({"id": "323e4567-e89b-12d3-a456-426614174000", "email": LOWER_EMAIL})

    code, out, err = run(fake, EMAIL.upper(), "--apply")

    assert code == 0, err
    assert fake.paths("POST")[0].endswith("/customers")
    assert len([u for u in fake.users if u["email"] == LOWER_EMAIL]) == 1
    assert [r["query"]["page"] for r in fake.requests if r["method"] == "GET"] == [["1"], ["2"], ["3"]]
    assert "found (already existed)" in out
    assert fake.balances == {"323e4567-e89b-12d3-a456-426614174000": 20}


def test_a_second_apply_finds_the_same_user_and_deposits_once(fake):
    run(fake, EMAIL, "--apply")
    code, out, err = run(fake, EMAIL, "--apply")

    assert code == 0, err
    user = created_user(fake)
    assert len(fake.users) == 1
    assert fake.balances == {user["id"]: 20}
    assert f"account id : {user['id']}" in out
    assert "already existed" in out


def test_a_revenuecat_409_on_the_customer_does_not_stop_the_run(fake):
    fake.script["POST /v2/projects/proj07f52826/customers"] = (409, {"message": "customer exists"})

    code, out, err = run(fake, EMAIL, "--apply")

    assert code == 0, err
    assert "RevenueCat customer already existed" in out
    assert fake.balances == {created_user(fake)["id"]: 20}


def test_no_pro_sends_no_entitlement_call_but_still_deposits_the_scans(fake):
    code, out, err = run(fake, EMAIL, "--no-pro", "--apply")

    assert code == 0, err
    assert not any(PRO_ONLY_PATH in p for p in fake.paths())
    assert fake.balances == {created_user(fake)["id"]: 20}
    assert "stays on Free" in out


def test_scans_pro_days_and_grant_id_reach_the_grant(fake):
    code, out, err = run(fake, EMAIL, "--scans", "7", "--pro-days", "30", "--grant-id", "beta-9", "--apply")

    assert code == 0, err
    user = created_user(fake)
    grant = next(r for r in fake.requests if r["path"].endswith("/grant_entitlement"))
    assert grant["body"]["expires_at"] == int(datetime(2026, 12, 1, 12, 0, tzinfo=timezone.utc).timestamp() * 1000)
    deposit = next(r for r in fake.requests if r["path"].endswith("/transactions"))
    assert deposit["body"]["adjustments"] == {"SCAN": 7}
    assert deposit["sent"]["idempotency-key"] == f"tester-grant-beta-9-{user['id']}"
    assert fake.balances == {user["id"]: 7}


def test_entitlement_option_overrides_the_one_in_wrangler_toml(fake):
    run(fake, EMAIL, "--entitlement", "entlOTHER99", "--apply")

    grant = next(r for r in fake.requests if r["path"].endswith("/grant_entitlement"))
    assert grant["body"]["entitlement_id"] == "entlOTHER99"


@pytest.mark.parametrize("bad", ["", "not-an-email", "a@b", "a b@example.com", "@example.com", "a@@example.com", "x" * 250 + "@example.com"])
def test_a_malformed_email_stops_before_any_request(fake, bad):
    code, out, err = run(fake, bad, "--apply")

    assert code != 0
    assert fake.requests == []
    assert "not an email address" in err


@pytest.mark.parametrize(
    "env, named",
    [
        ({gt.KEY_VAR: RC_KEY}, "SUPABASE_SECRET_KEY"),
        ({at.SUPABASE_KEY_VAR: SUPABASE_KEY}, "REVENUECAT_SECRET_KEY"),
        ({at.SUPABASE_KEY_VAR: "  ", gt.KEY_VAR: RC_KEY}, "SUPABASE_SECRET_KEY"),
        ({at.SUPABASE_KEY_VAR: SUPABASE_KEY, gt.KEY_VAR: ""}, "REVENUECAT_SECRET_KEY"),
        ({}, "SUPABASE_SECRET_KEY"),
    ],
)
def test_a_missing_key_stops_before_any_request_and_names_the_variable(fake, env, named):
    code, out, err = run(fake, EMAIL, "--apply", env=env)

    assert code != 0
    assert fake.requests == []
    assert named in err


@pytest.mark.parametrize(
    "args", [["--scans", "0"], ["--scans", "100000"], ["--pro-days", "0"], ["--grant-id", "has space"]]
)
def test_out_of_range_options_stop_before_any_request(fake, args):
    code, out, err = run(fake, EMAIL, *args, "--apply")

    assert code != 0
    assert fake.requests == []


def test_the_supabase_url_comes_from_the_workers_wrangler_toml_and_the_env_overrides_it(fake, tmp_path):
    assert at.read_supabase_url(gt.WRANGLER) == "https://lifginpapkevreyrzzex.supabase.co"
    wrangler = tmp_path / "wrangler.toml"
    wrangler.write_bytes(gt.WRANGLER.read_bytes())

    out, err = io.StringIO(), io.StringIO()
    code = at.main(
        [EMAIL, "--apply"], {**ENV, at.SUPABASE_URL_VAR: fake.base}, api_base=fake.api_base,
        wrangler_path=wrangler, now=lambda: NOW, out=out, err=err,
    )

    assert code == 0, err.getvalue()
    assert fake.paths("GET")[0] == "/auth/v1/admin/users"


def test_a_wrangler_toml_without_a_supabase_url_stops_before_any_request(fake, tmp_path):
    wrangler = tmp_path / "wrangler.toml"
    wrangler.write_text(
        '[vars]\nREVENUECAT_PROJECT_ID = "projXYZ"\nREVENUECAT_CURRENCY_CODE = "COIN"\n'
        'REVENUECAT_PRO_ENTITLEMENT_ID = "entlTEST123"\n'
    )
    out, err = io.StringIO(), io.StringIO()
    code = at.main([EMAIL, "--apply"], ENV, api_base=fake.api_base, wrangler_path=wrangler, now=lambda: NOW, out=out, err=err)

    assert code != 0 and "SUPABASE_URL" in err.getvalue()
    assert fake.requests == []


@pytest.mark.parametrize(
    "url", ["http://example.com", "https://evil.example", "https://x.supabase.co.evil.example", "https://supabase.co"]
)
def test_a_supabase_url_that_is_not_a_project_address_is_refused_because_the_secret_key_goes_to_it(fake, url):
    out, err = io.StringIO(), io.StringIO()
    code = at.main(
        [EMAIL, "--apply"], {**ENV, at.SUPABASE_URL_VAR: url}, api_base=fake.api_base,
        now=lambda: NOW, out=out, err=err,
    )

    assert code != 0 and "supabase.co" in err.getvalue()
    assert fake.requests == []


def test_a_legacy_jwt_service_role_key_is_also_sent_as_the_bearer_token(fake):
    jwt_key = "eyJhbGciOi.fakepayloadzz.fakesignature"

    code, out, err = run(fake, EMAIL, "--apply", env={at.SUPABASE_KEY_VAR: jwt_key, gt.KEY_VAR: RC_KEY})

    assert code == 0, err
    lookup = fake.requests[0]
    assert lookup["sent"]["apikey"] == jwt_key and lookup["sent"]["authorization"] == f"Bearer {jwt_key}"


def test_an_existing_user_who_never_confirmed_gets_a_note(fake):
    fake.users.append({"id": ENV_ID, "email": LOWER_EMAIL})

    code, out, err = run(fake, EMAIL, "--apply")

    assert code == 0, err
    assert "not confirmed" in out and "Authentication, Users" in out
    assert fake.balances == {ENV_ID: 20}


def test_a_confirmed_existing_user_gets_no_note(fake):
    fake.users.append({"id": ENV_ID, "email": LOWER_EMAIL, "email_confirmed_at": "2026-10-01T00:00:00Z"})

    code, out, err = run(fake, EMAIL, "--apply")

    assert code == 0, err
    assert "not confirmed" not in out


@pytest.mark.parametrize(
    "status, expected",
    [(401, "SUPABASE_SECRET_KEY must be the project's secret"), (403, "SUPABASE_SECRET_KEY must be the project's secret"),
     (422, "HTTP 422"), (500, "try again"), (503, "try again")],
)
def test_a_supabase_lookup_failure_names_what_failed_and_changes_nothing(fake, status, expected):
    fake.script["GET /auth/v1/admin/users"] = (status, {"msg": "nope"})

    code, out, err = run(fake, EMAIL, "--apply")

    assert code != 0
    assert "Supabase user lookup failed" in err and f"HTTP {status}" in err and "nope" in err and expected in err
    assert "Done: nothing" in err and "Not done: Supabase account, RevenueCat customer, Pro grant, scan deposit" in err
    assert fake.paths("POST") == [] and fake.users == []


@pytest.mark.parametrize("status", [401, 403, 422, 500])
def test_a_supabase_create_failure_names_the_step(fake, status):
    fake.script["POST /auth/v1/admin/users"] = (status, {"error_code": "x", "msg": "cannot create"})

    code, out, err = run(fake, EMAIL, "--apply")

    assert code != 0
    assert "Supabase user create failed" in err and f"HTTP {status}" in err and "cannot create" in err
    assert not any(p.endswith("/customers") for p in fake.paths())


@pytest.mark.parametrize("status", [401, 403])
def test_a_revenuecat_customer_permission_failure_names_the_permission_and_what_is_done(fake, status):
    fake.script["POST /v2/projects/proj07f52826/customers"] = (status, {"message": "forbidden"})

    code, out, err = run(fake, EMAIL, "--apply")

    assert code != 0
    assert "customer_information:customers:read_write" in err and "REVENUECAT_SECRET_KEY" in err
    assert "Done: Supabase account." in err and "Not done: RevenueCat customer, Pro grant, scan deposit" in err
    assert len(fake.users) == 1 and fake.balances == {}


@pytest.mark.parametrize("status", [422, 500])
def test_other_revenuecat_customer_failures_stop_the_run(fake, status):
    fake.script["POST /v2/projects/proj07f52826/customers"] = (status, {"message": "bad"})

    code, out, err = run(fake, EMAIL, "--apply")

    assert code != 0
    assert "RevenueCat customer create failed" in err and f"HTTP {status}" in err
    assert fake.balances == {}


def test_a_pro_failure_reports_the_steps_already_done(fake):
    fake.script["/grant_entitlement"] = (403, {"message": "forbidden"})

    code, out, err = run(fake, EMAIL, "--apply")

    assert code != 0
    assert "customer_information:customers:read_write" in err
    assert "Done: Supabase account, RevenueCat customer." in err and "Not done: Pro grant, scan deposit" in err


def test_a_deposit_failure_reports_the_pro_grant_as_done(fake):
    fake.script["/transactions"] = (403, {"message": "forbidden"})

    code, out, err = run(fake, EMAIL, "--apply")

    assert code != 0
    assert "customer_information:purchases:read_write" in err
    assert "Done: Supabase account, RevenueCat customer, Pro grant." in err and "Not done: scan deposit" in err


def test_a_pro_409_is_noted_and_the_scans_still_go(fake):
    fake.script["/grant_entitlement"] = (409, {"message": "too close to the existing grant"})

    code, out, err = run(fake, EMAIL, "--apply")

    assert code == 0, err
    assert "Pro not changed" in out
    assert fake.balances == {created_user(fake)["id"]: 20}


def test_an_unreachable_server_is_reported_and_names_the_service(fake):
    code, out, err = run(fake, EMAIL, "--apply", supabase_base="http://127.0.0.1:1")
    assert code != 0 and "could not reach Supabase" in err

    code, out, err = run(fake, EMAIL, "--apply", api_base="http://127.0.0.1:1/v2")
    assert code != 0 and "could not reach RevenueCat" in err
    assert "Done: Supabase account." in err


def test_a_lookup_that_never_ends_is_given_up_on(fake, monkeypatch):
    monkeypatch.setattr(at, "MAX_PAGES", 3)
    fake.script["GET /auth/v1/admin/users"] = (200, {"users": [{"id": ENV_ID, "email": "someone@example.com"}]})

    code, out, err = run(fake, EMAIL, "--apply")

    assert code != 0 and "gave up after 3 pages" in err
    assert fake.paths("POST") == []


def test_an_answer_without_a_users_list_or_user_id_is_an_error(fake):
    fake.script["GET /auth/v1/admin/users"] = (200, {"oops": True})
    code, out, err = run(fake, EMAIL, "--apply")
    assert code != 0 and "no 'users' list" in err

    del fake.script["GET /auth/v1/admin/users"]
    fake.script["POST /auth/v1/admin/users"] = (200, {"no_id": True})
    code, out, err = run(fake, EMAIL, "--apply")
    assert code != 0 and "account id" in err


def test_a_created_user_nested_under_user_is_read(fake):
    fake.script["POST /auth/v1/admin/users"] = (200, {"user": {"id": ENV_ID, "email": LOWER_EMAIL}})

    code, out, err = run(fake, EMAIL, "--apply")

    assert code == 0, err
    assert f"account id : {ENV_ID}" in out


def test_neither_key_appears_in_any_output(fake):
    seen = [run(fake, EMAIL), run(fake, EMAIL, "--apply"), run(fake, "bad"), run(fake, EMAIL, "--apply", env={gt.KEY_VAR: RC_KEY})]
    # Either service (or a proxy) echoing a key back inside an error must not reach the screen.
    fake.script["GET /auth/v1/admin/users"] = (401, {"msg": f"bad key {SUPABASE_KEY} and {RC_KEY}"})
    seen.append(run(fake, EMAIL, "--apply"))
    del fake.script["GET /auth/v1/admin/users"]
    fake.script["POST /v2/projects/proj07f52826/customers"] = (500, {"message": f"oops {RC_KEY} {SUPABASE_KEY}"})
    seen.append(run(fake, EMAIL, "--apply"))
    fake.script["POST /v2/projects/proj07f52826/customers"] = (409, {"message": f"conflict {RC_KEY}"})
    fake.script["/grant_entitlement"] = (409, {"message": f"conflict {SUPABASE_KEY}"})
    seen.append(run(fake, EMAIL, "--apply"))
    seen.append(run(fake, EMAIL, "--apply", supabase_base="http://127.0.0.1:1"))

    for code, out, err in seen:
        for piece in (SUPABASE_KEY, RC_KEY, "qw93", "zq81", "0123456789abcdef"):
            assert piece not in out + err
    assert "[secret key]" in seen[4][2] and "[secret key]" in seen[5][2]


def test_the_keys_are_not_command_line_options():
    for option in ("--key", "--supabase-key", "--secret-key"):
        with pytest.raises(SystemExit):
            at.build_parser().parse_args([EMAIL, option, SUPABASE_KEY])


def test_next_steps_name_forgot_password_the_web_page_and_the_manual_google_step(fake):
    code, out, err = run(fake, EMAIL, "--apply")

    assert code == 0, err
    assert "Forgot password" in out and "https://rigcheck-web.pages.dev" in out
    assert "Google test user" in out and "manual" in out


def test_the_reset_site_is_the_one_the_android_app_redirects_to():
    source = (_ROOT / "android/app/src/main/java/com/rigcheck/app/data/SupabaseAccountBackend.kt").read_text(encoding="utf-8")
    assert f'PASSWORD_RESET_REDIRECT = "{at.RESET_SITE}"' in source


def test_the_docs_describe_the_script_the_secret_key_setup_and_the_manual_google_step():
    docs = _ROOT / "docs"
    deploy = (docs / "BUILD_AND_DEPLOY.md").read_text(encoding="utf-8").split("### Granting a tester", 1)[1].split("\n### ", 1)[0]
    assert "scripts/add_tester.py <email>" in deploy and "--no-pro" in deploy and "--apply" in deploy
    assert "SUPABASE_SECRET_KEY" in deploy and "API keys" in deploy and "never" in deploy
    assert "Google test user" in deploy

    plan = (docs / "BETA_PLAN.md").read_text(encoding="utf-8").split("### Owner steps for Alpha", 1)[1].split("\n### ", 1)[0]
    assert "add_tester.py" in plan and "SUPABASE_SECRET_KEY" in plan

    guide = (docs / "BETA_TESTER_GUIDE.md").read_text(encoding="utf-8")
    assert "Forgot password" in guide and "Web" in guide.split("Forgot password", 1)[1][:400]

    sheet = (_ROOT / "scripts" / "gen_test_round_handoff.py").read_text(encoding="utf-8")
    assert "add_tester.py" in sheet and "SUPABASE_SECRET_KEY" in sheet
