import { verifyAccountToken } from "./auth.ts";
import type { DocType } from "./docTypes.ts";
import { badRequest, json, preflight, withCors } from "./http.ts";
import { parseScanRequest } from "./request.ts";
import { runScan } from "./scan.ts";
import { logScanResponse, logScanThrew } from "./scanLog.ts";
import type { Env } from "./types.ts";

// The document type is null until the body has been read and validated.
async function scanResponse(request: Request, env: Env): Promise<{ response: Response; docType: DocType | null }> {
  // Authenticate before reading the body or spending anything: the account
  // charged is the token's, never one the caller names.
  const auth = await verifyAccountToken(env, request.headers.get("Authorization"));
  if (!auth.ok) {
    console.error("account token rejected:", auth.reason);
    if (auth.unavailable) {
      return {
        response: json({ ok: false, code: "auth_unavailable", message: "Could not verify your account right now." }, 503),
        docType: null,
      };
    }
    return {
      response: json({ ok: false, code: "unauthorized", message: "Missing or invalid account token." }, 401),
      docType: null,
    };
  }

  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return { response: badRequest("Body must be valid JSON."), docType: null };
  }

  const parsed = parseScanRequest(payload);
  if (typeof parsed === "string") {
    return { response: badRequest(parsed), docType: null };
  }

  return { response: await runScan(env, auth.userId, parsed), docType: parsed.doc_type };
}

// Every POST /v1/scan, whatever happens to it, writes one scan log line
// (scanLog.ts); nothing else the Worker serves does.
async function handleScan(request: Request, env: Env): Promise<Response> {
  const startedAt = Date.now();
  let scanned: Awaited<ReturnType<typeof scanResponse>>;
  try {
    scanned = await scanResponse(request, env);
  } catch (err) {
    logScanThrew(null, startedAt);
    throw err;
  }
  await logScanResponse(scanned.response, scanned.docType, startedAt);
  return scanned.response;
}

async function route(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);

  if (request.method === "OPTIONS" && url.pathname === "/v1/scan") {
    return preflight();
  }

  if (request.method === "POST" && url.pathname === "/v1/scan") {
    return handleScan(request, env);
  }

  return json({ ok: false, code: "not_found", message: "POST /v1/scan only." }, 404);
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    return withCors(await route(request, env));
  },
};
