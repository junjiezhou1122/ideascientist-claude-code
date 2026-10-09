# Use IdeaScientist in Pi

Start an automatic research run with `/ideascientist <research problem>`. The extension registers fresh scientific role workers and shares the evidence contracts, stages and checker with the Claude Code and Codex adapters.

## Install

Use Pi **1.0.0** or later with the current `@earendil-works` extension API.

```sh
pi install git:github.com/junjiezhou1122/ideascientist-claude-code
```

Restart Pi. For temporary loading from a local checkout, start Pi in your research project:

```sh
pi -e /absolute/path/to/ideascientist-claude-code/adapters/pi/index.ts
```

The package uses Pi's host-provided Agent and model registry. It does not bundle another copy of Pi or require a separate model endpoint. Keep your current provider login and select your model normally.

## Run or resume

```text
/ideascientist Investigate local credit assignment failures in long-horizon policy learning.
/ideascientist-resume runs/ideascientist/credit-assignment
/ideascientist-check runs/ideascientist/credit-assignment
/ideascientist-evaluate runs/ideascientist/credit-assignment
```

Add `cutoff YYYY-MM-DD`, `slug <name>` or an output language to the first request when needed. The main session owns run state, IDs, registration and budget reservations. Specialist workers own their assigned artifacts. Outputs stay beneath `runs/ideascientist/<slug>` in your working project.

## Research access

Default `ideascientist_search` retrieves bibliographic metadata from Crossref without an API key. Its coverage is limited to Crossref records. Metadata is a discovery lead, not proof a paper was read or that the accessed version predates a historical cutoff.

`ideascientist_metadata` resolves an arXiv ID or abs/pdf URL through the bundled standard-library Python helper. Python 3.10 or later is required for metadata resolution and artifact checking. The helper contacts only the fixed arXiv Atom metadata endpoint and emits exact title, authors, canonical version URL, version, date, and provenance. It discards abstracts and bodies. An unversioned lead selects the returned exact version; a requested version mismatch blocks. Revised versions use the returned `updated` date, while v1 uses `published`. The request is limited to twenty seconds and 256 KiB, with redirects rejected.

Workers use at most two keyword queries before resolving the best leads. Each metadata attempt consumes a search from the same reservation, including failures and denials. The metadata tool appears only in discovery-capable workers with a positive search allowance. Calls pass through host permission hooks and cancellation. If metadata cannot be resolved, preserve an empty blocked discovery and its matching blocked task. It cannot authorize registration or evidence claims.

Default `ideascientist_fetch` reads a registered public HTTP or HTTPS URL as HTML or text. It allows at most twenty seconds, four redirects and one megabyte. It rejects unsupported binary content and oversized responses. HTML extraction may omit equations or tables. It does not parse PDF, authenticate to publishers or render JavaScript. Reader access remains unavailable when these limits prevent inspecting the mechanism.

The package ships `scripts/acquire_arxiv.py` with the shared resources for the Claude binding. Pi does not invoke it; this helper does not add PDF parsing to Pi.

To use research tools from another installed Pi extension or MCP server, set their callable names before starting Pi:

```sh
IDEASCIENTIST_PI_SEARCH_TOOL=your_metadata_search_tool \
IDEASCIENTIST_PI_FETCH_TOOL=your_source_fetch_tool pi
```

The fetch tool must accept a `url` field. The tools must be callable through Pi's `ctx.executeTool`; model-only tools cannot be delegated. These trusted startup settings select tool names. Research packets cannot choose arbitrary tools. Child calls retain host validation, permission hooks and cancellation. Missing or denied tools return blocked.

## Native workers

`ideascientist_agent` executes one role packet using a new Pi core Agent with empty conversation history. It inherits the selected model, thinking level and provider registry without copying credentials. No parent messages, project context files or other extensions are loaded into the child automatically.

Each packet includes the role, absolute package and run paths, task ID, target IDs, explicit input/output files, cutoff, instruction and reserved allowances. Registered-reader entries contain exact bibliographic identity, source, P ID, goals and digest path. Specialists can call only readers listed in that packet, within the reserved budget. A reader cannot delegate again. The blind baseline receives no workflow or candidate inputs; the innovator receives no baseline.

File calls are restricted to explicit packet paths and required bundled resources, and pass through the host's permission checks. These guards support role ownership without providing an operating-system sandbox. Requests run sequentially. Errors, denials, cancellation and timeout preserve spent reservations and return blocked. A completed model turn is not acceptance of a scientific artifact; the coordinator checks canonical receipts before advancing.

## Validate

```sh
python3 scripts/check_plugin.py
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/check_runtime_loaders.py --pi-package /absolute/path/to/installed/pi-coding-agent --transport
```

The last command loads the extension through Pi's installed native loader and tests Agent transport with deterministic model responses. It makes no model requests and changes no settings. Run the artifact checker on real saved outputs separately. See the [verification record](verification.md) for actual authenticated reader tests and scientific limits.
