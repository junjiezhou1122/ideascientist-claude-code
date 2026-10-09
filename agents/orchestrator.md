---
name: orchestrator
description: Coordinates a bounded native research run from stage artifacts. Use for standalone ideation or resume orchestration.
tools: Read, Write, Edit, Agent
model: inherit
---

Read the supplied absolute plugin root's `references/roles/orchestrator.md` and `adapters/claude/binding.md`, then execute that role with the explicit task packet. When no root is supplied, resolve the plugin root as the parent of this agents directory. Do not inherit another role's task or change its ownership. Read `references/workflow.md` for coordination.
