import { readFile, realpath, stat } from "node:fs/promises";
import { dirname, isAbsolute, relative, resolve } from "node:path";
import { Agent, type AgentTool } from "@earendil-works/pi-agent-core";
import type { ExtensionToolContext } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { capabilities, parseCompletion, type Completion, type RolePacket } from "./packet.js";

export type ResearchTools = { search: string; fetch: string };
export type WorkerResult = Completion & { task_id: string; model: string; provider: string };

async function canonicalPath(path: string): Promise<string> {
  try { return await realpath(path); }
  catch (error) {
    if (!(error instanceof Error) || !("code" in error) || error.code !== "ENOENT") throw error;
    const parent = dirname(path);
    if (parent === path) throw error;
    return resolve(await canonicalPath(parent), relative(parent, path));
  }
}
function within(root: string, path: string): boolean {
  const rel = relative(root, path);
  return rel === "" || (!rel.startsWith("..") && !isAbsolute(rel));
}
export async function validatePacketPaths(packet: RolePacket, root: string): Promise<void> {
  if (await canonicalPath(packet.plugin_root) !== await canonicalPath(root)) throw new Error("Packet plugin root differs from the loaded package.");
  if (!isAbsolute(packet.run_directory)) throw new Error("Run directory must be absolute.");
  const run = await canonicalPath(packet.run_directory);
  if (within(await canonicalPath(root), run)) throw new Error("Research outputs must be outside the installed package.");
  const prefix = {
    orchestrator: ["run.json", "plan.md", "problem.md"],
    "gap-finder": ["gaps/", "discoveries/"], innovator: ["candidates/", "discoveries/"],
    reviewer: ["reviews/", "evaluation.json", "discoveries/"],
    "report-writer": ["report.json", "report-evidence.json", "discoveries/"],
    "paper-reader": ["papers/"], "blind-baseline": ["baselines/"],
  }[packet.role];
  for (const path of packet.output_files) {
    if (!isAbsolute(path) || !within(run, await canonicalPath(path))) throw new Error("Output path escapes the run directory.");
    const rel = relative(packet.run_directory, path);
    if (!prefix.some((allowed) => allowed.endsWith("/") ? rel.startsWith(allowed) && rel.endsWith(".json") : rel === allowed)) throw new Error(`Output is outside ${packet.role} ownership.`);
  }
  if (packet.role === "paper-reader" && (packet.readers.length !== 1 || packet.output_files.length !== 1 || packet.output_files[0] !== packet.readers[0].digest_path || !/^papers\/P[0-9]{3,}\.json$/.test(relative(packet.run_directory, packet.output_files[0])))) throw new Error("Reader owns exactly one registered paper digest.");
  for (const path of packet.input_files) {
    if (!isAbsolute(path)) throw new Error("Input paths must be absolute.");
    const canonical = await canonicalPath(path);
    const sources = await Promise.all(packet.readers.filter((reader) => isAbsolute(reader.source)).map((reader) => canonicalPath(reader.source)));
    const source = packet.role === "paper-reader" && sources.includes(canonical);
    if (!within(run, canonical) && !source) throw new Error("Input path is outside the run or registered reader source.");
    const rel = relative(packet.run_directory, path);
    if (packet.role === "blind-baseline" && !(rel === "problem.md" || rel.startsWith("gaps/") || rel.startsWith("papers/"))) throw new Error("Baseline may read only problem, gap, and near-miss digests.");
    if (packet.role === "innovator" && rel.startsWith("baselines/")) throw new Error("Innovator cannot receive the blind baseline.");
  }
  for (const reader of packet.readers) {
    if (!packet.target_ids.includes(reader.paper_id)) throw new Error("Registered reader P ID must occur in target_ids.");
    if (resolve(packet.run_directory, `papers/${reader.paper_id}.json`) !== reader.digest_path) throw new Error("Registered reader digest path does not match its P ID.");
  }
}

