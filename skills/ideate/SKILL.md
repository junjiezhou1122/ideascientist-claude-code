---
name: ideate
description: Start a bounded native IdeaScientist run for a research problem, grounded gaps, one intuition and an independently reviewed proposal.
argument-hint: "<research problem> [cutoff YYYY-MM-DD] [slug]"
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Agent, Bash
---

Run inline in the main session. Resolve `${CLAUDE_PLUGIN_ROOT}` as the absolute plugin root. Read `${CLAUDE_PLUGIN_ROOT}/references/commands/ideate.md` and `${CLAUDE_PLUGIN_ROOT}/adapters/claude/binding.md`, then execute that command for $ARGUMENTS. Read `${CLAUDE_PLUGIN_ROOT}/references/workflow.md`.
