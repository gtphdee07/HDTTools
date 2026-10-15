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

// One attempt, no more. The SDK's default of 2 retries (on timeouts, 408, 409,
// 429 and every 5xx, and honouring a Retry-After of up to 60 s per wait)
// stretched a Scan to about 87 s at best and to no real limit at worst, past
// Android's 60 s read timeout. A failed attempt already refunds the credit and
// the user can try again at no charge, so a silent retry buys little. See
// CONTEXT.md "Time limits" for the arithmetic, and timeLimits.test.ts, which
// fails if the Worker's worst case reaches a client's limit.
export const ANTHROPIC_MAX_RETRIES = 0;

// One attempt's limit. Together with ANTHROPIC_MAX_RETRIES it must keep the
// Worker's whole worst case under Android's 60 s readTimeout, or the app gives
// up on a Scan the Worker then finishes and charges for.
export const ANTHROPIC_TIMEOUT_MS = 20_000;

export async function extractFields(
  apiKey: string,
  imageBase64: string,
  mediaType: MediaType,
  config: DocTypeConfig,
): Promise<Record<string, unknown>> {
  const client = new Anthropic({ apiKey, timeout: ANTHROPIC_TIMEOUT_MS, maxRetries: ANTHROPIC_MAX_RETRIES });

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
