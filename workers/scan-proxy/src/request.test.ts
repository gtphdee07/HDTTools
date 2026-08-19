import assert from "node:assert/strict";
import test from "node:test";
import { parseScanRequest } from "./request.ts";

const validBody = {
  app_user_id: "user-123",
  doc_type: "truck_tag",
  image_base64: "aGVsbG8=",
  media_type: "image/png",
};

test("[sanity] parses a fully valid request", () => {
  assert.deepEqual(parseScanRequest(validBody), validBody);
});

test("defaults media_type to image/jpeg when omitted", () => {
  const { media_type: _media_type, ...rest } = validBody;
  const result = parseScanRequest(rest);
  assert.equal(typeof result, "object");
  assert.equal((result as { media_type: string }).media_type, "image/jpeg");
});

test("rejects a non-object body", () => {
  assert.match(parseScanRequest("nope") as string, /JSON object/);
  assert.match(parseScanRequest(null) as string, /JSON object/);
  assert.match(parseScanRequest(42) as string, /JSON object/);
});

test("rejects a missing or blank app_user_id", () => {
  assert.match(parseScanRequest({ ...validBody, app_user_id: "" }) as string, /app_user_id/);
  assert.match(parseScanRequest({ ...validBody, app_user_id: "   " }) as string, /app_user_id/);
  const { app_user_id: _app_user_id, ...rest } = validBody;
  assert.match(parseScanRequest(rest) as string, /app_user_id/);
});

test("rejects an invalid doc_type", () => {
  assert.match(parseScanRequest({ ...validBody, doc_type: "passport" }) as string, /doc_type/);
  const { doc_type: _doc_type, ...rest } = validBody;
  assert.match(parseScanRequest(rest) as string, /doc_type/);
});

test("rejects a missing image_base64", () => {
  assert.match(parseScanRequest({ ...validBody, image_base64: "" }) as string, /image_base64/);
  const { image_base64: _image_base64, ...rest } = validBody;
  assert.match(parseScanRequest(rest) as string, /image_base64/, "key absent entirely, not just empty");
});

test("rejects an unsupported media_type", () => {
  assert.match(parseScanRequest({ ...validBody, media_type: "image/heic" }) as string, /media_type/);
});

test("rejects wrong-typed fields, not just wrong/missing values", () => {
  assert.match(parseScanRequest({ ...validBody, app_user_id: 123 }) as string, /app_user_id/);
  assert.match(parseScanRequest({ ...validBody, doc_type: 42 }) as string, /doc_type/);
  assert.match(parseScanRequest({ ...validBody, doc_type: ["truck_tag"] }) as string, /doc_type/);
  assert.match(parseScanRequest({ ...validBody, image_base64: 123 }) as string, /image_base64/);
});

test("an explicit null media_type is treated the same as an omitted one", () => {
  const result = parseScanRequest({ ...validBody, media_type: null });
  assert.equal(typeof result, "object");
  assert.equal((result as { media_type: string }).media_type, "image/jpeg");
});

test("rejects an array payload the same way as any other non-conforming object", () => {
  assert.match(parseScanRequest([]) as string, /app_user_id/);
  assert.match(parseScanRequest(["truck_tag"]) as string, /app_user_id/);
});

test("silently ignores unknown extra fields rather than rejecting them", () => {
  const result = parseScanRequest({ ...validBody, extra_field: "should be ignored", another: 42 });
  assert.deepEqual(result, validBody);
});
