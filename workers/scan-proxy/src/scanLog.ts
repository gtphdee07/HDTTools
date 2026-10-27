// The one structured log line every POST /v1/scan writes, which Cloudflare
// Workers Logs (wrangler.toml, [observability]) stores and lets the owner
// filter by field. It says what happened and nothing about who: no account id,
// token, image, key or email ever goes in (owner decision, #183) - a report is
// traced by time. Only fields chosen here are written, never a request or
// response object, so a new field has to be added on purpose.
import type { DocType } from "./docTypes.ts";

const DELIVERED = "delivered";
const INTERNAL_ERROR = "internal_error";

interface ScanLogLine {
  event: "scan";
  // "delivered", or the error code the client received (the `code` of the
  // response body), so the line always agrees with what the app saw.
  outcome: string;
  // Null when the request failed before its document type was known.
  doc_type: DocType | null;
  duration_ms: number;
  // True only when a charged scan failed and the credit went back. A scan that
  // failed before charging has nothing to refund, so it is false too.
  refunded: boolean;
}

// "extraction_failed" is the one code whose response says the credit was
// refunded (scan.ts); "extraction_failed_no_refund" says it was not.
function wasRefunded(outcome: string): boolean {
  return outcome === "extraction_failed";
}

// The outcome of a response this Worker built: its JSON body is
// { ok: true, ... } or { ok: false, code, ... } (http.ts, scan.ts, index.ts).
async function outcomeOf(response: Response): Promise<string> {
  try {
    const body = (await response.clone().json()) as { ok?: unknown; code?: unknown };
    if (body.ok === true) return DELIVERED;
    if (typeof body.code === "string") return body.code;
  } catch {
    // Not JSON: fall through to the unknown outcome.
  }
  return "unknown";
}

function scanLogLine(outcome: string, docType: DocType | null, durationMs: number): ScanLogLine {
  return { event: "scan", outcome, doc_type: docType, duration_ms: durationMs, refunded: wasRefunded(outcome) };
}

// console.error for every outcome but a delivered scan, so the dashboard's
// level filter finds the failures.
function write(line: ScanLogLine): void {
  const text = JSON.stringify(line);
  if (line.outcome === DELIVERED) console.log(text);
  else console.error(text);
}

export async function logScanResponse(response: Response, docType: DocType | null, startedAt: number): Promise<void> {
  write(scanLogLine(await outcomeOf(response), docType, Date.now() - startedAt));
}

export function logScanThrew(docType: DocType | null, startedAt: number): void {
  write(scanLogLine(INTERNAL_ERROR, docType, Date.now() - startedAt));
}
