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

## Corrections included in the tested design

- Discovery-only calls reserve no reader budget. Registered reading continuations reserve no repeated-search budget.
- Live research permits unknown version dates with an explicit date basis. Historical runs reject unknown exact-version dates.
- A failed appended read affects new goals and preserves earlier read evidence.
- Exact answer text and complete gap, candidate, and report input snapshots invalidate old receipts after dependency changes.
- An irrecoverably missing blind baseline can be marked unavailable without claiming a non-obviousness comparison.
- Local loading instructions include the plugin root in `--add-dir` because bundled contract files may otherwise lack Read permission from another project.

## Unverified scope

The native-agent smoke tests used synthetic local documents. They did not complete an ideation task against real literature or verify live paper fetching. Offline tests and native calls establish component behavior and handoffs. They do not establish research quality, global novelty, or original-paper benchmark performance.

Role instructions maintain file boundaries and baseline blindness. Tool lists do not provide a filesystem sandbox. Receipt consistency is not proof of semantic citation support or actual execution chronology. No model weights, corpus, training environment, or original runtime is included.

## Repeat the checks

Run these commands from the repository root. The final three commands require Claude Code, and the offline tests require only Python 3.10 or later:

```sh
python3 -m unittest discover -s tests -p 'test_native_*.py' -v
python3 scripts/check_plugin.py
python3 -m json.tool .claude-plugin/plugin.json
python3 -m json.tool .claude-plugin/marketplace.json
claude plugin validate .claude-plugin/plugin.json --strict --json
claude plugin validate .claude-plugin/marketplace.json --strict --json
claude --plugin-dir "$PWD" plugin details ideascientist
```

The [CI workflow](../.github/workflows/validate.yml) runs JSON parsing, structure checks, and the existing offline test suite on Python 3.10 and 3.13. It does not install Claude Code, use credentials, or call models. Strict Claude manifest validation and agent smoke tests remain separately recorded checks.
