---
name: skill
description: Manually invoke a curated skill outside the pipeline.
arguments:
  - name: skill_name
    description: One of the 54 skill IDs (e.g., security-baseline, india-commerce-economics).
    required: true
---

Manually invoke a curated skill. Used when you (the operator) want the skill's discipline applied to ad-hoc work, outside the pipeline.

Steps:

1. Locate the skill at `plugin-skills/$ARGUMENTS/SKILL.md`. If not found, suggest the closest match from [`docs/skill-mapping-matrix.md`](../docs/skill-mapping-matrix.md).
2. Read the skill body.
3. Apply the skill to whatever the operator has in front of them right now (the current conversation, the open file, the just-failed test).
4. If the skill specifies an owner persona, surface that ("This is primarily Shreya's skill; want me to delegate?").
