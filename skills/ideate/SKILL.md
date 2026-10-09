---
name: ideate
description: Start a bounded native IdeaScientist run for a research problem, grounded gaps, one intuition and an independently reviewed proposal.
argument-hint: "<research problem> [cutoff YYYY-MM-DD] [slug]"
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Agent
---

Run this skill inline in the main session. The main session is the coordinator. Read `${CLAUDE_PLUGIN_ROOT}/references/workflow.md` and `${CLAUDE_PLUGIN_ROOT}/references/contracts.md`, then execute their start and dispatch protocol for $ARGUMENTS. Use `${CLAUDE_PLUGIN_ROOT}/references/artifacts.schema.json` and templates as writing contracts. Pass the resolved absolute plugin root to each agent.

Create an unused `runs/ideascientist/<slug>` in the user's working project, finite budgets and selected IDs in run.json, and plan.md. Do not delegate the entire run by default. Launch substantive native agents foreground and let them launch the registered paper-reader foreground. Perform discovery-registration relays, freeze blind baseline before innovation, review every new candidate ID and stop honestly on unavailable evidence. If nesting is denied, perform the documented main-session reader relay. Return the resulting proposal or no-gap/blocked finding in the user language with absolute artifact paths.
