---
name: check
description: Run the standalone offline validator for a native IdeaScientist run's artifacts, evidence receipts and stage dependencies.
argument-hint: "<run directory>"
disable-model-invocation: true
allowed-tools: Read, Bash
---

Read `${CLAUDE_PLUGIN_ROOT}/references/contracts.md`. Run only the artifact check against $ARGUMENTS, with the actual absolute plugin root and run directory safely shell-quoted as separate arguments.

```sh
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_artifacts.py" "<absolute run directory>" --json
```

This stdlib script validates files offline. It does not run agents, import the original system, retrieve papers or assess scientific truth. Report the actual exit status and errors. A pass verifies structural receipts and state, not semantic support, execution chronology, permission isolation, novelty or originality. Do not edit run artifacts from this read-only check command.
