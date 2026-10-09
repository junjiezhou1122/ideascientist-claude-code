# IdeaScientist for Claude Code, Codex and Pi

Give a research problem to the entry point for your coding agent:

| Runtime | Start a run |
|---|---|
| Claude Code | `/ideascientist:ideate <research problem>` |
| Codex | `$ideascientist:ideascientist-ideate <research problem>` |
| Pi | `/ideascientist <research problem>` |

Start with a research problem. The plugin automatically searches for methodological gaps, reads supporting papers, transfers a mechanism across research settings, challenges and revises the candidate, and develops a surviving idea into a complete falsifiable proposal. One command coordinates the workflow, subject to available evidence and finite budgets.

This is an independent native translation/adaptation for Claude Code, Codex and Pi of the research methodology in [IdeaScientist: Orchestrating Agents for Grounded Scientific Ideation](https://github.com/jiarui-liu/IdeaScientist). Original work by the IdeaScientist authors. This is not an official upstream distribution.

The output is a research proposal with traceable paper evidence, explicit assumptions, an evaluation plan, and conditions that would falsify its predictions. The plugin does not run experiments, train models, or implement research code.

## Install the plugin

Use a current Claude Code version with nested subagent support. The native design was tested with Claude Code **2.1.287**. All seven agents use `model: inherit` and your existing Claude Code login and model configuration. You do not need the original Python runtime, Vault database, vector services, custom model endpoints, MCP servers, or training environment. The offline checker requires Python **3.10 or later** and only its standard library.

Install from the GitHub marketplace:

```text
/plugin marketplace add junjiezhou1122/ideascientist-claude-code
/plugin install ideascientist@ideascientist-native
```

The equivalent terminal commands are:

```sh
claude plugin marketplace add junjiezhou1122/ideascientist-claude-code
claude plugin install ideascientist@ideascientist-native
```

Restart Claude Code after installation. If Claude requests permission to read bundled contracts or templates, grant Read access to the plugin files. Loading a plugin does not automatically grant filesystem access to its bundled resources. Use the actual installed path shown by Claude Code rather than a fixed cache version.

To load a local checkout, clone the published repository and start Claude Code from the research project where you want to save outputs:

```sh
git clone https://github.com/junjiezhou1122/ideascientist-claude-code.git
# Replace both paths with the absolute path to your checkout.
claude --plugin-dir /absolute/path/to/ideascientist-claude-code --add-dir /absolute/path/to/ideascientist-claude-code
```

`--add-dir` lets the agents read the bundled [workflow](references/workflow.md), [contracts](references/contracts.md), and [artifact schema](references/artifacts.schema.json). Keep research outputs in your working project.

## Install for Codex

Use Codex CLI with native plugin and multi-agent support. This adapter was loaded with **0.160.0**. Install from the same Git repository:

```sh
codex plugin marketplace add junjiezhou1122/ideascientist-claude-code
codex plugin add ideascientist@ideascientist-native
```

Restart Codex, then invoke `$ideascientist:ideascientist-ideate <research problem>`. The four installed skills use fresh generic native workers with shared role instructions. The coordinator relays paper-reader tasks, so no custom agent configuration or nesting-depth change is required. Use the session's actual multi-agent schemas and native web search capability. See the [Codex guide](docs/codex-plugin.md).

## Install for Pi

Use Pi **1.0.0** or later with the current `@earendil-works` extension API:

```sh
pi install git:github.com/junjiezhou1122/ideascientist-claude-code
```

Restart Pi, then invoke `/ideascientist <research problem>`. The package registers four commands and fresh native role workers. Workers inherit your active model, thinking level and provider authentication. Default research tools use Crossref metadata and public HTML/text without an extra API key. PDF parsing, publisher login and JavaScript rendering require a compatible host tool. See the [Pi guide](docs/pi-package.md).

## Start a research run

```text
/ideascientist:ideate Investigate local credit assignment failures in long-horizon policy learning.
```

The coordinator searches one challenge axis at a time. The gap finder grounds a concrete method deficiency in near-miss work. The innovator proposes one sourced intuition and maps its mechanism to the target setting. A fresh reviewer searches for competing work and tries to disprove novelty, coherence, feasibility, and grounding. Revisions receive new IDs and another review. Only the current surviving candidate advances to a full proposal.

Add a historical cutoff, a run name, or an output language to your request when needed:

```text
/ideascientist:ideate <research problem> cutoff 2025-12-31 slug credit-assignment
```

Without a cutoff, the run uses live literature. A cutoff applies to the exact paper version read. Sources with unknown version dates cannot support a historical run. Output follows your requested language, or the language of your request.

The auxiliary commands support saved runs:

| Action | Claude Code | Codex | Pi |
|---|---|---|---|
| Resume | `/ideascientist:resume` | `$ideascientist:ideascientist-resume` | `/ideascientist-resume` |
| Check evidence | `/ideascientist:check` | `$ideascientist:ideascientist-check` | `/ideascientist-check` |
| Evaluate proposal | `/ideascientist:evaluate` | `$ideascientist:ideascientist-evaluate` | `/ideascientist-evaluate` |

Append `runs/ideascientist/<slug>` to any auxiliary command.

## Native roles

All runtimes share seven scientific role instructions and four entry actions. Claude Code registers seven native agents and four skills. Codex installs four skills that assign the shared roles to fresh generic workers. Pi registers four commands and a bounded native Agent dispatcher. Claude and Pi specialists can call a registered paper-reader directly; Codex uses coordinator relay. The main session normally coordinates the run.

| Agent | Responsibility |
|---|---|
| `orchestrator` | Coordinate state, stable IDs, budgets, and stage decisions from artifacts. |
| `gap-finder` | Find zero to two grounded methodological gaps on one challenge axis. |
| `paper-reader` | Read one registered paper version and answer specific goals with locators. |
| `innovator` | Propose one sourced intuition, or a new revision of a reviewed candidate. |
| `reviewer` | Actively challenge the current candidate and optionally evaluate the proposal. |
| `blind-baseline` | Freeze a derivation from the problem and near misses before candidate exposure. |
| `report-writer` | Develop a surviving intuition into all fourteen proposal fields. |

Default budgets are 24 role calls, 40 searches, and 18 reader calls. Runs allow at most three challenge axes, three candidates per gap, and two revisions per lineage. Reserved allowances remain spent after interruption. If evidence cannot support a gap, the workflow records `no_gap`. If access, verification, or budget blocks progress, it records `blocked` or `unverified` with the reason.

## Inspect the outputs

Each run lives in `runs/ideascientist/<slug>` beneath your research project.

| Artifact | Contents |
|---|---|
| `run.json`, `plan.md`, `problem.md` | State, budgets, selected IDs, decisions, and the research problem. |
| `gaps/A001.json` | Evidence-grounded gaps for one axis. |
| `papers/P001.json` | Exact-version identity, goal answers, locators, and four result-masked views. |
| `discoveries/T001.json` | Bibliographic metadata and reading goals awaiting registration. |
| `candidates/C001.json`, `reviews/C001.json` | One intuition and the independent verdict on that exact candidate. |
| `baselines/G001.json` | A frozen baseline created before the candidate. |
| `report.json`, `report-evidence.json` | The complete proposal and its citation receipts and dependency snapshots. |
| `evaluation.json` | Optional independent evaluation with declared evidence limits. |

The proposal covers the problem, related work, mechanism, formal setting, method, model and training assumptions, comparison with prior work, proposed evaluation, falsifiable predictions, and limitations. Predictions include explicit `kill_condition` fields. Proposed results stay predictions.

The checker rejects broken paper IDs, missing reads, mismatched locators, inadmissible version dates, stale evidence receipts, changed dependency snapshots, and incomplete nested proposal fields:

```sh
python3 /absolute/path/to/ideascientist-claude-code/scripts/check_artifacts.py /absolute/path/to/run --json
```

## Evidence and limits

Roles exchange structured digests instead of raw paper text. Result masking removes reported numerical outcomes and superiority claims from those digests. Search snippets and fetched documents may still reveal results or pages after a historical cutoff. File ownership and role boundaries depend on prompts and tool configuration. They are not a filesystem sandbox or a guarantee of complete blindness.

The offline checker confirms structural consistency. It cannot prove that a citation supports its claim, that a baseline was actually created first, or that an idea is globally novel. Non-obviousness comparison requires a baseline frozen before candidate exposure. Reference matching and citation F1 remain unavailable unless you explicitly supply a reference proposal.

The verification record includes 31 passing offline tests, strict Claude manifest validation, actual Codex and Pi loader checks, deterministic Pi permission and context regressions, and synthetic native reader checks. A complete run on real literature has not been verified. No original benchmark equivalence is claimed. See the [verification record](docs/verification.md), [user guide](docs/claude-code-plugin.md), and [method adaptation](docs/method.md).

## Attribution and license

Original copyright remains **Copyright (c) 2026 The IdeaScientist authors**. This adaptation retains [CC BY-NC 4.0](LICENSE), including attribution and noncommercial terms. The [full legal code](https://creativecommons.org/licenses/by-nc/4.0/legalcode) governs the license.

The adaptation changes execution into native skills and agent prompts, role instructions, file artifacts, provenance receipts, and an offline checker. This repository includes no original runtime code, model weights, or research corpus. The adaptation maintainer is `junjiezhou1122`. See [NOTICE.md](NOTICE.md) for source pointers pinned to the upstream commit.
