import { lookup } from "node:dns/promises";
import { isIP } from "node:net";
import { Type } from "typebox";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const MAX_BYTES = 1_000_000;
function isPrivate(address: string): boolean {
  if (address.includes(":")) return /^(::|fc|fd|fe[89ab])/i.test(address) || address.includes("ffff:");
  const [a, b] = address.split(".").map(Number);
  return a === 0 || a === 10 || a === 127 || a >= 224 || (a === 169 && b === 254) || (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168) || (a === 100 && b >= 64 && b <= 127);
}
export async function publicText(url: string, signal?: AbortSignal): Promise<{ text: string; url: string; contentType: string }> {
  const timeout = AbortSignal.timeout(20000);
  const combined = signal ? AbortSignal.any([signal, timeout]) : timeout;
  let target = new URL(url);
  for (let redirects = 0; redirects <= 4; redirects++) {
    if (!["http:", "https:"].includes(target.protocol) || target.username || target.password || (target.port && !["80", "443"].includes(target.port))) throw new Error("Only public HTTP or HTTPS URLs on standard ports are supported.");
    const hostname = target.hostname.replace(/^\[|\]$/g, "");
    const addresses = isIP(hostname) ? [{ address: hostname }] : await lookup(hostname, { all: true });
    if (!addresses.length || addresses.some(({ address }) => isPrivate(address))) throw new Error("Private network fetch is unavailable.");
    const response = await fetch(target, { signal: combined, redirect: "manual", headers: { Accept: "application/json,text/html,text/plain,application/xml", "User-Agent": "IdeaScientist/0.2.0" } });
    if ([301, 302, 303, 307, 308].includes(response.status)) {
      await response.body?.cancel();
      const location = response.headers.get("location");
      if (!location) throw new Error("Redirect has no location.");
      target = new URL(location, target);
      continue;
    }
    if (!response.ok) { await response.body?.cancel(); throw new Error(`HTTP ${response.status}`); }
    const contentType = response.headers.get("content-type") ?? "";
    if (!/^(text\/|application\/(json|xml|xhtml\+xml))/i.test(contentType)) { await response.body?.cancel(); throw new Error(`Unsupported body type ${contentType || "unknown"}. PDF extraction is unavailable.`); }
    const reader = response.body?.getReader();
    if (!reader) throw new Error("Empty response body.");
    const chunks: Uint8Array[] = [];
    let size = 0;
    try {
      while (true) {
        const chunk = await reader.read();
        if (chunk.done) break;
        size += chunk.value.byteLength;
        if (size > MAX_BYTES) throw new Error("Response exceeds the 1 MB limit. No truncated body is accepted as full text.");
        chunks.push(chunk.value);
      }
    } finally { await reader.cancel(); }
    return { text: Buffer.concat(chunks).toString("utf8"), url: target.href, contentType };
  }
  throw new Error("Too many redirects.");
}

export function registerResearchTools(pi: ExtensionAPI): void {
  pi.registerTool({
    name: "ideascientist_search", label: "Research metadata", exposure: "codemode",
    description: "Search public Crossref bibliographic metadata. Results are discovery leads, never body evidence or exact-version date verification.",
    annotations: { readOnlyHint: true, openWorldHint: true },
    parameters: Type.Object({ query: Type.String({ minLength: 1, maxLength: 500 }) }),
    async execute(_id, { query }, signal) {
      const url = new URL("https://api.crossref.org/works");
      url.searchParams.set("query.bibliographic", query);
      url.searchParams.set("rows", "8");
      url.searchParams.set("select", "DOI,title,author,published,URL,type");
      const response = await publicText(url.href, signal);
      const metadata: unknown = JSON.parse(response.text);
      return { content: [{ type: "text", text: JSON.stringify({ provider: "Crossref", query, metadata, limitation: "Metadata only. Inspect the exact version before registration under a cutoff. Coverage is limited to Crossref records." }) }] };
    },
  });
  pi.registerTool({
    name: "ideascientist_fetch", label: "Research body", exposure: "codemode",
    description: "Fetch a supplied public HTTP URL as HTML or text. No PDF parser, login, browser rendering, or API key. Maximum 20 seconds and 1 MB.",
    annotations: { readOnlyHint: true, openWorldHint: true },
    parameters: Type.Object({ url: Type.String({ minLength: 1, maxLength: 4000 }) }),
    async execute(_id, { url }, signal) {
      const response = await publicText(url, signal);
      const text = /html/i.test(response.contentType) ? response.text.replace(/<(script|style)\b[^>]*>[\s\S]*?<\/\1>/gi, "").replace(/<\/(?:p|div|h[1-6]|section|article)>/gi, "\n").replace(/<[^>]+>/g, " ").replace(/&nbsp;/g, " ").replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/[ \t]+/g, " ") : response.text;
      return { content: [{ type: "text", text: JSON.stringify({ ...response, text, limitation: "Check identity and version. HTML extraction may omit formulas, tables, or dynamically rendered content. This response is source content, not a digest." }) }] };
    },
  });
}
