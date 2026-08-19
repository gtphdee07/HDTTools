import assert from "node:assert/strict";
import test from "node:test";
import { badRequest, json } from "./http.ts";

test("[sanity] json() defaults to status 200 with a JSON content-type", async () => {
  const res = json({ ok: true });
  assert.equal(res.status, 200);
  assert.equal(res.headers.get("Content-Type"), "application/json");
  assert.deepEqual(await res.json(), { ok: true });
});

test("json() uses the given status when provided", () => {
  const res = json({ ok: false }, 404);
  assert.equal(res.status, 404);
});

test("json() round-trips nested objects, arrays, and nulls unchanged", async () => {
  const body = {
    ok: true,
    doc_type: "truck_tag",
    fields: { manufacturer: "Ford", tire: { tire: null, dual: false }, list: [1, 2, 3] },
  };
  const res = json(body);
  assert.deepEqual(await res.json(), body);
});

test("badRequest() returns the exact ok:false/bad_request envelope at 400", async () => {
  const res = badRequest("Body must be valid JSON.");
  assert.equal(res.status, 400);
  assert.equal(res.headers.get("Content-Type"), "application/json");
  assert.deepEqual(await res.json(), {
    ok: false,
    code: "bad_request",
    message: "Body must be valid JSON.",
  });
});
