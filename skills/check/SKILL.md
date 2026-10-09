---
name: check
description: Run the standalone offline validator for a native IdeaScientist run's artifacts, evidence receipts and stage dependencies.
argument-hint: "<run directory>"
disable-model-invocation: true
allowed-tools: Read, Bash
---

Run inline in the main session. Resolve `${CLAUDE_PLUGIN_ROOT}` as the absolute plugin root. Read `${CLAUDE_PLUGIN_ROOT}/references/commands/check.md` and `${CLAUDE_PLUGIN_ROOT}/adapters/claude/binding.md`, then execute that command for $ARGUMENTS.
