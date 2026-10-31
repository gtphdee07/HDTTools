"""Creates a beta tester's account and gives them Pro and scans before they have opened the app (#205).

Usage: uv run scripts/add_tester.py <email> [--scans 20] [--no-pro] [--apply]

grant_tester.py needs the tester's Supabase account id, which exists only after they sign in once. This
creates the account first, so the owner can do everything from one command. Without --apply it is a dry run:
it prints the plan and sends nothing (not even the lookup). With --apply it does four steps:

1. Supabase: find the user by email (paged GET /auth/v1/admin/users, case-insensitive); if absent, create it
   with POST /auth/v1/admin/users, email_confirm true and no password. That sends no email. A second run
   finds the same user.
2. RevenueCat: POST /v2/projects/{project}/customers with the Supabase id. 409 is taken as "already exists".
3. Pro and 4. scans: the calls of grant_tester.py, with the same idempotency key
   (tester-grant-<grant-id>-<account-id>). --no-pro skips the Pro call and still deposits the scans.

The tester then uses Forgot password (the email's link opens the Web site, where they set the password) or
Continue with Google. Adding a Gmail to the Google consent screen's test users stays a manual step in Google
Cloud Console.

Keys come only from the environment, never from an argument, and are scrubbed from everything printed:
  SUPABASE_SECRET_KEY    the project's secret (service-role) key; Supabase dashboard, API keys. Shell only.
  REVENUECAT_SECRET_KEY  the same key grant_tester.py uses.
SUPABASE_URL overrides the project URL, which is otherwise read from workers/scan-proxy/wrangler.toml.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Mapping, TextIO

sys.path.insert(0, str(Path(__file__).resolve().parent))

import grant_tester as gt  # noqa: E402

SUPABASE_KEY_VAR = "SUPABASE_SECRET_KEY"
SUPABASE_URL_VAR = "SUPABASE_URL"
PAGE_SIZE = 200
# 100 pages of 200 is 20,000 users: far beyond the beta, and it stops a server that ignores `page` from looping.
MAX_PAGES = 100
_EMAIL_SHAPE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# The secret key goes to this URL, so it must be a Supabase project over https (plain http only to this machine,
# for the tests' fakes).
_SAFE_BASE = re.compile(r"^(https://[a-z0-9-]+\.supabase\.co/?$|http://127\.0\.0\.1[:/])")


class _Scrubbed:
    """A text stream that replaces every secret with a label before writing, whatever printed it."""

    def __init__(self, target: TextIO, secrets: list[str]):
        self._target = target
        self._secrets = secrets

    def write(self, text: str) -> int:
        for secret in self._secrets:
            text = text.replace(secret, "[secret key]")
        return self._target.write(text)

    def flush(self) -> None:
        self._target.flush()


class SupabaseAdmin:
    def __init__(self, base_url: str, key: str):
        self._base = base_url.rstrip("/")
        self._key = key
        self._opener = gt.opener_without_redirects()

    def request(self, method: str, path: str, body: dict | None = None) -> tuple[int, object]:
        """(status, parsed JSON or None). Raises GrantError only when no answer came back."""
        headers = {"apikey": self._key, "Content-Type": "application/json"}
        if self._key.count(".") == 2:
            # A legacy service_role key is a JWT and is also sent as the bearer token. A new sb_secret_ key is not a
            # JWT: Supabase's gateway turns the apikey header into the token itself, and a bearer value is not wanted.
            headers["Authorization"] = f"Bearer {self._key}"
        request = urllib.request.Request(
            self._base + path,
            data=None if body is None else json.dumps(body).encode(),
            headers=headers,
            method=method,
        )
        try:
            with self._opener.open(request, timeout=gt.TIMEOUT_SECONDS) as response:
                return response.status, gt.json_or_none(response.read())
        except urllib.error.HTTPError as err:
            return err.code, gt.json_or_none(err.read())
        except (urllib.error.URLError, TimeoutError, OSError) as err:
            reason = getattr(err, "reason", err)
            raise gt.GrantError(f"could not reach Supabase ({type(err).__name__}: {reason})") from None


def read_supabase_url(path: Path) -> str:
    match = re.search(r'^SUPABASE_URL\s*=\s*"([^"]+)"', path.read_text(encoding="utf-8"), re.M)
    if not match:
        raise gt.GrantError(f"SUPABASE_URL not found in {path}; set the {SUPABASE_URL_VAR} environment variable")
    return match.group(1)


def normalise_email(raw: str) -> str:
    email = (raw or "").strip()
    if len(email) > 254 or not _EMAIL_SHAPE.match(email):
        raise gt.GrantError(f"'{raw}' is not an email address (expected name@example.com)")
    return email.lower()


def _message(body: object) -> str:
    if isinstance(body, dict):
        for field in ("message", "msg", "error_description", "error"):
            text = body.get(field)
            if isinstance(text, str):
                return text
    return "no message"


def _failure(step: str, service: str, status: int, body: object, key_hint: str) -> str:
    text = f"{step} failed: {service} answered HTTP {status} ({_message(body)})"
    if status in (401, 403):
        text += f". {key_hint}"
    elif status >= 500:
        text += ". The service had a problem on its side; try again in a few minutes."
    return text


def find_user(admin: SupabaseAdmin, email: str) -> tuple[str, bool] | None:
    """(account id, email confirmed) of the user with this email (any case), or None; reads pages until an empty one."""
    for page in range(1, MAX_PAGES + 1):
        status, body = admin.request("GET", f"/auth/v1/admin/users?page={page}&per_page={PAGE_SIZE}")
        if not 200 <= status < 300:
            raise gt.GrantError(_failure("Supabase user lookup", "Supabase", status, body, _SUPABASE_HINT))
        users = body.get("users") if isinstance(body, dict) else None
        if not isinstance(users, list):
            raise gt.GrantError("Supabase user lookup failed: the answer had no 'users' list")
        if not users:
            return None
        for user in users:
            if isinstance(user, dict) and str(user.get("email") or "").lower() == email:
                confirmed = bool(user.get("email_confirmed_at") or user.get("confirmed_at"))
                return gt.normalise_account_id(str(user.get("id"))), confirmed
    raise gt.GrantError(f"Supabase user lookup gave up after {MAX_PAGES} pages without reaching the end of the list")


def create_user(admin: SupabaseAdmin, email: str) -> str:
    status, body = admin.request("POST", "/auth/v1/admin/users", {"email": email, "email_confirm": True})
    if not 200 <= status < 300:
        raise gt.GrantError(_failure("Supabase user create", "Supabase", status, body, _SUPABASE_HINT))
    user = body.get("user") if isinstance(body, dict) and isinstance(body.get("user"), dict) else body
    return gt.normalise_account_id(str(user.get("id")) if isinstance(user, dict) else "")


def create_customer(client: gt.Client, project_id: str, account_id: str) -> bool:
    """True when RevenueCat created the customer, False when it already existed (409)."""
    status, body = client.post(f"/projects/{project_id}/customers", {"id": account_id})
    if 200 <= status < 300:
        return True
    if status == 409:
        return False
    hint = f"The key in {gt.KEY_VAR} needs the permission customer_information:customers:read_write."
    raise gt.GrantError(_failure("RevenueCat customer create", "RevenueCat", status, body, hint))


_SUPABASE_HINT = (
    f"{SUPABASE_KEY_VAR} must be the project's secret (service-role) key: "
    "Supabase dashboard, Project Settings, API keys, create a secret key."
)

NEXT_STEPS = """\
Next steps for the tester ({email}):
  1. Install the beta APK.
  2. In the app, tap Forgot password and enter this address. The email's link opens the Web site
     ({reset_site}), where they set a password; then they sign in on the app with the address and password.
  3. Or tap Continue with Google, but only if this Gmail is listed as a Google test user (Google Cloud
     Console, OAuth consent screen; that step is manual and is not done by this script)."""
# SupabaseAccountBackend.kt, PASSWORD_RESET_REDIRECT.
RESET_SITE = "https://rigcheck-web.pages.dev"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="add_tester.py",
        description=(
            "Create a beta tester's Supabase account (confirmed, no password) and RevenueCat customer, then give "
            "them Pro and scans. Dry run unless --apply is given."
        ),
        epilog=f"The secret keys are read from {SUPABASE_KEY_VAR} and {gt.KEY_VAR} and never printed.",
    )
    parser.add_argument("email", help="the tester's email address")
    parser.add_argument("--scans", type=int, default=gt.DEFAULT_SCANS, help=f"scans to deposit (default {gt.DEFAULT_SCANS})")
    parser.add_argument("--apply", action="store_true", help="do it; without it nothing is sent")
    parser.add_argument("--no-pro", action="store_true", help="leave the tester on Free: no Pro grant, scans still deposited")
    parser.add_argument(
        "--pro-days", type=int, default=gt.DEFAULT_PRO_DAYS,
        help=f"days until the Pro grant expires (default {gt.DEFAULT_PRO_DAYS}, longer than the beta)",
    )
    parser.add_argument(
        "--entitlement", default=None,
        help="the RevenueCat entitlement id (entl...) to grant; default is REVENUECAT_PRO_ENTITLEMENT_ID in workers/scan-proxy/wrangler.toml",
    )
    parser.add_argument(
        "--grant-id", default=gt.DEFAULT_GRANT_ID,
        help=f"names this grant in the idempotency key (default {gt.DEFAULT_GRANT_ID}); use a new one to deposit again on purpose",
    )
    return parser


def main(
    argv: list[str] | None = None,
    env: Mapping[str, str] | None = None,
    *,
    supabase_base: str | None = None,
    api_base: str = gt.API_BASE,
    wrangler_path: Path = gt.WRANGLER,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    out: TextIO | None = None,
    err: TextIO | None = None,
) -> int:
    env = os.environ if env is None else env
    args = build_parser().parse_args(argv)
    supabase_key = (env.get(SUPABASE_KEY_VAR) or "").strip()
    revenuecat_key = (env.get(gt.KEY_VAR) or "").strip()
    secrets = [key for key in (supabase_key, revenuecat_key) if key]
    out = _Scrubbed(out or sys.stdout, secrets)
    err = _Scrubbed(err or sys.stderr, secrets)

    try:
        email = normalise_email(args.email)
        gt.check_options(args)
        for var, key in ((SUPABASE_KEY_VAR, supabase_key), (gt.KEY_VAR, revenuecat_key)):
            if not key:
                raise gt.GrantError(f"{var} is not set; put the secret key in that environment variable")
        project_id, currency, wrangler_entitlement = gt.read_wrangler_vars(wrangler_path)
        base = supabase_base or (env.get(SUPABASE_URL_VAR) or "").strip() or read_supabase_url(wrangler_path)
        if not _SAFE_BASE.match(base):
            raise gt.GrantError(
                f"{SUPABASE_URL_VAR} must be an https://<project>.supabase.co address (the secret key is sent to it)"
            )
    except gt.GrantError as problem:
        print(f"error: {problem}", file=err)
        return 1

    entitlement = args.entitlement or wrangler_entitlement
    expires_at = now() + timedelta(days=args.pro_days)
    steps = ["Supabase account", "RevenueCat customer"] + ([] if args.no_pro else ["Pro grant"]) + ["scan deposit"]
    done: list[str] = []

    print(f"{'APPLY' if args.apply else 'DRY RUN (nothing is sent; add --apply to do it)'}", file=out)
    print(f"  tester     : {email}", file=out)
    print("  account    : found by email in Supabase, or created confirmed with no password", file=out)
    print(f"  customer   : RevenueCat customer with the same id in project {project_id} (an existing one is fine)", file=out)
    if args.no_pro:
        print("  Pro        : not granted (--no-pro): the tester stays on Free", file=out)
    else:
        print(f"  Pro        : entitlement '{entitlement}' until {expires_at:%Y-%m-%d} UTC ({args.pro_days} days)", file=out)
    print(f"  scans      : +{args.scans} {currency}", file=out)
    print(f"  idempotency: {gt.grant_idempotency_key(args.grant_id, '<account id>')}", file=out)
    if not args.apply:
        return 0

    admin = SupabaseAdmin(base, supabase_key)
    client = gt.Client(api_base, revenuecat_key)
    try:
        existing = find_user(admin, email)
        account_id = existing[0] if existing else create_user(admin, email)
        done.append("Supabase account")
        print(f"  ok   Supabase account {'found (already existed)' if existing else 'created (confirmed, no password)'}", file=out)
        print(f"  account id : {account_id}", file=out)
        if existing and not existing[1]:
            print(
                "  note this account's email is not confirmed (it was created by a sign-up, not by this script): "
                "confirm it in the Supabase dashboard, Authentication, Users, or the tester must open the confirmation "
                "email, before Forgot password will work.",
                file=out,
            )

        created = create_customer(client, project_id, account_id)
        done.append("RevenueCat customer")
        print(f"  ok   RevenueCat customer {'created' if created else 'already existed'}", file=out)

        customer = gt.customer_path(project_id, account_id)
        idempotency_key = gt.grant_idempotency_key(args.grant_id, account_id)
        if not args.no_pro:
            gt.grant_pro(client, customer, entitlement, expires_at, out)
            done.append("Pro grant")
        gt.deposit_scans(client, customer, currency, args.scans, idempotency_key, out)
        done.append("scan deposit")
    except gt.GrantError as problem:
        print(f"error: {problem}", file=err)
        print(
            f"stopped. Done: {', '.join(done) or 'nothing'}. Not done: {', '.join(s for s in steps if s not in done)}. "
            "Running the same command again is safe: it picks up where this stopped.",
            file=err,
        )
        return 1

    print(NEXT_STEPS.format(email=email, reset_site=RESET_SITE), file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
