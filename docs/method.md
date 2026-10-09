# The native IdeaScientist adaptation

IdeaScientist divides scientific ideation into research stages whose inputs, outputs, and evidence can be checked separately. This independent adaptation preserves those stage contracts and runs them through Claude Code agents, Codex native workers and Pi Agent contexts. The repository contains the native plugin and offline checker, without the original runtime code.

## Original concepts and native components

| Original concept | Native counterpart | Preserved constraint |
|---|---|---|
| Orchestrator and plan | Inline `ideate` and `resume` skills, standalone orchestrator, shared workflow | Coordinate from stage artifacts without reading paper bodies. |
| Gap finder | Gap-finder agent and per-axis gap file | Exactly one axis per task and zero to two methodological gaps. |
| Innovator | Innovator agent and one candidate file | One gap and one intuition per task. Cross-domain transfer is preferred. |
| Reviewer | Reviewer agent and candidate review | Active disconfirming search with `survive`, `revise`, `reject`, or `unverified`. |
| Report writer | Report-writer agent and proposal files | Preserve all fourteen proposal fields without invented measurements. |
| Isolated `read_paper` | Foreground native paper-reader calls | One exact paper version and one to five concrete reading goals per call. |
| Stable Vault evidence identity | Coordinator-assigned P IDs and reader-owned paper files | Every citation resolves to a read answer and a precise locator. |
| Result-masked tuple | Four digest views | Preserve `problem_definition`, `challenge`, `intuition`, and `solution`. |
| Mechanism non-obviousness | Baseline frozen before the candidate, later reviewer comparison | Baseline sees only the problem, selected gap, and near-miss digests. |
| Reference-grounded metrics | Optional comparison with an explicitly supplied reference | Without a reference, metrics stay unavailable or null. |

## Research stage contracts

Gap finding explains why methods for the same problem come close yet fail at a specific mechanism. A gap names a deficiency in an algorithm, objective, inductive bias, credit assignment, representation, or another method component. Missing experiments or data alone do not establish a methodological gap. Normally two read near misses support the finding. A narrow problem with only one near miss requires an explicit search-scope rationale.

Innovation identifies a transferable mechanism and explains its source, mapping, required conditions, and failure risk. The candidate remains a short conceptual intuition. Formal algorithms and evaluation design belong to the proposal stage. The reviewer searches for combinations of the borrowed mechanism and target problem to test whether prior work already covers the candidate. A revision receives a new ID and a new review. Rejection permits a different intuition within the finite budget.

The coordinator works from metadata and artifacts. Research roles discover metadata; only isolated readers inspect source bodies. Roles return new sources for coordinator registration before reading under stable P IDs. Claude uses native Agent and web tools. Codex assigns canonical role instructions to fresh generic workers and relays readers through main. Pi uses fresh native Agent contexts and callable host tools, with default Crossref discovery and HTML/text fetching. The shared workflow defines stage behavior, while each runtime binding defines dispatch and available tools.

## Differences from the original system

The original system uses Vault, custom clients, and a training environment for isolation, retrieval, rewards, and evaluation. This adaptation uses file contracts, prompt discipline, nested agents, and native tools. Its training behavior, retrieval coverage, and permission guarantees differ from the original system.

Result masking governs digest outputs. Search snippets and fetched paper bodies may contain published results, so the adaptation does not guarantee a completely blind context. A historical cutoff checks the exact version read. An early v1 publication date does not authorize a later v2. Search may still expose future pages, and the plan and evaluation record that limit.

Independent quality judgments retain actionability, specificity, clarity, impact, soundness, and relevance. Novelty applies only to searched and read coverage. The baseline's frozen file, input list, and `before_candidate` marker make the claimed process reviewable. They are not cryptographic proof of chronology. If no baseline preceded the candidate, non-obviousness remains unevaluated.

The plugin has no privileged reference generation, training labels, GRPO, LoRA, or original benchmark reproduction path. Synthetic offline tests show that the checker rejects missing evidence and incorrect dependencies. They do not establish research quality. Real use requires accessible literature and independent checks of what the evidence supports. The workflow produces a proposal rather than running experiments, training models, or implementing the research.

## Source attribution

This adaptation draws on the upstream [research description](https://github.com/jiarui-liu/IdeaScientist/blob/9613a5e575e4a3f41fcb62609e3c8e80bea819a6/README.md), [role contracts](https://github.com/jiarui-liu/IdeaScientist/blob/9613a5e575e4a3f41fcb62609e3c8e80bea819a6/ideascientist/harness/roles.py), and [proposal structure](https://github.com/jiarui-liu/IdeaScientist/blob/9613a5e575e4a3f41fcb62609e3c8e80bea819a6/ideascientist/vault/schema.py). These links pin upstream commit `9613a5e575e4a3f41fcb62609e3c8e80bea819a6`.

Original work remains attributed to the IdeaScientist authors under [CC BY-NC 4.0](../LICENSE). The adaptation maintainer is `junjiezhou1122`. See [NOTICE.md](../NOTICE.md) for the derivative description and original copyright.
