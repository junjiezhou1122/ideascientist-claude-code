# Native plugin verification record

The source plugin was verified on 2026-10-09 with Claude Code 2.1.287. This record distinguishes offline structural checks and synthetic native-agent smoke tests from research-quality evaluation.

## Verified behavior

- Both manifests passed `claude plugin validate --strict --json` without errors or warnings.
- `claude --plugin-dir <repository-path> plugin details ideascientist` recognized four skills, seven agents, zero MCP servers, and zero hooks.
- All 26 offline tests passed. They cover missing citation IDs, unread paper bodies, mismatched locators, abstract-only mechanism support, exact versions after the cutoff, missing current-candidate reviews, changed content under the same ID, changed digest answers, missing nested evaluation fields and kill conditions, baseline recovery, failed appended reads, and zero-gap outcomes.
- The artifact checker's CLI accepted a complete synthetic run. An injected `[P999]` citation produced a specific error and exit code 1.
- A real Claude session loaded paper-reader, read an explicitly labeled synthetic local method note, and wrote answers to two goals, four digest views, section locators, and a limitation stating that there were no experimental results.
- A real Claude session executed the main session, gap-finder, and nested paper-reader route. Streaming tool records contained two Agent calls and the reader's parent-call ID. The digest file existed after completion.

The standalone packaging pass also passed all 26 existing offline tests, the structure checker, both strict manifest checks, and native component discovery against the extracted repository. Its checker CLI accepted a complete synthetic run and rejected an injected unknown citation with exit code 1. The pass did not repeat the model smoke tests or add research-quality claims.

## Codex and Pi adapters, version 0.2.0

The runtime adaptation was checked on 2026-10-09 against Codex CLI 0.160.0 and Pi 1.0.0.

- All 31 Python regressions passed, including five adapter packaging and shared-resource checks. The canonical artifact schema, templates and checker remain shared.
- Codex installed the plugin in a temporary `CODEX_HOME`. Native `skills/list` from an unrelated project returned four enabled skills from the installed cache. Their resource roots resolved the canonical workflow, commands and roles. Native `plugin/read` reported version 0.2.0 installed and enabled.
- Pi's native extension loader registered four commands and `ideascientist_agent`, `ideascientist_search`, `ideascientist_fetch` without errors. Deterministic native Agent tests covered empty initial context, inherited model/thinking, no raw-source completion, denied tools, packet and symlink escapes, missing fetch, absent initial output metadata, denied missing-output reads, cancellation before model dispatch, and nested registered readers with exhausted-budget rejection.
- An authenticated Pi CLI session invoked `ideascientist_agent` for the local synthetic reader. Nested host read/write events had the role call's parent ID; no coordinator source read occurred. The worker returned done with its P001 path. The digest passed the canonical paper schema, answered two goals with section locators, and retained synthetic/no-experiment limits. It used the active parent model and provider without an adapter override. The final implementation also passed a historical-cutoff reader run after the permission and completion fixes.
- An authenticated Codex app-server session started a generic worker with `fork_turns="none"`. Native sub-agent activity events identified a distinct reader thread. Source-file commands belonged to that child, while main checked only its resulting digest. The P001 artifact passed the same schema and two-goal check. The external smoke driver timed out waiting for the parent's final turn after the child completed; the successful claim is limited to the observed child execution and artifact.
- A bounded network probe confirmed Crossref metadata access and an exact-version arXiv HTML URL. This did not establish the adapter's full live-literature workflow or source-date correctness.

Actual execution found two corrected issues. Codex's native file access uses a command tool, so the binding now permits scoped file operations while forbidding general command execution. Pi supplies owned-output existence metadata before dispatch, so the reader can create a first digest without attempting a read of a missing file. Every model-issued read still passes through host hooks. Cancellation is checked again after instruction loading, and explicitly supplied evaluation references are staged inside the run. Host denials and other failures still stop the worker.

The initial Codex CLI-only delegation probe was inconclusive because its JSON output omitted child activity. Native app-server events supplied the later proof. The initial Pi attempt returned blocked and its coordinator subsequently wrote a digest itself; that result was rejected as an isolation test. Only successful isolated-worker runs are counted. A later Pi attempt repeatedly emitted an invalid cutoff and never dispatched. Another wrote a digest but returned extra role-specific completion fields and was blocked. The final binding explicitly takes precedence over the role's summary format, and the final CLI run returned done with a valid digest.

These tests establish packaging and local synthetic reader behavior. They do not establish scientific quality, semantic citation support, complete baseline blindness, or a full real-literature run. Codex and Claude generic tool access remains governed by native permissions and prompt discipline; Pi's explicit path/tool guards are not an operating-system sandbox.

## Discovery and catalog repair, version 0.2.1

