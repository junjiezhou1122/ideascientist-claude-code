---
name: evaluate
description: Independently evaluate a native proposal with explained quality scores, coverage-limited novelty and a previously frozen blind baseline.
argument-hint: "<run directory> [explicit user reference file]"
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Agent, Bash
---

Run inline in the main session. Resolve `${CLAUDE_PLUGIN_ROOT}` as the absolute plugin root. Read `${CLAUDE_PLUGIN_ROOT}/references/commands/evaluate.md` and `${CLAUDE_PLUGIN_ROOT}/adapters/claude/binding.md`, then execute that command for $ARGUMENTS.
