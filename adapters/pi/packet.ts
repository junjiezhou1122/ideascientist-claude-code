import { Type, type Static } from "typebox";
import { Value } from "typebox/value";

export const roles = ["orchestrator", "gap-finder", "innovator", "reviewer", "report-writer", "paper-reader", "blind-baseline"] as const;
const paths = Type.Array(Type.String({ minLength: 1 }), { maxItems: 40 });
export const RolePacketSchema = Type.Object({
  role: Type.Union(roles.map((role) => Type.Literal(role))),
  plugin_root: Type.String({ minLength: 1 }),
  run_directory: Type.String({ minLength: 1 }),
  task_id: Type.String({ pattern: "^T[0-9]{3,}$" }),
  target_ids: Type.Array(Type.String({ pattern: "^[AGCP][0-9]{3,}$" }), { maxItems: 12 }),
  input_files: paths,
  output_files: paths,
  instruction: Type.String({ minLength: 1, maxLength: 12000 }),
  cutoff: Type.Union([Type.Null(), Type.String({ pattern: "^[0-9]{4}-[0-9]{2}-[0-9]{2}$" })]),
  allowances: Type.Object({
    searches: Type.Integer({ minimum: 0, maximum: 10 }),
    reader_calls: Type.Integer({ minimum: 0, maximum: 6 }),
  }, { additionalProperties: false }),
  readers: Type.Array(Type.Object({
    paper_id: Type.String({ pattern: "^P[0-9]{3,}$" }),
    identity: Type.String({ minLength: 1, maxLength: 6000 }),
    source: Type.String({ minLength: 1 }),
    goals: Type.Array(Type.String({ minLength: 1 }), { minItems: 1, maxItems: 5 }),
    digest_path: Type.String({ minLength: 1 }),
  }, { additionalProperties: false }), { maxItems: 6 }),
}, { additionalProperties: false });
export type RolePacket = Static<typeof RolePacketSchema>;
export function parsePacket(value: unknown): RolePacket {
  if (!Value.Check(RolePacketSchema, value)) throw new Error("Invalid RolePacket. Use the ideascientist_agent tool schema.");
  return value;
}

export const capabilities = {
  orchestrator: ["read", "write", "edit"],
  "gap-finder": ["read", "write", "edit", "search", "reader"],
  innovator: ["read", "write", "edit", "search", "reader"],
  reviewer: ["read", "write", "edit", "search", "reader"],
  "report-writer": ["read", "write", "edit", "search", "reader"],
  "paper-reader": ["read", "write", "edit", "fetch"],
  "blind-baseline": ["read", "write", "edit"],
} satisfies Record<RolePacket["role"], readonly string[]>;

export const CompletionSchema = Type.Union([
  Type.Object({ status: Type.Literal("done"), artifact_paths: paths }, { additionalProperties: false }),
  Type.Object({ status: Type.Literal("needs_registration"), discovery_path: Type.String() }, { additionalProperties: false }),
  Type.Object({ status: Type.Literal("reader_relay"), request_path: Type.String() }, { additionalProperties: false }),
  Type.Object({ status: Type.Literal("blocked"), reason: Type.String({ minLength: 1 }) }, { additionalProperties: false }),
]);
export type Completion = Static<typeof CompletionSchema>;
export function parseCompletion(text: string): Completion {
  const value: unknown = JSON.parse(text.replace(/^```(?:json)?\s*|\s*```$/g, "").trim());
  if (!Value.Check(CompletionSchema, value)) throw new Error("Worker did not return the completion contract.");
  return value;
}
