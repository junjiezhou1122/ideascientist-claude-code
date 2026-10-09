import assert from "node:assert/strict";
import { mkdtemp, writeFile, readFile, mkdir, symlink, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { Type } from "typebox";
import { createAssistantMessageEventStream, getModel, type Context } from "@earendil-works/pi-ai";
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
          if (deny) return { toolCall: { type: "toolCall", id: "host", name, arguments: {} }, result: { content: [textContent("Denied by host")] }, isError: true };
          const parsed: unknown = args;
          assert(parsed && typeof parsed === "object" && "path" in parsed && typeof parsed.path === "string");
          const content = name === "read" ? await readFile(parsed.path, "utf8") : "written";
          if (name === "write") { assert("content" in parsed && typeof parsed.content === "string"); await writeFile(parsed.path, parsed.content); }
          return { toolCall: { type: "toolCall", id: "host", name, arguments: {} }, result: { content: [textContent(content)] }, isError: false };
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
        commandCtx.ui.notify("Pi native Agent transport checks passed.", "info");
      } finally { await rm(temporary, { recursive: true, force: true }); }
    },
  });
}
