import assert from "node:assert/strict";
import { Buffer } from "node:buffer";
import test from "node:test";
import { base64urlToBytes, decodeJwt, decodeJwtPart } from "./jwt.ts";

const encode = (value: unknown) => Buffer.from(JSON.stringify(value)).toString("base64url");

test("decodes a base64url JSON part, including characters outside ASCII", () => {
  assert.deepEqual(decodeJwtPart(encode({ name: "Zoë", n: 1 })), { name: "Zoë", n: 1 });
});

test("an empty, missing, non-base64url or non-JSON part decodes to undefined, never throws", () => {
  assert.equal(decodeJwtPart(undefined), undefined);
  assert.equal(decodeJwtPart(""), undefined);
  assert.equal(decodeJwtPart("%%%"), undefined);
  assert.equal(decodeJwtPart(Buffer.from("not json").toString("base64url")), undefined);
});

test("decodeJwt returns the header and claims of a token and ignores the signature", () => {
  const token = `${encode({ alg: "ES256", kid: "k" })}.${encode({ sub: "u" })}.sig`;
  assert.deepEqual(decodeJwt(token), { header: { alg: "ES256", kid: "k" }, claims: { sub: "u" } });
  assert.deepEqual(decodeJwt("garbage"), { header: undefined, claims: undefined });
});

test("base64urlToBytes decodes unpadded input and rejects characters outside the alphabet", () => {
  assert.deepEqual([...base64urlToBytes("_-8")], [255, 239]);
  assert.throws(() => base64urlToBytes("a+b"), /not base64url/);
});
