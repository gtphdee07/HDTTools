// The money-critical control flow: charge, then extract, then refund on
// failure. Deps are injectable so this can be unit-tested without the real
// Anthropic SDK or a network call to RevenueCat — see scan.test.ts.
import { DOC_TYPE_CONFIG } from "./docTypes.ts";
import { json } from "./http.ts";
import type { ScanRequest } from "./request.ts";
import { refundCredit, spendCredit, type TransactionResult } from "./revenuecat.ts";
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

const defaultScanDeps: ScanDeps = {
  spendCredit,
  refundCredit,
  extractFields: defaultExtractFields,
};

export async function runScan(
  env: Env,
  request: ScanRequest,
  deps: ScanDeps = defaultScanDeps,
): Promise<Response> {
  // A client-supplied id (stable across retries of the same logical scan
  // attempt) makes the RevenueCat spend/refund idempotent across a lost or
  // timed-out response; falling back to a fresh random key when absent
  // matches today's behavior for any caller that doesn't send one yet.
  const idempotencyKey = request.client_request_id ?? crypto.randomUUID();

  // Spend the credit before doing anything costly. RevenueCat's 422 on
  // insufficient balance doubles as the entitlement check, so a user with
  // no credits never triggers a Claude call (which we'd be paying for).
  // A thrown rejection (RevenueCat unreachable, or its own timeout firing)
  // is mapped to the same billing_error response as a non-ok status, so a
  // hung upstream still returns a clean bounded error instead of failing
  // the whole request ungracefully.
  let spend: TransactionResult;
  try {
    spend = await deps.spendCredit(env, request.app_user_id, idempotencyKey);
  } catch (err) {
    console.error("spendCredit threw", err);
    return json(
      { ok: false, code: "billing_error", message: "Could not verify scan credits." },
      502,
    );
  }
  if (!spend.ok) {
    console.error("spendCredit failed", spend.status, JSON.stringify(spend.body));
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
    // failed scan (e.g. Claude API error, an unreadable photo). The refund
    // call itself can fail too (RevenueCat unreachable, etc.) - the response
    // message must reflect what actually happened, not claim a refund that
    // didn't go through.
    const refund = await deps
      .refundCredit(env, request.app_user_id, idempotencyKey)
      .catch(() => null);

    if (refund?.ok) {
      return json(
        { ok: false, code: "extraction_failed", message: "Could not read the image. Credit refunded." },
        502,
      );
    }

    console.error("refundCredit failed after a charged scan", request.app_user_id, idempotencyKey);
    return json(
      {
        ok: false,
        code: "extraction_failed_no_refund",
        message:
          "Could not read the image, and we weren't able to automatically refund your credit. " +
          "Please contact support if this keeps happening.",
      },
      502,
    );
  }
}
