import Anthropic from "@anthropic-ai/sdk";
import type { DocTypeConfig } from "./docTypes.ts";
import type { MediaType } from "./types.ts";

// Sonnet 5, not the cheaper Haiku 4.5 this used to be pinned to (~$0.01/scan
// vs ~$0.03) - confirmed for real 2026-08-25 that Haiku 4.5 is not reliable
// enough for this task: it returned confident, non-deterministic, WRONG
// GVWR/GAWR numbers for AddieTag.jpg (the easiest, previously-"known good"
// fixture) on two separate real calls, even with a fresh redeploy ruling out
// a stale-Worker artifact. A direct call to claude-sonnet-5 with the exact
// same prompt/schema/image got every field exactly right. See NEXT_STEPS.md
// item #13 / ARCHIVE_MONETIZATION.md for the full real-call evidence.
const MODEL = "claude-sonnet-5";

// Must be shorter than Android's own ScanApiClient 60s readTimeout, or a
// timeout here would never actually fire before the app's own client had
// already given up and shown its own error.
export const ANTHROPIC_TIMEOUT_MS = 20_000;

export async function extractFields(
  apiKey: string,
  imageBase64: string,
  mediaType: MediaType,
  config: DocTypeConfig,
): Promise<Record<string, unknown>> {
  const client = new Anthropic({ apiKey, timeout: ANTHROPIC_TIMEOUT_MS });

  const response = await client.messages.create({
    model: MODEL,
    max_tokens: 1024,
    system: config.systemPrompt,
    tools: [
      {
        name: config.toolName,
        description: config.toolDescription,
        input_schema: config.schema,
      },
    ],
    tool_choice: { type: "tool", name: config.toolName },
    messages: [
      {
        role: "user",
        content: [
          {
            type: "image",
            source: { type: "base64", media_type: mediaType, data: imageBase64 },
          },
          { type: "text", text: "Extract the requested fields from this image." },
        ],
      },
    ],
  });

  for (const block of response.content) {
    if (block.type === "tool_use" && block.name === config.toolName) {
      return block.input as Record<string, unknown>;
    }
  }

  throw new Error("Claude did not return the expected structured data.");
}
