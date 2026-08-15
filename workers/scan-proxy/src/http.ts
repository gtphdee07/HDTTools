export function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export function badRequest(message: string): Response {
  return json({ ok: false, code: "bad_request", message }, 400);
}
