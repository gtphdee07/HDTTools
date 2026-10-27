"""Gives one beta tester a Pro entitlement and a number of scans in RevenueCat (#180).

Usage: uv run scripts/grant_tester.py <supabase-account-id> [--scans 20] [--apply]

The RevenueCat customer id is the Supabase account id (Supabase dashboard,
Authentication, Users). Without --apply this is a dry run: it prints exactly what
it would do and sends nothing. With --apply it makes two calls:

1. Pro: POST /v2/projects/{project}/customers/{id}/actions/grant_entitlement,
   a promotional entitlement that expires --pro-days from now (default 365, so
   it outlasts the beta). Needs the key permission customer_information:customers:read_write.
   The entitlement is named by its internal id, REVENUECAT_PRO_ENTITLEMENT_ID in the Worker's
   wrangler.toml (RevenueCat's call takes the id, not the lookup key `pro`), so the id is
   written in one place; --entitlement overrides it for a single run.
2. Scans: POST /v2/projects/{project}/customers/{id}/virtual_currencies/transactions,
   the same call the Worker makes (workers/scan-proxy/src/revenuecat.ts), with an
   Idempotency-Key built from the account id and --grant-id. Needs
   customer_information:purchases:read_write.

Running it twice for the same tester and the same --grant-id sends the same
Idempotency-Key, so RevenueCat applies the deposit once. How long RevenueCat
remembers a key is not in its documentation; for a deliberate second deposit
(more scans later) pass a new --grant-id. The Pro expiry is counted from the moment
of each run, so a second run within two hours of the first asks for an expiry
RevenueCat treats as a duplicate and refuses; the tool reports that (HTTP 409 is
assumed, as RevenueCat's page does not name the code) and carries on to the scans.

The secret key is read from REVENUECAT_SECRET_KEY, never from an argument, and
is never printed: every message is scrubbed of it before it is shown.
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
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Mapping, TextIO

API_BASE = "https://api.revenuecat.com/v2"
WRANGLER = Path(__file__).resolve().parent.parent / "workers" / "scan-proxy" / "wrangler.toml"
TIMEOUT_SECONDS = 10
DEFAULT_SCANS = 20
DEFAULT_PRO_DAYS = 365
DEFAULT_GRANT_ID = "beta-1"
# A sanity cap, so a mistyped extra zero is caught before it is deposited.
MAX_SCANS = 1000

KEY_VAR = "REVENUECAT_SECRET_KEY"
_UUID_SHAPE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
_GRANT_ID_SHAPE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class GrantError(Exception):
    """A problem the owner can act on; its message is safe to print."""


def read_wrangler_vars(path: Path) -> tuple[str, str, str]:
    """(REVENUECAT_PROJECT_ID, REVENUECAT_CURRENCY_CODE, REVENUECAT_PRO_ENTITLEMENT_ID) from the Worker's wrangler.toml."""
    text = path.read_text(encoding="utf-8")
    found = []
    for name in ("REVENUECAT_PROJECT_ID", "REVENUECAT_CURRENCY_CODE", "REVENUECAT_PRO_ENTITLEMENT_ID"):
        match = re.search(rf'^{name}\s*=\s*"([^"]+)"', text, re.M)
        if not match:
            raise GrantError(f"{name} not found in {path}")
        found.append(match.group(1))
    return found[0], found[1], found[2]


def normalise_account_id(raw: str) -> str:
    if not _UUID_SHAPE.match(raw or ""):
        raise GrantError(
            "the account id must be a Supabase user id (a UUID like "
            "123e4567-e89b-12d3-a456-426614174000); copy it from the Supabase "
            "dashboard, Authentication, Users"
        )
    return str(uuid.UUID(raw))


def _opener_without_redirects() -> urllib.request.OpenerDirector:
    """A redirect would carry the Authorization header to another host, so none is followed:
    returning None from redirect_request makes urllib raise the 3xx as an HTTPError."""
    handler = urllib.request.HTTPRedirectHandler()
    setattr(handler, "redirect_request", lambda *args, **kwargs: None)  # vulture cannot see a def
    return urllib.request.build_opener(handler)


class Client:
    def __init__(self, api_base: str, key: str):
        self._api_base = api_base.rstrip("/")
        self._key = key
        self._opener = _opener_without_redirects()

    def scrub(self, text: str) -> str:
        return text.replace(self._key, "[secret key]") if self._key else text

    def post(self, path: str, body: dict, idempotency_key: str | None = None) -> tuple[int, object]:
        """(status, parsed JSON or None). Raises GrantError only when no answer came back."""
        headers = {
            "Authorization": f"Bearer {self._key}",
            "Content-Type": "application/json",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        request = urllib.request.Request(
            self._api_base + path, data=json.dumps(body).encode(), headers=headers, method="POST"
        )
        try:
            with self._opener.open(request, timeout=TIMEOUT_SECONDS) as response:
                return response.status, _json_or_none(response.read())
        except urllib.error.HTTPError as err:
            return err.code, _json_or_none(err.read())
        except (urllib.error.URLError, TimeoutError, OSError) as err:
            reason = getattr(err, "reason", err)
            raise GrantError(self.scrub(f"could not reach RevenueCat ({type(err).__name__}: {reason})")) from None


def _json_or_none(raw: bytes) -> object:
    try:
        return json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        return None


def _message(body: object) -> str:
    if isinstance(body, dict):
        text = body.get("message") or body.get("error")
        if isinstance(text, str):
            return text
    return "no message"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="grant_tester.py",
        description="Give a beta tester Pro and scans in RevenueCat. Dry run unless --apply is given.",
        epilog=f"The secret key is read from {KEY_VAR} and never printed.",
    )
    parser.add_argument("account_id", help="the tester's Supabase account id (a UUID)")
    parser.add_argument("--scans", type=int, default=DEFAULT_SCANS, help=f"scans to deposit (default {DEFAULT_SCANS})")
    parser.add_argument("--apply", action="store_true", help="send the grants; without it nothing is sent")
    parser.add_argument(
        "--pro-days", type=int, default=DEFAULT_PRO_DAYS,
        help=f"days until the Pro grant expires (default {DEFAULT_PRO_DAYS}, longer than the beta)",
    )
    parser.add_argument(
        "--entitlement", default=None,
        help="the RevenueCat entitlement id (entl...) to grant; default is REVENUECAT_PRO_ENTITLEMENT_ID in workers/scan-proxy/wrangler.toml",
    )
    parser.add_argument(
        "--grant-id", default=DEFAULT_GRANT_ID,
        help=f"names this grant in the idempotency key (default {DEFAULT_GRANT_ID}); use a new one to deposit again on purpose",
    )
    return parser


