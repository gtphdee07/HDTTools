// The cases the Claude vision External test runs, from the one file both sides
// share (test-vectors/vision_external_cases.json; the Python side reads it in
// scripts/vision_cases.py). Each case names an image in ExampleDocs/ and the
// entry in the "photos" section of ExampleDocs/golden_fields.json that holds
// its expected field values and known_ocr_limitations, so the expected values
// live in one place. A mismatch on a field named in known_ocr_limitations is
// tolerated; any other mismatch fails (the same rule the Python test applies).
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type { DocType } from "./docTypes.ts";
import type { MediaType } from "./types.ts";

export const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const EXAMPLE_DOCS = path.join(REPO_ROOT, "ExampleDocs");

export interface VisionCase {
  docType: DocType;
  image: string;
  golden: string;
  imagePath: string;
  mediaType: MediaType;
  fields: Record<string, unknown>;
  knownOcrLimitations: Record<string, string>;
}

interface GoldenPhoto {
  fields: Record<string, unknown>;
  known_ocr_limitations?: Record<string, string>;
}

const MEDIA_TYPES: Record<string, MediaType> = {
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".png": "image/png",
};

function mediaTypeOf(image: string): MediaType {
  return MEDIA_TYPES[path.extname(image).toLowerCase()] ?? "image/jpeg";
}

/** Every case in the shared file, with its expected values from golden_fields.json.
 *  A case whose golden entry is missing throws, naming it. */
export function loadVisionCases(): VisionCase[] {
  const shared = JSON.parse(readFileSync(path.join(REPO_ROOT, "test-vectors", "vision_external_cases.json"), "utf8")) as {
    cases: { doc_type: DocType; image: string; golden: string }[];
  };
  const photos = (JSON.parse(readFileSync(path.join(EXAMPLE_DOCS, "golden_fields.json"), "utf8")) as {
    photos: Record<string, GoldenPhoto>;
  }).photos;
  return shared.cases.map((raw) => {
    const photo = photos[raw.golden];
    if (!photo) throw new Error(`golden_fields.json has no photos entry "${raw.golden}" (case ${raw.doc_type})`);
    return {
      docType: raw.doc_type,
      image: raw.image,
      golden: raw.golden,
      imagePath: path.join(EXAMPLE_DOCS, raw.image),
      mediaType: mediaTypeOf(raw.image),
      fields: photo.fields,
      knownOcrLimitations: photo.known_ocr_limitations ?? {},
    };
  });
}

/** Fields whose extracted value differs from the golden value, other than the ones the golden
 *  entry documents in known_ocr_limitations: { field: { got, expected } }. */
export function newMismatches(
  visionCase: Pick<VisionCase, "fields" | "knownOcrLimitations">,
  extracted: Record<string, unknown>,
): Record<string, { got: unknown; expected: unknown }> {
  const mismatches: Record<string, { got: unknown; expected: unknown }> = {};
  for (const [name, expected] of Object.entries(visionCase.fields)) {
    if (extracted[name] === expected || name in visionCase.knownOcrLimitations) continue;
    mismatches[name] = { got: extracted[name], expected };
  }
  return mismatches;
}
