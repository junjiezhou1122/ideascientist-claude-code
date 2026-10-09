---
name: resume
description: Validate a saved native IdeaScientist run and continue its next admissible stage without resetting budgets or overwriting outputs.
argument-hint: "<run directory>"
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Agent
---

Run inline in the main session. Resolve `${CLAUDE_PLUGIN_ROOT}` as the absolute plugin root. Read `${CLAUDE_PLUGIN_ROOT}/references/commands/resume.md` and `${CLAUDE_PLUGIN_ROOT}/adapters/claude/binding.md`, then execute that command for $ARGUMENTS. Read `${CLAUDE_PLUGIN_ROOT}/references/workflow.md`.
