# Use IdeaScientist in Codex

Start an automatic research run with `$ideascientist:ideascientist-ideate <research problem>`. The main session coordinates literature discovery, registered paper reading, gap selection, a blind baseline, one candidate, adversarial review and a proposal. The workflow shares its evidence contracts with the Claude Code and Pi adapters.

## Install

Use Codex CLI with native plugins, multi-agent tools and web research. The adapter was loaded with Codex **0.160.0**.

```sh
codex plugin marketplace add junjiezhou1122/ideascientist-claude-code
codex plugin add ideascientist@ideascientist-native
```

For a local checkout, replace the marketplace source with its absolute directory. Restart Codex after installation. Keep your existing model, provider, sandbox and approval configuration. If web retrieval is unavailable for your selected provider, the run records the missing capability and stops before unsupported evidence advances.

## Run or resume

```text
$ideascientist:ideascientist-ideate Investigate local credit assignment failures in long-horizon policy learning.
$ideascientist:ideascientist-resume runs/ideascientist/credit-assignment
$ideascientist:ideascientist-check runs/ideascientist/credit-assignment
$ideascientist:ideascientist-evaluate runs/ideascientist/credit-assignment
```

Add `cutoff YYYY-MM-DD`, `slug <name>` or an output language to the ideate request when needed. Use the installed skills picker if your client displays invocation syntax differently. Native `skills/list` exposes these four names with the `ideascientist:` plugin namespace.

Outputs live in your research project's `runs/ideascientist/<slug>`. The [artifact contracts](../references/contracts.md) describe receipts, paper identities, snapshots and proposal fields. Resume preserves spent allowances and existing artifacts. A no-gap, blocked or unverified outcome includes its evidence or access limits.

## Native delegation

Codex's plugin manifest loads skills; it does not register custom agent types. These skills assign the seven shared scientific roles to generic native workers. Each packet names the role instruction, installed resource root, explicit inputs and outputs, targets, registered source identities and reserved allowances.

The binding inspects the tools exposed by the active runtime. V1 workers use `fork_context=false`; V2 workers use `fork_turns="none"`. The explicit clean-context setting matters because V2 can inherit history by default. Workers retain host configuration and system instructions. Fresh conversation does not prove filesystem isolation or freedom from project instructions.

Paper reading uses coordinator relay by default. A role returns a registered reader request, the coordinator runs a fresh reader, and a new role task consumes only structured digests. The original reader reservation covers the relay. This avoids changing nesting depth or user agent configuration. No source body enters the coordinator packet.

Metadata discovery uses native web search and the fixed command `python3 <plugin-root>/scripts/resolve_metadata.py <arxiv-ID-or-abs/pdf-URL>` through the native command tool. Python 3.10 or later is required. This scoped helper returns only exact arXiv identity and provenance, discards abstracts and bodies, and bounds requests to twenty seconds and 256 KiB. It rejects redirects and requested-version mismatches. Revised versions use `updated`; v1 uses `published`. Each attempt consumes one search from the existing reservation. Workers use at most two keyword queries before resolving leads. Host denial remains blocked. An empty blocked discovery preserves the failed metadata trace and cannot authorize registration or stage advancement. The reader uses native page opening, locator search or authorized local source reading. Unsupported PDF parsing or inaccessible exact versions remain unavailable. Search snippets cannot support mechanism claims. File ownership and raw-source boundaries are prompt constraints within your existing permissions, not an operating-system sandbox.

The bundled `scripts/acquire_arxiv.py` is a Claude reader capability. Codex does not invoke it, and downloading a PDF does not establish native PDF parsing support.

## Validate

```sh
python3 /absolute/plugin/root/scripts/check_artifacts.py /absolute/run/directory --json
python3 scripts/check_plugin.py
python3 scripts/check_runtime_loaders.py --codex
```

The loader check uses a temporary `CODEX_HOME` without changing your settings or copying credentials. It installs and lists the local plugin and checks cached resources. Offline validation does not establish scientific truth or global novelty. See the [verification record](verification.md) for observed runtime checks and remaining limits.