def _validate(args: argparse.Namespace, env: Mapping[str, str]) -> tuple[str, str]:
    """(account id, secret key), or a GrantError, before any request."""
    account_id = normalise_account_id(args.account_id)
    if not 1 <= args.scans <= MAX_SCANS:
        raise GrantError(f"--scans must be between 1 and {MAX_SCANS}")
    if args.pro_days < 1:
        raise GrantError("--pro-days must be at least 1")
    if not _GRANT_ID_SHAPE.match(args.grant_id):
        raise GrantError("--grant-id may use only letters, digits, dot, dash and underscore (64 at most)")
    key = (env.get(KEY_VAR) or "").strip()
    if not key:
        raise GrantError(f"{KEY_VAR} is not set; put the RevenueCat secret key in that environment variable")
    return account_id, key


def main(
    argv: list[str] | None = None,
    env: Mapping[str, str] | None = None,
    *,
    api_base: str = API_BASE,
    wrangler_path: Path = WRANGLER,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    out: TextIO | None = None,
    err: TextIO | None = None,
) -> int:
    out = out or sys.stdout
    err = err or sys.stderr
    env = os.environ if env is None else env
    args = build_parser().parse_args(argv)
    key = (env.get(KEY_VAR) or "").strip()
    client = Client(api_base, key)

    def fail(text: str) -> int:
        print(f"error: {client.scrub(text)}", file=err)
        return 1

    try:
        account_id, key = _validate(args, env)
        project_id, currency, wrangler_entitlement = read_wrangler_vars(wrangler_path)
    except GrantError as problem:
        return fail(str(problem))

    entitlement = args.entitlement or wrangler_entitlement
    expires_at = now() + timedelta(days=args.pro_days)
    expires_ms = int(expires_at.timestamp() * 1000)
    idempotency_key = f"tester-grant-{args.grant_id}-{account_id}"
    customer = f"/projects/{project_id}/customers/{urllib.parse.quote(account_id, safe='')}"

    print(f"{'APPLY' if args.apply else 'DRY RUN (nothing is sent; add --apply to do it)'}", file=out)
    print(f"  account id : {account_id}", file=out)
    print(f"  Pro        : entitlement '{entitlement}' until {expires_at:%Y-%m-%d} UTC ({args.pro_days} days)", file=out)
    print(f"  scans      : +{args.scans} {currency}", file=out)
    print(f"  project    : {project_id}", file=out)
    print(f"  idempotency: {idempotency_key}", file=out)
    if not args.apply:
        return 0

    try:
        status, body = client.post(
            f"{customer}/actions/grant_entitlement",
            {"entitlement_id": entitlement, "expires_at": expires_ms},
        )
        if 200 <= status < 300:
            print(f"  ok   Pro granted until {expires_at:%Y-%m-%d} UTC", file=out)
        elif status == 409:
            print(
                f"  note Pro not changed: RevenueCat answered 409 ({client.scrub(_message(body))}); "
                "usually Pro was already granted within the last two hours. Carrying on to the scans.",
                file=out,
            )
        else:
            return fail(_step_failure("Pro grant", status, body, "customer_information:customers:read_write"))

        status, body = client.post(
            f"{customer}/virtual_currencies/transactions",
            {"adjustments": {currency: args.scans}, "reference": idempotency_key},
            idempotency_key,
        )
        if 200 <= status < 300:
            print(
                f"  ok   +{args.scans} {currency} deposited (a repeat with the same --grant-id is applied once)",
                file=out,
            )
        else:
            return fail(_step_failure("scan deposit", status, body, "customer_information:purchases:read_write"))
    except GrantError as problem:
        return fail(str(problem))
    return 0


def _step_failure(step: str, status: int, body: object, permission: str) -> str:
    text = f"{step} failed: HTTP {status} ({_message(body)})"
    if status in (401, 403):
        text += f". The key in {KEY_VAR} needs the permission {permission}."
    elif status == 404:
        text += ". Check the account id (RevenueCat creates the customer when the app first logs in) and, for Pro, REVENUECAT_PRO_ENTITLEMENT_ID in workers/scan-proxy/wrangler.toml."
    return text


if __name__ == "__main__":
    sys.exit(main())
