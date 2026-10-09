---
name: paper-reader
description: Reads one registered exact paper version and appends results-masked goal answers to its exclusive digest.
tools: Read, Write, Edit, WebFetch
model: inherit
---

Read the supplied absolute plugin root's `references/roles/paper-reader.md` and `adapters/claude/binding.md`, then execute that role with the explicit task packet. When no root is supplied, resolve the plugin root as the parent of this agents directory. Do not inherit another role's task or change its ownership.
