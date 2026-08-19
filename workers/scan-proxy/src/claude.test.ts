// Mocks the real Anthropic HTTP endpoint via fetch (same technique
// revenuecat.test.ts uses) rather than reaching into the SDK's internals -
// extractFields is the only module that touches the real @anthropic-ai/sdk,
// and scan.ts deliberately isolates it behind an injectable dependency so
// scan.test.ts never has to go near it. This file is the SDK's own coverage.
import assert from "node:assert/strict";
import test from "node:test";
import { DOC_TYPE_CONFIG } from "./docTypes.ts";
import { extractFields } from "./claude.ts";

const config = DOC_TYPE_CONFIG.truck_tag;

function messageWithBlocks(content: unknown[]) {
  return {
    id: "msg_test",
    type: "message",
    role: "assistant",
    model: "claude-haiku-4-5-20251001",
    content,
    stop_reason: "tool_use",
    stop_sequence: null,
    usage: { input_tokens: 100, output_tokens: 50 },
  };
}

function toolUseBlock(input: Record<string, unknown>, name = config.toolName) {
  return { type: "tool_use", id: "toolu_test", name, input };
}

// The Anthropic SDK keys its response parsing off Content-Type - a mocked
// Response without this header gets treated as non-JSON and never reaches
// extractFields' own logic at all.
function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

test("[sanity] extracts fields from a matching tool_use block", async (t) => {
  let capturedUrl: string | undefined;
  let capturedBody: Record<string, unknown> | undefined;
  t.mock.method(globalThis, "fetch", async (url: string | URL, init?: RequestInit) => {
    capturedUrl = String(url);
    capturedBody = JSON.parse(init?.body as string);
    return jsonResponse(messageWithBlocks([toolUseBlock({ manufacturer: "Ford" })]));
  });

  const fields = await extractFields("sk-ant-test", "aGVsbG8=", "image/jpeg", config);

  assert.deepEqual(fields, { manufacturer: "Ford" });
  assert.equal(capturedUrl, "https://api.anthropic.com/v1/messages");
  assert.equal(capturedBody?.model, "claude-haiku-4-5-20251001");
  assert.deepEqual(capturedBody?.tool_choice, { type: "tool", name: config.toolName });
  assert.equal((capturedBody?.tools as Array<{ name: string }>)[0].name, config.toolName);

  type ContentBlock = { type: string; source?: { media_type: string; data: string } };
  const userMessage = (capturedBody?.messages as Array<{ content: ContentBlock[] }>)[0];
  const imageBlock = userMessage.content.find((block) => block.type === "image");
  assert.ok(imageBlock?.source, "expected an image content block with a source");
  assert.equal(imageBlock.source.media_type, "image/jpeg");
  assert.equal(imageBlock.source.data, "aGVsbG8=");
});

// This is the branch scan.ts's entire refund path exists to handle - if
// this ever silently stopped throwing, a failed extraction would look like
// a successful one with empty fields instead of triggering a refund.
test("throws when no content block matches the requested tool", async (t) => {
  t.mock.method(globalThis, "fetch", async () =>
    jsonResponse(messageWithBlocks([{ type: "text", text: "I can't read this label." }])),
  );

  await assert.rejects(
    () => extractFields("sk-ant-test", "aGVsbG8=", "image/jpeg", config),
    /did not return the expected structured data/,
  );
});

test("finds the matching tool_use block even when a non-matching block comes first", async (t) => {
  t.mock.method(globalThis, "fetch", async () =>
    jsonResponse(
      messageWithBlocks([
        { type: "text", text: "Here are the fields:" },
        toolUseBlock({ manufacturer: "Brinkley RV" }),
      ]),
    ),
  );

  const fields = await extractFields("sk-ant-test", "aGVsbG8=", "image/jpeg", config);
  assert.deepEqual(fields, { manufacturer: "Brinkley RV" });
});

test("a tool_use block with a different tool name is not accepted", async (t) => {
  t.mock.method(globalThis, "fetch", async () =>
    jsonResponse(messageWithBlocks([toolUseBlock({ manufacturer: "Ford" }, "some_other_tool")])),
  );

  await assert.rejects(() => extractFields("sk-ant-test", "aGVsbG8=", "image/jpeg", config));
});
