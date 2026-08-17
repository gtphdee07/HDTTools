// System prompts, tool names, and JSON schemas ported directly from the
// desktop CLI's Claude-vision reader modules (src/hdttools/truck_tag.py,
// trailer_tag.py, scale_ticket.py / vision_client.py) so extraction results
// match the same field names the OCR path already produces.
import type Anthropic from "@anthropic-ai/sdk";

export type DocType = "truck_tag" | "trailer_tag" | "scale_ticket";

export interface DocTypeConfig {
  systemPrompt: string;
  toolName: string;
  toolDescription: string;
  schema: Anthropic.Tool.InputSchema;
}

const TIRE_SCHEMA = {
  type: "object",
  properties: {
    tire: { type: ["string", "null"] },
    rim: { type: ["string", "null"] },
    cold_pressure_kpa: { type: ["number", "null"] },
    cold_pressure_psi: { type: ["number", "null"] },
    dual: { type: "boolean" },
  },
  required: ["tire", "rim", "cold_pressure_kpa", "cold_pressure_psi", "dual"],
};

export const DOC_TYPE_CONFIG: Record<DocType, DocTypeConfig> = {
  truck_tag: {
    systemPrompt:
      "You are reading a Ford-style Vehicle Safety Compliance Certification " +
      "label for a truck, mounted on the door jamb. It lists separate Front " +
      "and Rear GAWR values and separate front/rear tire and rim specs. " +
      "Leave a field null if it is not present on the label.",
    toolName: "record_truck_tag",
    toolDescription: "Record the fields extracted from a truck compliance label.",
    schema: {
      type: "object",
      properties: {
        manufacturer: { type: ["string", "null"] },
        date: { type: ["string", "null"] },
        vin: { type: ["string", "null"] },
        vehicle_type: { type: ["string", "null"] },
        gvwr_kg: { type: ["number", "null"] },
        gvwr_lb: { type: ["number", "null"] },
        front_gawr_kg: { type: ["number", "null"] },
        front_gawr_lb: { type: ["number", "null"] },
        rear_gawr_kg: { type: ["number", "null"] },
        rear_gawr_lb: { type: ["number", "null"] },
        front_tire: TIRE_SCHEMA,
        rear_tire: TIRE_SCHEMA,
      },
      required: [
        "manufacturer",
        "date",
        "vin",
        "vehicle_type",
        "gvwr_kg",
        "gvwr_lb",
        "front_gawr_kg",
        "front_gawr_lb",
        "rear_gawr_kg",
        "rear_gawr_lb",
        "front_tire",
        "rear_tire",
      ],
    },
  },

  trailer_tag: {
    systemPrompt:
      "You are reading a Vehicle Safety Compliance Certification label for a " +
      "travel trailer / RV. It lists a single GAWR that applies to each axle " +
      "(not separate front/rear values), and may list a UVW (unloaded vehicle " +
      "weight). Leave a field null if it is not present on the label.",
    toolName: "record_trailer_tag",
    toolDescription: "Record the fields extracted from a trailer compliance label.",
    schema: {
      type: "object",
      properties: {
        manufacturer: { type: ["string", "null"] },
        date: { type: ["string", "null"] },
        vin: { type: ["string", "null"] },
        vehicle_type: { type: ["string", "null"] },
        gvwr_kg: { type: ["number", "null"] },
        gvwr_lb: { type: ["number", "null"] },
        gawr_per_axle_kg: { type: ["number", "null"] },
        gawr_per_axle_lb: { type: ["number", "null"] },
        uvw_kg: { type: ["number", "null"] },
        uvw_lb: { type: ["number", "null"] },
        tire: TIRE_SCHEMA,
      },
      required: [
        "manufacturer",
        "date",
        "vin",
        "vehicle_type",
        "gvwr_kg",
        "gvwr_lb",
        "gawr_per_axle_kg",
        "gawr_per_axle_lb",
        "uvw_kg",
        "uvw_lb",
        "tire",
      ],
    },
  },

  scale_ticket: {
    systemPrompt:
      "You are reading a truck weigh scale ticket (e.g. a CAT Scale ticket). " +
      "Extract the fields exactly as printed. Weights are in pounds unless " +
      "otherwise noted. Leave a field null if it is not present on the ticket.",
    toolName: "record_scale_ticket",
    toolDescription: "Record the fields extracted from a weigh scale ticket.",
    schema: {
      type: "object",
      properties: {
        ticket_number: { type: ["string", "null"] },
        weigh_number: { type: ["string", "null"] },
        date: { type: ["string", "null"] },
        time: { type: ["string", "null"] },
        scale_number: { type: ["string", "null"] },
        location_name: { type: ["string", "null"] },
        location_address: { type: ["string", "null"] },
        city: { type: ["string", "null"] },
        state: { type: ["string", "null"] },
        steer_axle_lb: { type: ["number", "null"] },
        drive_axle_lb: { type: ["number", "null"] },
        trailer_axle_lb: { type: ["number", "null"] },
        gross_weight_lb: { type: ["number", "null"] },
        company: { type: ["string", "null"] },
        commodity: { type: ["string", "null"] },
        tractor_number: { type: ["string", "null"] },
        trailer_number: { type: ["string", "null"] },
      },
      required: [
        "ticket_number",
        "weigh_number",
        "date",
        "time",
        "scale_number",
        "location_name",
        "location_address",
        "city",
        "state",
        "steer_axle_lb",
        "drive_axle_lb",
        "trailer_axle_lb",
        "gross_weight_lb",
        "company",
        "commodity",
        "tractor_number",
        "trailer_number",
      ],
    },
  },
};