The real-literature trial on 2026-10-09 exposed a discovery failure. Its search provider returned URL leads without authors or exact versions, and the specialist lacked a metadata-resolution capability. It honestly stopped with an empty discovery, which the previous schema rejected. Earlier attempts also exposed foreground scheduling and checker tool-declaration problems.

The repair adds a fixed arXiv Atom metadata helper, a strict empty-blocked discovery variant, explicit foreground waiting, and Bash declarations for the canonical checker. Metadata calls share the existing search reservation. The helper returns no abstract or paper body, rejects returned identity/version mismatches, and uses the selected revision date. Its CLI has a portable twenty-second deadline and a 256 KiB response limit. Expected metadata failure returns blocked JSON; host denial or cancellation still blocks the Pi worker.

Verification completed on 2026-10-10:

- All 51 Python regressions passed. They cover both discovery variants, blocked task linkage, exact version/date selection, malformed metadata, rejected redirects, abstract exclusion, CLI timeout, packaging, and tool declarations.
- Both strict Claude manifests passed without warnings. Codex 0.160.0 installed the corrected native marketplace and loaded four skills. Pi 1.0.0 loaded four commands and four tools, including metadata resolution. Its native transport tests passed shared-budget, tool-exposure, permission, cancellation, and reader-boundary checks. The shipped Pi extension passed strict TypeScript checking. The deterministic test driver runs successfully through Pi's loader, but its separate strict type check has existing incompatibilities with Pi's exported test APIs.
- A real Claude CLI session loaded 0.2.1 and invoked one foreground gap-finder with an incomplete CLIN URL. The child executed the helper, preserved the returned eight authors, exact `2310.10134v1` identity and 2023-10-16 date, and wrote four reader goals. It returned `needs_registration`. Coordinator checks ran after child completion, and the independent checker returned `ok: true` with no errors. Streaming provenance passed twenty assertions, including no coordinator metadata resolution, no body reads, and no permission denials. The focused run spent one role call, one metadata search, and zero reader calls.
- The original blocked run passed the repaired checker without editing any of its eight files. This validates the honest blocked record; it does not advance that scientific run.
- The same pinned `plugin-scanner` 3.0.123 used by the catalog scored the combined source 85/100, compared with 71/100 before repair. It reported zero critical, zero high, two medium, four low, and five informational findings. Remaining medium findings repeat the missing lockfile for a peer-only runtime package. The scan skipped unavailable Cisco deep scanning and online probing. It does not prove semantic instruction safety or research quality.

The catalog repair pins GitHub Actions to immutable SHAs and supplies explicit native Codex marketplace source and policy fields. The source scan workflow uses the catalog's pinned action with read-only permissions and no comments, submissions, online probes, or SARIF upload. A passing local scan is separate from the catalog's own approval and centralized scan.

The focused native test verified discovery-to-registration handoff. It did not run subsequent readers, create a gap or candidate, or finish a research proposal. Windows execution of the portable CLI has not been tested on a Windows host.

## Corrections included in the tested design

- Discovery-only calls reserve no reader budget. Registered reading continuations reserve no repeated-search budget.
- Live research permits unknown version dates with an explicit date basis. Historical runs reject unknown exact-version dates.
- A failed appended read affects new goals and preserves earlier read evidence.
- Exact answer text and complete gap, candidate, and report input snapshots invalidate old receipts after dependency changes.
- An irrecoverably missing blind baseline can be marked unavailable without claiming a non-obviousness comparison.
- Local loading instructions include the plugin root in `--add-dir` because bundled contract files may otherwise lack Read permission from another project.

## Unverified scope

The reader smoke tests used synthetic local documents. The later real-literature trial completed an isolated reader digest but stopped during discovery; the repaired discovery test verified an actual arXiv metadata handoff. A complete ideation task against real literature remains unverified. Offline tests and native calls establish component behavior and handoffs. They do not establish research quality, global novelty, or original-paper benchmark performance.

Role instructions maintain file boundaries and baseline blindness. Tool lists do not provide a filesystem sandbox. Receipt consistency is not proof of semantic citation support or actual execution chronology. No model weights, corpus, training environment, or original runtime is included.

## Repeat the checks

Run these commands from the repository root. The final three commands require Claude Code, and the offline tests require only Python 3.10 or later:

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/check_plugin.py
python3 -m json.tool .claude-plugin/plugin.json
python3 -m json.tool .claude-plugin/marketplace.json
claude plugin validate .claude-plugin/plugin.json --strict --json
claude plugin validate .claude-plugin/marketplace.json --strict --json
claude --plugin-dir "$PWD" plugin details ideascientist
```

The [CI workflow](../.github/workflows/validate.yml) runs JSON parsing, structure checks, and all Python tests on Python 3.10 and 3.13. A Node 22 job installs Pi 1.0.0 and runs its extension loader and deterministic native Agent transport checks. CI does not use credentials or call models. Strict Claude manifest validation and authenticated agent smoke tests remain separately recorded checks.
