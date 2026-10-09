import assert from "node:assert/strict";
import { mkdtemp, writeFile, readFile, mkdir, symlink, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { Type } from "typebox";
import { createAssistantMessageEventStream, getModel, type Context, type JsonObject } from "@earendil-works/pi-ai";
import type { ExtensionAPI, ExtensionToolContext } from "@earendil-works/pi-coding-agent";
import { executeRole, validatePacketPaths } from "../adapters/pi/worker.js";
import { parsePacket, type RolePacket } from "../adapters/pi/packet.js";

export default function transportTests(pi: ExtensionAPI): void {
  pi.registerCommand("test-ideascientist-transport", {
    description: "Run offline native Agent transport checks.",
    async handler(_args, commandCtx) {
      const temporary = await mkdtemp(join(tmpdir(), "ideascientist-pi-transport-"));
      const root = join(temporary, "relocated-package");
      const run = join(temporary, "run");
      await mkdir(join(root, "references/roles"), { recursive: true });
      await mkdir(join(root, "adapters/pi"), { recursive: true });
      await mkdir(join(run, "papers"), { recursive: true });
      await writeFile(join(root, "references/roles/paper-reader.md"), "Isolated reader.");
      await writeFile(join(root, "references/roles/blind-baseline.md"), "Isolated baseline.");
      await writeFile(join(root, "adapters/pi/binding.md"), "Return only completion JSON.");
      const source = join(temporary, "source.md");
      await writeFile(source, "RAW_BODY_SENTINEL");
      const output = join(run, "papers/P001.json");
      const packet: RolePacket = {
        role: "paper-reader", plugin_root: root, run_directory: run, task_id: "T001", target_ids: ["P001"],
        input_files: [source], output_files: [output], instruction: "Read registered source and write digest.", cutoff: null,
        allowances: { searches: 0, reader_calls: 0 },
        readers: [{ paper_id: "P001", identity: "Synthetic v1", source, goals: ["What condition?"], digest_path: output }],
      };
      const model = getModel("openai", "gpt-4o-mini");
      const textContent = (text: string) => ({ type: "text" as const, text });
      let request = 0;
      let deny = false;
      let outside = false;
      let probeMissing = false;
      const requests: unknown[] = [];
      const calls: string[] = [];
      const fileSchema = Type.Object({ path: Type.String(), content: Type.Optional(Type.String()) });
      const hostTools = ["read", "write", "edit"].map((name) => ({
        name, label: name, description: name, parameters: fileSchema,
        execute: async () => { throw new Error("Must use host executeTool, never direct tool execution."); },
      }));
      const ctx: ExtensionToolContext = {
        ...commandCtx, cwd: temporary, model, thinkingLevel: "low", tools: hostTools,
        modelRegistry: {
          ...commandCtx.modelRegistry,
          streamSimple(selectedModel, context, options) {
            assert.equal(selectedModel, model);
            assert.equal(options?.reasoning, "low");
            requests.push(context);
            const stream = createAssistantMessageEventStream();
            const index = request++;
            const content = index === 0 ? [{ type: "toolCall" as const, id: "read1", name: "read", arguments: { path: probeMissing ? output : source } }]
              : index === 1 ? [{ type: "toolCall" as const, id: "write1", name: "write", arguments: { path: outside ? join(temporary, "escape.json") : output, content: "{}" } }]
                : [textContent(JSON.stringify({ status: "done", artifact_paths: [output] }))];
            const message = {
              role: "assistant" as const, content, api: model.api, provider: model.provider, model: model.id,
              usage: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, totalTokens: 0, cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 } },
              stopReason: index < 2 ? "toolUse" as const : "stop" as const, timestamp: Date.now(),
            };
            queueMicrotask(() => { stream.push({ type: "done", reason: message.stopReason, message }); stream.end(message); });
            return stream;
          },
        },
        async executeTool(name, args) {
          calls.push(name);
          if (deny) return { toolCall: { type: "toolCall", id: "host", name, arguments: {} }, result: { content: [textContent("Denied by host")], details: undefined }, isError: true };
          const parsed: unknown = args;
          assert(parsed && typeof parsed === "object" && "path" in parsed && typeof parsed.path === "string");
          const content = name === "read" ? await readFile(parsed.path, "utf8") : "written";
          if (name === "write") { assert("content" in parsed && typeof parsed.content === "string"); await writeFile(parsed.path, parsed.content); }
          return { toolCall: { type: "toolCall", id: "host", name, arguments: {} }, result: { content: [textContent(content)], details: undefined }, isError: false };
        },
      };
      const invoke = () => executeRole({ packet, root, ctx, research: { search: "absent_search", fetch: "absent_fetch" } });
      try {
        assert.equal(parsePacket(packet), packet);
        assert.throws(() => parsePacket({ ...packet, research_tools: { search: "bash", fetch: "bash" } }));
        const result = await invoke();
        assert.equal(result.status, "done", JSON.stringify(result));
        assert.deepEqual(calls, ["read", "write"]);
        assert(!JSON.stringify(requests[0]).includes("RAW_BODY_SENTINEL"));
        assert(!JSON.stringify(requests[0]).includes('"name":"ideascientist_metadata"'));
        assert(!JSON.stringify(result).includes("RAW_BODY_SENTINEL"));
        const firstMessage = (requests[0] as Context).messages.find((message) => message.role === "user");
        assert(firstMessage?.role === "user");
        const initialText = typeof firstMessage.content === "string" ? firstMessage.content : firstMessage.content.filter((block) => block.type === "text").map((block) => block.text).join("");
        assert.deepEqual(JSON.parse(initialText).existing_output_files, []);
        assert(JSON.stringify(requests[1]).includes("RAW_BODY_SENTINEL"));
        await rm(output);
        request = 0; deny = true; probeMissing = true; calls.length = 0;
        assert.equal((await invoke()).status, "blocked");
        assert.deepEqual(calls, ["read"]);
        deny = false; probeMissing = false; outside = true; request = 0; calls.length = 0;
        assert.equal((await invoke()).status, "blocked");
        assert.deepEqual(calls, ["read"]);
        const abort = new AbortController(); abort.abort();
        assert.equal((await executeRole({ packet, root, ctx, research: { search: "x", fetch: "y" }, signal: abort.signal })).status, "blocked");
        const midDispatch = new AbortController();
        const cancellingCtx = { ...ctx, get tools() { midDispatch.abort(); return hostTools; } };
        const requestsBeforeCancel = requests.length;
        assert.equal((await executeRole({ packet, root, ctx: cancellingCtx, research: { search: "x", fetch: "y" }, signal: midDispatch.signal })).status, "blocked");
        assert.equal(requests.length, requestsBeforeCancel);
        await symlink(temporary, join(run, "papers/escape"));
        await assert.rejects(validatePacketPaths({ ...packet, output_files: [join(run, "papers/escape/out.json")] }, root));
        await assert.rejects(validatePacketPaths({ ...packet, role: "blind-baseline", input_files: [join(run, "candidates/C001.json")], output_files: [join(run, "baselines/G001.json")], readers: [] }, root));
        const remote = { ...packet, input_files: [], readers: [{ ...packet.readers[0], source: "https://example.org/paper" }] };
        assert.equal((await executeRole({ packet: remote, root, ctx, research: { search: "x", fetch: "missing_fetch" } })).status, "blocked");
        outside = false;
        await writeFile(join(root, "references/roles/gap-finder.md"), "Specialist with registered reader.");
        await mkdir(join(run, "gaps"));
        const gapOutput = join(run, "gaps/A001.json");
        const nestedRequests: unknown[] = [];
        let parentTurn = 0;
        let readerTurn = 0;
        const nestedCtx = {
          ...ctx,
          modelRegistry: {
            ...ctx.modelRegistry,
            streamSimple(selectedModel, context, options) {
              assert.equal(selectedModel, model);
              assert.equal(options?.reasoning, "low");
              nestedRequests.push(context);
              const child = JSON.stringify(context.messages.filter((message) => message.role === "system")).includes("Isolated reader.");
              const index = child ? readerTurn++ : parentTurn++;
              const content = child
                ? index === 0 ? [{ type: "toolCall" as const, id: "child-read", name: "read", arguments: { path: source } }]
                  : index === 1 ? [{ type: "toolCall" as const, id: "child-write", name: "write", arguments: { path: output, content: "{}" } }]
                    : [textContent(JSON.stringify({ status: "done", artifact_paths: [output] }))]
                : index === 0 ? [{ type: "toolCall" as const, id: "reader", name: "registered_reader", arguments: { paper_id: "P001" } }]
                  : index === 1 ? [{ type: "toolCall" as const, id: "gap-write", name: "write", arguments: { path: gapOutput, content: "{}" } }]
                    : [textContent(JSON.stringify({ status: "done", artifact_paths: [gapOutput] }))];
              const message = {
                role: "assistant" as const, content, api: model.api, provider: model.provider, model: model.id,
                usage: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, totalTokens: 0, cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 } },
                stopReason: index < 2 ? "toolUse" as const : "stop" as const, timestamp: Date.now(),
              };
              const stream = createAssistantMessageEventStream();
              queueMicrotask(() => { stream.push({ type: "done", reason: message.stopReason, message }); stream.end(message); });
              return stream;
            },
          },
        } satisfies ExtensionToolContext;
        const specialist: RolePacket = { ...packet, role: "gap-finder", target_ids: ["A001", "P001"], input_files: [], output_files: [gapOutput], allowances: { searches: 0, reader_calls: 1 } };
        const nested = () => executeRole({ packet: specialist, root, ctx: nestedCtx, research: { search: "absent_search", fetch: "absent_fetch" } });
        const nestedResult = await nested();
        assert.equal(nestedResult.status, "done", JSON.stringify(nestedResult));
        assert.equal(readerTurn, 3);
        assert(!JSON.stringify(nestedRequests.filter((context) => !JSON.stringify(context).includes("Isolated reader."))).includes("RAW_BODY_SENTINEL"));
        specialist.allowances.reader_calls = 0;
        parentTurn = 0; readerTurn = 0;
        assert.equal((await nested()).status, "blocked");
        assert.equal(readerTurn, 0);
        const discoveryOutput = join(run, "discoveries/T001.json");
        await mkdir(join(run, "discoveries"));
        const discovery: RolePacket = { ...specialist, output_files: [discoveryOutput], readers: [], allowances: { searches: 2, reader_calls: 0 } };
        const researchNames = ["ideascientist_search", "ideascientist_metadata"];
        const researchTools = researchNames.map((name) => ({ ...hostTools[0], name, label: name, parameters: Type.Object({ source: Type.Optional(Type.String()), query: Type.Optional(Type.String()) }) }));
        const research = { search: "ideascientist_search", fetch: "absent_fetch" };
        async function discoveryProbe(sequence: string[], allowance: number, denied = false, cancellation?: AbortController, probePacket = discovery) {
          let turn = 0;
          const hostCalls: string[] = [];
          const exposed: string[][] = [];
          const probeCtx = {
            ...ctx, tools: [...hostTools, ...researchTools],
            modelRegistry: {
              ...ctx.modelRegistry,
              streamSimple(selectedModel, context, options) {
                assert.equal(selectedModel, model);
                exposed.push(context.messages.flatMap((message) => message.role === "system" ? message.toolsAdded?.map((tool) => tool.name) ?? [] : []));
                const name = sequence[turn++];
                const args: JsonObject = name === "ideascientist_metadata" ? { source: "2310.10134v1" } : { query: "synthetic search" };
                const content = name ? [{ type: "toolCall" as const, id: `metadata-${turn}`, name, arguments: args }]
                  : [textContent(JSON.stringify({ status: "blocked", reason: "Synthetic discovery probe completed." }))];
                const message = { role: "assistant" as const, content, api: model.api, provider: model.provider, model: model.id,
                  usage: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, totalTokens: 0, cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 } },
                  stopReason: name ? "toolUse" as const : "stop" as const, timestamp: Date.now() };
                const stream = createAssistantMessageEventStream();
                queueMicrotask(() => { stream.push({ type: "done", reason: message.stopReason, message }); stream.end(message); });
                return stream;
              },
            },
            async executeTool(name, _args, options) {
              hostCalls.push(name);
              assert(options?.signal);
              cancellation?.abort();
              return { toolCall: { type: "toolCall" as const, id: "host", name, arguments: {} },
                result: { content: [textContent(denied ? "Denied by host" : JSON.stringify({ status: "resolved", identity: { title: "Synthetic metadata", authors: ["Fixture Author"], version: "v1" } }))], details: undefined }, isError: denied };
            },
          } satisfies ExtensionToolContext;
          const result = await executeRole({ packet: { ...probePacket, allowances: { searches: allowance, reader_calls: 0 } }, root, ctx: probeCtx, research, signal: cancellation?.signal });
          return { result, hostCalls, exposed };
        }
        const budgetProbe = await discoveryProbe(["ideascientist_search", "ideascientist_metadata", "ideascientist_metadata"], 2);
        assert.deepEqual(budgetProbe.hostCalls, ["ideascientist_search", "ideascientist_metadata"]);
        assert.equal(budgetProbe.result.status, "blocked");
        assert(budgetProbe.result.status === "blocked" && budgetProbe.result.reason.includes("allowance exhausted"));
        assert(budgetProbe.exposed[0].includes("ideascientist_metadata"));
        assert(!budgetProbe.exposed[0].includes("ideascientist_fetch"));
        assert(!JSON.stringify(budgetProbe.result).includes("Fixture Author"));
        const deniedProbe = await discoveryProbe(["ideascientist_metadata", "ideascientist_search"], 2, true);
        assert.deepEqual(deniedProbe.hostCalls, ["ideascientist_metadata"]);
        assert(deniedProbe.result.status === "blocked" && deniedProbe.result.reason.includes("denied"));
        const cancelledProbe = await discoveryProbe(["ideascientist_metadata", "ideascientist_search"], 2, false, new AbortController());
        assert.equal(cancelledProbe.result.status, "blocked");
        assert.deepEqual(cancelledProbe.hostCalls, ["ideascientist_metadata"]);
        const noBudget = await discoveryProbe([], 0);
        assert(!noBudget.exposed[0].includes("ideascientist_metadata"));
        await mkdir(join(run, "baselines"));
        const baseline: RolePacket = { ...discovery, role: "blind-baseline", output_files: [join(run, "baselines/G001.json")] };
        const baselineProbe = await discoveryProbe([], 2, false, undefined, baseline);
        assert(!baselineProbe.exposed[0].includes("ideascientist_metadata"));
        assert(!baselineProbe.exposed[0].includes("ideascientist_search"));
        const coordinator: RolePacket = { ...discovery, role: "orchestrator", output_files: [join(run, "run.json")] };
        await writeFile(join(root, "references/roles/orchestrator.md"), "Coordinator without research tools.");
        const coordinatorProbe = await discoveryProbe([], 2, false, undefined, coordinator);
        assert(!coordinatorProbe.exposed[0].includes("ideascientist_metadata"));
        assert(!coordinatorProbe.exposed[0].includes("ideascientist_search"));
        commandCtx.ui.notify("Pi native Agent transport checks passed.", "info");
      } finally { await rm(temporary, { recursive: true, force: true }); }
    },
  });
}
