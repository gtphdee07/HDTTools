export function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

// The Web app calls this Worker from the browser, from another origin. The
// account token travels in the Authorization header, never a cookie, so any
// origin may call: the token is what authorises, and the browser's origin
// check adds nothing here.
const CORS_HEADERS: Record<string, string> = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Authorization, Content-Type",
  "Access-Control-Max-Age": "86400",
};

export function preflight(): Response {
  return new Response(null, { status: 204, headers: CORS_HEADERS });
}

// Lets a browser page read the response, errors included.
export function withCors(response: Response): Response {
  const headers = new Headers(response.headers);
  headers.set("Access-Control-Allow-Origin", CORS_HEADERS["Access-Control-Allow-Origin"]);
  return new Response(response.body, { status: response.status, statusText: response.statusText, headers });
}

export function badRequest(message: string): Response {
  return json({ ok: false, code: "bad_request", message }, 400);
}
