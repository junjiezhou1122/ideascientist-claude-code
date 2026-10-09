# Use the native Claude Code plugin

Start a research run with `/ideascientist:ideate <research problem>`. The main session coordinates gap discovery, paper reading, mechanism transfer, adversarial review and revision, and a complete proposal. The auxiliary skills resume, check, or evaluate saved runs.

## Load the plugin

Use a current Claude Code version that supports nested subagents. This design was tested with version 2.1.287 and uses at most three agent layers below the main session. All agents use `model: inherit`, your existing login, and the session's model configuration.

The plugin requires no original Python package, Vault database, vector service, custom model endpoint, MCP server, SDK, or training environment. Its offline checker uses Python 3.10 or later and the standard library.

For marketplace installation after the GitHub repository is published, run:

```text
/plugin marketplace add junjiezhou1122/ideascientist-claude-code
/plugin install ideascientist@ideascientist-native
```

The terminal equivalents are:

```sh
claude plugin marketplace add junjiezhou1122/ideascientist-claude-code
claude plugin install ideascientist@ideascientist-native
```

Restart Claude Code after installation. When prompted, grant Read permission for the bundled workflow, contracts, schema, and templates. Plugin loading does not itself grant those filesystem permissions. Use the actual installed resource path reported by Claude Code, without assuming a cache version.

For a local checkout, start Claude Code in the research project where you want to save outputs. Replace both plugin paths with the checkout's absolute path:

```sh
claude --plugin-dir /absolute/path/to/ideascientist-claude-code --add-dir /absolute/path/to/ideascientist-claude-code
```

The repository also provides a single-plugin local marketplace with source `.`. To install a local checkout persistently, run:

```sh
claude plugin marketplace add /absolute/path/to/ideascientist-claude-code
claude plugin install ideascientist@ideascientist-native
```

## Start or continue a run

```text
/ideascientist:ideate Investigate local credit assignment failures in long-horizon policy learning.
/ideascientist:ideate <research problem> cutoff 2025-12-31 slug credit-assignment
/ideascientist:resume runs/ideascientist/credit-assignment
/ideascientist:check runs/ideascientist/credit-assignment
/ideascientist:evaluate runs/ideascientist/credit-assignment
```

`ideate` coordinates inline in the main session. It does not fork the skill context. Without a cutoff, it uses live literature. With a cutoff, the actual version read must have a known date on or before that date. The workflow excludes versions with unknown dates from historical evidence. Output follows your requested language, or the language of your request.

If a run already exists, use `resume` or choose a new slug. The plugin preserves existing runs. Default budgets are 24 role calls, 40 searches, and 18 reader calls. Each gap permits at most three candidates and two revisions per lineage. The run permits at most three challenge axes. Reservations remain spent after interruption. Unsupported gaps produce `no_gap`. Access or verification failures produce `blocked` or `unverified` with a reason.

You can also select `ideascientist:orchestrator` in Claude Code or start with `--agent ideascientist:orchestrator`. That agent reads the same [workflow](../references/workflow.md) as the skills. It has no Bash tool, so it checks artifacts manually or returns an executable checker request to the main session.

## Inspect run artifacts

Outputs live in `runs/ideascientist/<slug>` under your current research project.

| File | Contents and exclusive writer |
|---|---|
| `run.json`, `plan.md`, `problem.md` | State, budgets, selected IDs, decisions, and problem input. The coordinator writes them. |
| `gaps/A001.json` | Zero to two gaps on one axis. The gap finder writes it. |
| `candidates/C001.json` | One intuition for one gap. The innovator writes it. |
| `reviews/C001.json` | An independent verdict on the exact candidate. The reviewer writes it. |
| `papers/P001.json` | One version's digest and accumulated goal answers. The paper reader writes it. |
| `discoveries/T001.json` | One task's metadata registration request. The requesting role writes it. |
| `baselines/G001.json` | A blind baseline frozen before candidate exposure. The baseline agent writes it. |
| `report.json`, `report-evidence.json` | The fourteen-field proposal and evidence receipt. The report writer writes them. |
| `evaluation.json` | Optional independent quality, scoped novelty, and non-obviousness judgments. The reviewer writes it. |

A role first discovers papers and returns metadata. The coordinator assigns stable P IDs and invokes the role again. The role calls the paper reader directly in the foreground and reads its structured digest. Roles and readers run sequentially to avoid concurrent edits. If nested Agent calls are denied, the main session can relay the same reader packet and return only the digest.

## Check artifacts offline

The checker inspects saved artifacts. It does not retrieve literature or execute agents.

```sh
python3 /absolute/path/to/ideascientist-claude-code/scripts/check_artifacts.py /absolute/path/to/run --json
python3 /absolute/path/to/ideascientist-claude-code/scripts/check_plugin.py
python3 -m unittest discover -s /absolute/path/to/ideascientist-claude-code/tests -p 'test_native_*.py' -v
claude plugin validate /absolute/path/to/ideascientist-claude-code/.claude-plugin/plugin.json --strict --json
claude plugin validate /absolute/path/to/ideascientist-claude-code/.claude-plugin/marketplace.json --strict --json
claude --plugin-dir /absolute/path/to/ideascientist-claude-code plugin details ideascientist
```

Tests use explicitly labeled synthetic offline data. They are not real literature or successful research runs. `create_run(path)` in `tests/native_fixture.py` generates a complete synthetic run for CLI checks. The [artifact schema](../references/artifacts.schema.json) defines structured field names and types. Empty template values are writing inputs, not valid completed artifacts.

## Understand the limits

Agent tool lists restrict tool names, not filesystem paths. File ownership, raw-paper boundaries, and the coordinator's separation from paper bodies depend on prompt discipline. They do not provide a filesystem security sandbox. The plugin includes no hooks or permission settings.

The reader's four result-masked views retain problems, mechanisms, and designs while removing reported metrics and outcome claims. Search snippets and fetched text can still reveal results. Historical search can expose pages after the cutoff. The plugin therefore cannot guarantee complete result or historical blindness, and it does not reproduce the original trained adapters, corpus-scale retrieval, or benchmark scores.

The checker confirms IDs, read receipts, locators, dates, stage dependencies, and nested fields. Receipts preserve exact answers and full input snapshots. Changes under the same ID invalidate downstream artifacts. Adding new reading goals preserves earlier valid evidence. The checker cannot prove semantic support, actual execution chronology, global novelty, or a baseline's true lack of candidate exposure. Independent review remains necessary.

Non-obviousness comparison requires a baseline frozen before the candidate. Otherwise it stays unavailable. Reference matching and citation F1 remain unavailable or null unless you explicitly provide a reference proposal. The plugin produces proposals. It does not run experiments, train models, or implement research code.

## Attribution

This is an independent translation/adaptation of the IdeaScientist authors' research methodology. It retains [CC BY-NC 4.0](../LICENSE). Read the [adaptation explanation](method.md), [verification record](verification.md), and [attribution notice](../NOTICE.md) for pinned upstream sources and evidence boundaries.
