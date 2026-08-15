import Anthropic from "@anthropic-ai/sdk";
import type { DocTypeConfig } from "./docTypes.ts";
import type { MediaType } from "./types.ts";

// Haiku 4.5 — structured field extraction from a printed label is squarely
// its use case, and it's the cheapest tier (~$0.01/scan vs ~$0.03 on
// Sonnet 5). See NEXT_STEPS.md's monetization thread for the cost baseline.
const MODEL = "claude-haiku-4-5-20251001";

export async function extractFields(
  apiKey: string,
  imageBase64: string,
  mediaType: MediaType,
  config: DocTypeConfig,
): Promise<Record<string, unknown>> {
  const client = new Anthropic({ apiKey });

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
