import "./requireInstall.ts";
import assert from "node:assert/strict";
import test from "node:test";
import { installMessage, missingDependencies } from "./installGuard.ts";

const resolvesNothing = () => {
  throw new Error("Cannot find package");
};

test("[sanity] reports every runtime dependency the resolver cannot find", () => {
  const missing = missingDependencies({ "@anthropic-ai/sdk": "^0.71.0" }, resolvesNothing);
  assert.deepEqual(missing, ["@anthropic-ai/sdk"]);
});

test("[sanity] reports nothing when every dependency resolves", () => {
  assert.deepEqual(missingDependencies({ "@anthropic-ai/sdk": "^0.71.0" }, () => "file:///ok"), []);
});

test("[sanity] only the dependencies that fail to resolve are reported", () => {
  const resolver = (name: string) => {
    if (name === "b") throw new Error("missing");
    return "file:///ok";
  };
  assert.deepEqual(missingDependencies({ a: "1", b: "1", c: "1" }, resolver), ["b"]);
});

test("[sanity] the message names the missing package and the exact install command", () => {
  const message = installMessage(["@anthropic-ai/sdk"]);
  assert.match(message, /@anthropic-ai\/sdk/);
  assert.match(message, /npm install/);
  assert.match(message, /workers\/scan-proxy/);
  assert.match(message, /npm --prefix workers\/scan-proxy install/);
});

test("[sanity] with the real install present, the real dependencies all resolve", () => {
  // Reaching this line already proves the guard passed at import time; this pins the
  // pure function against the real package.json so a renamed dependency is noticed.
  assert.deepEqual(missingDependencies(undefined, undefined), []);
});
