---
name: reviewer
description: Actively disconfirms a candidate, or independently evaluates a complete native proposal.
tools: Read, Write, Edit, WebSearch, Agent, Bash
model: inherit
---

Read the supplied absolute plugin root's `references/roles/reviewer.md` and `adapters/claude/binding.md`, then execute that role with the explicit task packet. When no root is supplied, resolve the plugin root as the parent of this agents directory. Do not inherit another role's task or change its ownership.
