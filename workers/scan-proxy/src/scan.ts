// The money-critical control flow: charge, then extract, then refund on
// failure. Deps are injectable so this can be unit-tested without the real
// Anthropic SDK or a network call to RevenueCat — see scan.test.ts.
import { DOC_TYPE_CONFIG } from "./docTypes.ts";
import { json } from "./http.ts";
import type { ScanRequest } from "./request.ts";
import { refundCredit, spendCredit } from "./revenuecat.ts";
import type { Env } from "./types.ts";
// Type-only — doesn't pull in claude.ts (and the Anthropic SDK it imports)
// at module-load time. See defaultExtractFields below for the real link.
import type { extractFields as ExtractFields } from "./claude.ts";

export interface ScanDeps {
  spendCredit: typeof spendCredit;
  refundCredit: typeof refundCredit;
  extractFields: typeof ExtractFields;
}

// Loads claude.ts (and @anthropic-ai/sdk) only when a real scan actually
// runs, not when this module is imported — so runScan and its tests work
// without the SDK installed, while the real Worker still gets it lazily on
// first use.
const defaultExtractFields: typeof ExtractFields = async (...args) => {
  const { extractFields } = await import("./claude.ts");
  return extractFields(...args);
};

export const defaultScanDeps: ScanDeps = {
  spendCredit,
  refundCredit,
  extractFields: defaultExtractFields,
};

export async function runScan(
  env: Env,
  request: ScanRequest,
  deps: ScanDeps = defaultScanDeps,
): Promise<Response> {
  const idempotencyKey = crypto.randomUUID();

  // Spend the credit before doing anything costly. RevenueCat's 422 on
  // insufficient balance doubles as the entitlement check, so a user with
  // no credits never triggers a Claude call (which we'd be paying for).
  const spend = await deps.spendCredit(env, request.app_user_id, idempotencyKey);
  if (!spend.ok) {
    if (spend.status === 422) {
      return json(
        { ok: false, code: "insufficient_credits", message: "Not enough scan credits." },
        402,
      );
    }
    return json(
      { ok: false, code: "billing_error", message: "Could not verify scan credits." },
      502,
    );
  }

  try {
    const config = DOC_TYPE_CONFIG[request.doc_type];
    const fields = await deps.extractFields(
      env.ANTHROPIC_API_KEY,
      request.image_base64,
      request.media_type,
      config,
    );
    return json({ ok: true, doc_type: request.doc_type, fields });
  } catch {
    // Charged but couldn't deliver — refund so the user isn't billed for a
    // failed scan (e.g. Claude API error, an unreadable photo).
    await deps.refundCredit(env, request.app_user_id, idempotencyKey).catch(() => {});
    return json(
      { ok: false, code: "extraction_failed", message: "Could not read the image. Credit refunded." },
      502,
    );
  }
}
