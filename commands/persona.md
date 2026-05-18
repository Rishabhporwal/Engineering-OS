---
name: persona
description: Manually spawn a dynamic persona for an open question.
argument-hint: "<persona-type> <question>"
---

Manually spawn a dynamic persona to stress-test a question or proposal — outside the normal Stage 1 flow.

Steps:

1. Parse `$ARGUMENTS` into `persona_type` and `question`.
2. Validate `persona_type` against the catalog in [`docs/role-empowerment-model.md`](../docs/role-empowerment-model.md#2-dynamic-persona-generator--dynamic-persona-generator). If invalid, list valid options.
3. **Invoke the `dynamic-persona-generator` subagent** with the persona type and the question.
4. The persona inhabits its role for one round and returns a structured review (≥1 concern mandatory).
5. Print the review.

Useful when you want a second opinion before going through full Stage 1 — e.g., "is this paradigm choice sane?" → spawn `ai-cost-realist`; "what would enterprise procurement say?" → spawn `enterprise-buyer`.
