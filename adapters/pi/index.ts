import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { RolePacketSchema } from "./packet.js";
import { registerResearchTools } from "./research.js";
import { executeRole } from "./worker.js";

export const pluginRoot = fileURLToPath(new URL("../../", import.meta.url));

export default function ideascientist(pi: ExtensionAPI): void {
  registerResearchTools(pi);
  let busy = false;
  pi.registerTool({
    name: "ideascientist_agent", label: "IdeaScientist role",
    description: "Execute one fresh scientific role with explicit owned paths and already reserved budgets. No parent conversation is inherited. Main coordinator retains all IDs and state. Sequential calls only.",
    parameters: RolePacketSchema, executionMode: "sequential",
    async execute(_id, packet, signal, _onUpdate, ctx) {
      if (busy) return { content: [{ type: "text", text: "IdeaScientist role dispatch is already active." }], details: undefined, isError: true };
      busy = true;
      try {
        const result = await executeRole({
          packet, root: pluginRoot, ctx, signal,
          research: {
            search: process.env.IDEASCIENTIST_PI_SEARCH_TOOL ?? "ideascientist_search",
            fetch: process.env.IDEASCIENTIST_PI_FETCH_TOOL ?? "ideascientist_fetch",
          },
        });
        return { content: [{ type: "text", text: JSON.stringify(result) }], details: result, isError: result.status === "blocked" };
      } finally { busy = false; }
    },
  });
  for (const [command, action] of [
    ["ideascientist", "ideate"], ["ideascientist-resume", "resume"],
    ["ideascientist-check", "check"], ["ideascientist-evaluate", "evaluate"],
  ]) {
    pi.registerCommand(command, {
      description: `IdeaScientist ${action} with the shared research contracts.`,
      handler: async (args) => {
        const binding = await readFile(new URL("./binding.md", import.meta.url), "utf8");
        const instructions = await readFile(new URL(`../../references/commands/${action}.md`, import.meta.url), "utf8");
        pi.sendUserMessage(`${binding}\n\n${instructions}\n\nResolved plugin root ${pluginRoot}\nUser arguments ${args}`, { expandPromptTemplates: false });
      },
    });
  }
}
