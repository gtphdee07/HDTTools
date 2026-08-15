import { badRequest, json } from "./http.ts";
import { parseScanRequest } from "./request.ts";
import { runScan } from "./scan.ts";
import type { Env } from "./types.ts";

async function handleScan(request: Request, env: Env): Promise<Response> {
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

  return runScan(env, parsed);
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