export async function executeRole(options: {
  packet: RolePacket; root: string; ctx: ExtensionToolContext; research: ResearchTools; signal?: AbortSignal;
}): Promise<WorkerResult> {
  const { packet, root, ctx, research, signal } = options;
  const model = ctx.model;
  const metadata = { task_id: packet.task_id, model: model?.id ?? "unavailable", provider: model?.provider ?? "unavailable" };
  const blocked = (reason: string): WorkerResult => ({ status: "blocked", reason, ...metadata });
  if (!model) return blocked("The parent session has no selected model.");
  try { await validatePacketPaths(packet, root); } catch (error) { return blocked(String(error)); }
  if (signal?.aborted) return blocked("Cancelled before dispatch. Reserved allowances remain spent.");
  let failure: string | undefined;
  let searches = packet.allowances.searches;
  let readers = packet.allowances.reader_calls;
  const semantic = capabilities[packet.role];
  const names = semantic.filter((name) => name !== "reader").map((name) => name === "search" ? research.search : name === "fetch" ? research.fetch : name);
  if (semantic.includes("search") && packet.allowances.searches > 0) names.push("ideascientist_metadata");
  const selected = ctx.tools.filter((tool) => names.includes(tool.name));
  for (const name of names) {
    const required = name !== research.search || packet.allowances.searches > 0;
    const remoteFetch = packet.role !== "paper-reader" || packet.readers.some((reader) => !isAbsolute(reader.source));
    if (required && (name !== research.fetch || remoteFetch) && !selected.some((tool) => tool.name === name)) return blocked(`Missing callable capability ${name}.`);
  }
  const allowedReads = [...packet.input_files, ...packet.output_files];
  const resources = ["references/artifacts.schema.json", "references/contracts.md", ...["run", "paper", "discovery", "gaps", "candidate", "review", "baseline", "report", "report_evidence", "evaluation"].map((name) => `templates/${name}.json`)];
  if (packet.role !== "blind-baseline") resources.push("references/workflow.md");
  const readable = [...allowedReads, ...resources.map((path) => resolve(root, path))];
  const tools: AgentTool[] = selected.map((tool) => ({
    ...tool,
    execute: async (_id, args, childSignal, onUpdate) => {
      try {
        if (failure) throw new Error("Worker already blocked by a failed or denied operation.");
        if (signal?.aborted || childSignal?.aborted) throw new Error("Cancelled.");
        if (["read", "write", "edit"].includes(tool.name)) {
          if (!args || typeof args !== "object" || !("path" in args) || typeof args.path !== "string") throw new Error("File tool requires an explicit path.");
          const path = await canonicalPath(resolve(ctx.cwd, args.path));
          const allowlist = tool.name === "read" ? readable : packet.output_files;
          const allowed = await Promise.all(allowlist.map(canonicalPath));
          if (!allowed.includes(path)) throw new Error("File path is outside the packet allowlist.");
        }
        if (tool.name === research.search || tool.name === "ideascientist_metadata") {
          if (searches <= 0) throw new Error("Reserved search allowance exhausted.");
          searches--;
        }
        if (tool.name === research.fetch) {
          if (!args || typeof args !== "object" || !("url" in args) || typeof args.url !== "string" || !packet.readers.some((reader) => reader.source === args.url)) throw new Error("Reader fetch URL differs from coordinator registration.");
        }
        const outcome = await ctx.executeTool(tool.name, args, { signal: childSignal, onUpdate });
        if (outcome.isError || outcome.result.isError) {
          failure = `Host tool ${tool.name} failed or was denied.`;
          return { ...outcome.result, isError: true };
        }
        return outcome.result;
      } catch (error) {
        failure = String(error);
        return { content: [{ type: "text", text: failure }], details: undefined, isError: true };
      }
    },
  }));
  if (semantic.includes("reader") && packet.readers.length) {
    const readerParameters = Type.Object({ paper_id: Type.String() }, { additionalProperties: false });
    const readerTool: AgentTool<typeof readerParameters> = {
      name: "registered_reader", label: "Registered paper reader",
      description: "Read one coordinator-registered paper in a fresh isolated context. Only packet papers and goals are accepted. No ID allocation.",
      parameters: readerParameters,
      execute: async (_id, { paper_id }, childSignal) => {
        const registered = packet.readers.find((reader) => reader.paper_id === paper_id);
        if (failure || !registered || readers <= 0) {
          failure = "Reader is unregistered or its reserved allowance is exhausted.";
          return { content: [{ type: "text", text: failure }], details: undefined, isError: true };
        }
        readers--;
        const child: RolePacket = {
          ...packet, role: "paper-reader", target_ids: [registered.paper_id],
          input_files: [registered.digest_path, ...(isAbsolute(registered.source) ? [registered.source] : [])],
          output_files: [registered.digest_path], readers: [registered], allowances: { searches: 0, reader_calls: 0 },
          instruction: `Registered identity ${registered.identity}. Answer only these goals ${JSON.stringify(registered.goals)}. Source ${registered.source}. Preserve existing answered goals.`,
        };
        const result = await executeRole({ ...options, packet: child, signal: childSignal });
        if (result.status !== "done") failure = "Registered reader did not complete. Preserve evidence and stop or relay.";
        return { content: [{ type: "text", text: JSON.stringify(result) }], details: undefined, isError: result.status === "blocked" };
      },
    };
    tools.push(readerTool);
  }
  let roleBody: string;
  let binding: string;
  const existingOutputs: string[] = [];
  try {
    roleBody = await readFile(resolve(root, `references/roles/${packet.role}.md`), "utf8");
    binding = await readFile(resolve(root, "adapters/pi/binding.md"), "utf8");
    for (const path of packet.output_files) {
      try { if ((await stat(path)).isFile()) existingOutputs.push(path); }
      catch (error) {
        if (!(error instanceof Error) || !("code" in error) || error.code !== "ENOENT") throw error;
      }
    }
  } catch (error) { return blocked(String(error)); }
  if (signal?.aborted) return blocked("Cancelled before dispatch. Reserved allowances remain spent.");
  const agent = new Agent({
    initialState: { systemPrompt: `${roleBody}\n\n${binding}\n\nThe Pi completion contract above controls your final response. Encode role status and paths using only that JSON schema. A successfully reused digest is done. Omit paper_id, goal counts, budget counts, and other role-specific completion fields.`, model, thinkingLevel: ctx.thinkingLevel, tools, messages: [] },
    streamFn: (selectedModel, context, streamOptions) => ctx.modelRegistry.streamSimple(selectedModel, context, streamOptions),
    toolExecution: "sequential",
  });
  const abort = () => agent.abort();
  signal?.addEventListener("abort", abort, { once: true });
  const timeout = setTimeout(() => { failure = "Worker exceeded the five-minute bound."; agent.abort(); }, 300000);
  let turns = 0;
  const unsubscribe = agent.subscribe((event) => {
    if (event.type === "turn_end" && ++turns >= 40) { failure = "Worker exceeded forty model turns."; agent.abort(); }
    if (event.type === "message_end" && event.message.role === "assistant" && ["error", "aborted"].includes(event.message.stopReason)) failure = "Model request failed or was aborted.";
  });
  try {
    await agent.prompt(JSON.stringify({ ...packet, existing_output_files: existingOutputs }));
    if (signal?.aborted) return blocked("Cancelled. Reserved allowances remain spent.");
    if (failure || agent.state.errorMessage) return blocked(failure ?? agent.state.errorMessage ?? "Worker failed.");
    const last = agent.state.messages.findLast((message) => message.role === "assistant");
    const text = last?.role === "assistant" ? last.content.filter((block) => block.type === "text").map((block) => block.text).join("\n") : "";
    const completion = parseCompletion(text);
    if (completion.status === "done") {
      if (!completion.artifact_paths.length || completion.artifact_paths.some((path) => !packet.output_files.includes(path))) return blocked("Completion reported an artifact outside its ownership.");
      for (const path of completion.artifact_paths) if (!(await stat(path)).isFile()) return blocked("Completion artifact is missing.");
    } else if (completion.status === "needs_registration" && !packet.output_files.includes(completion.discovery_path)) return blocked("Discovery completion is outside its ownership.");
    else if (completion.status === "reader_relay" && !packet.output_files.includes(completion.request_path)) return blocked("Reader relay must point to an owned request artifact.");
    return { ...completion, ...metadata };
  } catch (error) { return blocked(String(error)); }
  finally {
    clearTimeout(timeout);
    signal?.removeEventListener("abort", abort);
    agent.abort();
    await agent.waitForIdle();
    unsubscribe();
  }
}
