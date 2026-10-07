import { verifyAccountToken } from "./auth.ts";
import { badRequest, json } from "./http.ts";
import { parseScanRequest } from "./request.ts";
import { runScan } from "./scan.ts";
import type { Env } from "./types.ts";

async function handleScan(request: Request, env: Env): Promise<Response> {
  // Authenticate before reading the body or spending anything: the account
  // charged is the token's, never one the caller names.
  const auth = await verifyAccountToken(env, request.headers.get("Authorization"));
  if (!auth.ok) {
    console.error("account token rejected:", auth.reason);
    if (auth.unavailable) {
      return json({ ok: false, code: "auth_unavailable", message: "Could not verify your account right now." }, 503);
    }
    return json({ ok: false, code: "unauthorized", message: "Missing or invalid account token." }, 401);
  }

  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return badRequest("Body must be valid JSON.");
  }

  const parsed = parseScanRequest(payload);
  if (typeof parsed === "string") {
    return badRequest(parsed);
  }

  return runScan(env, auth.userId, parsed);
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (request.method === "POST" && url.pathname === "/v1/scan") {
      return handleScan(request, env);
    }

    return json({ ok: false, code: "not_found", message: "POST /v1/scan only." }, 404);
  },
};
