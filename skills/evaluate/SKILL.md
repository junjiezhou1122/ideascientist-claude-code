---
name: evaluate
description: Independently evaluate a native proposal with explained quality scores, coverage-limited novelty and a previously frozen blind baseline.
argument-hint: "<run directory> [explicit user reference file]"
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Agent
---

Run inline. Read `${CLAUDE_PLUGIN_ROOT}/references/workflow.md`, `${CLAUDE_PLUGIN_ROOT}/references/contracts.md`, and the evaluation definition in `${CLAUDE_PLUGIN_ROOT}/references/artifacts.schema.json`. Validate the selected candidate, its survive review, report and evidence receipt in $ARGUMENTS. Allocate a finite evaluation task as coordinator under the shared budget reservation protocol. Pass plugin root, run directory, permitted paths, target candidate and evaluation mode to a fresh FOREGROUND `ideascientist:reviewer`.

The reviewer may discover and request registered readers, following the shared relay. Give an existing valid frozen blind baseline only now. Missing or contaminated baselines mean nonobviousness unavailable. Do not generate a baseline after proposal exposure. Reference metrics stay unavailable/null unless the user explicitly supplies a file. Record evaluated only after the full evaluation artifact and receipts pass. If evaluation already exists, preserve it by reporting it, or create a separate new run when the user wants a changed research target. Explain score scale, searched coverage and limits in the user's language.
