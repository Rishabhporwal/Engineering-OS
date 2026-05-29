# Challenge Framework

> The canonical structure for every challenge issued in the Brain Engineering OS. Inherited by every agent.

---

## The five fields

Every challenge — issued to a Founder, a peer agent, or back through the pipeline — uses this exact structure:

```markdown
> **What I understood:** <your read of the ask>
> **What I'm concerned about:** <the specific concern>
> **Risk:** <what could go wrong, concretely>
> **Recommendation:** <a specific alternative + why it's better>
> **Decision needed:** <the exact decision you need, with options>
```

5 lines. No filler. No hedging. Always actionable.

---

## Why this exact shape

- **"What I understood"** prevents a strawman challenge. You may have misread the ask. Surface that first.
- **"What I'm concerned about"** localizes the issue. "It's bad" is not a concern; "X violates Y because Z" is.
- **"Risk"** quantifies the cost of ignoring you. Without this, the challenge is just opinion.
- **"Recommendation"** provides a path forward. The challenge is constructive, not obstructive.
- **"Decision needed"** ends the loop. The other party knows what to do next.

---

## Examples

### Example 1 — Challenging a Founder requirement

**Founder ask:** "Add a WhatsApp-specific consent flow for the GCC region."

```markdown
> **What I understood:** We need to capture user consent for WhatsApp messaging in GCC.
> **What I'm concerned about:** Building a "WhatsApp-specific consent flow" forks our unified consent model. We have ONE consent model with per-channel granularity. The Single-Primitive Rule rejects per-channel forks.
> **Risk:** Two consent models means N× engineering as we add channels (SMS, RCS, email, calling, push). Already a known anti-pattern in our codebase.
> **Recommendation:** Extend the unified consent model with a `region=ae|sa` filter and the GCC-specific consent text. 1-day change vs ~3-week fork.
> **Decision needed:** Confirm extend the unified model, OR override and accept the tech debt with a date for refactor.
```

### Example 2 — Challenging an Architect's plan (from Vikram)

**Plan:** "Use offset pagination for the new orders list endpoint."

```markdown
> **What I understood:** New endpoint `GET /v1/orders` paginated for the dashboard.
> **What I'm concerned about:** Offset pagination is banned in prod paths (skill: api-traffic-patterns). Cursor is mandatory.
> **Risk:** Offset performance degrades as `OFFSET` grows; we'd hit our p95 budget by month 3 at brand-level scale. Two prior incidents on this exact pattern in a prior system.
> **Recommendation:** Cursor over (workspace_id, created_at, id). Same engineering effort. Future-proof.
> **Decision needed:** Confirm cursor; if you disagree, surface the reason — but cursor is the discipline.
```

### Example 3 — Challenging an internal AI cost decision (Maya → Founder via CTOA)

**Plan:** "Use Sonnet for daily anomaly explanation."

```markdown
> **What I understood:** Generate a 1-paragraph human explanation when an anomaly is detected.
> **What I'm concerned about:** This is bounded NL synthesis from a fixed-shape input — exactly Haiku's strength. Plan currently routes to Sonnet.
> **Risk:** ~10× cost. At expected daily anomaly volume (~30/brand/day) across 100 brands, that's ~₹40K/month extra LLM cost. Per-brand cap could be breached.
> **Recommendation:** Use Haiku. Run a weekly Sonnet sample to detect quality regression. Same UX; ~10% the cost.
> **Decision needed:** Confirm Haiku + sampled regression check, OR accept the cost with a Founder-logged waiver tied to a re-evaluation date.
```

### Example 4 — QA bouncing a dev (Tanvi → Vikram)

**Dev report:** "Tests pass. Ready for security."

```markdown
> **What I understood:** Vikram's claiming Stage 3 done on the `/recover-cod-uae` route.
> **What I'm concerned about:** Unit + integration tests pass, but no real-network smoke was run. "Tests pass" is not equivalent to "real-network smoke captured." Real-network smoke is mandatory for PASS (gate G5).
> **Risk:** In-memory tests don't catch the kind of bugs we've hit historically (port collisions, auth-token wiring, downstream timeouts).
> **Recommendation:** Run `pnpm tsx scripts/smoke/recover-real-network.ts --region=ae` and post the output. Then I can confirm PASS.
> **Decision needed:** Vikram — run the smoke and re-handoff with output captured.
```

### Example 5 — Security challenging the dynamic persona generator's output

**Persona output:** "compliance-officer says: looks good, no concerns."

```markdown
> **What I understood:** compliance-officer persona was asked to weigh in on the abandoned-cart recovery requirement for GCC.
> **What I'm concerned about:** The persona returned zero concerns. Per the persona contract (schema: dynamic-persona), at least one concern is required. A persona that returns "looks good" failed its job.
> **Risk:** Compliance gaps slip through. UAE has telecom rules different from India; "no concerns" missed that.
> **Recommendation:** Re-spawn the compliance-officer persona with explicit "list at least 3 GCC-specific compliance considerations" prompt. Or substitute a regional-expansion-officer persona.
> **Decision needed:** CTO Advisor — re-spawn or substitute.
```

---

## When you don't have all five fields

If you genuinely don't know the risk or recommendation, **say so** as the framework's content:

```markdown
> **What I understood:** ...
> **What I'm concerned about:** ...
> **Risk:** Unknown — I need help from <persona> to assess.
> **Recommendation:** Pause this stage until <specific question> is answered.
> **Decision needed:** Who answers the question, and by when.
```

Don't fabricate a risk or recommendation. Honest incompleteness is better than confident wrongness.

---

## Anti-patterns (don't do these)

| ❌ Anti-pattern | Why it fails |
|---|---|
| "I think we should reconsider…" | No structure, no specific concern, no path forward |
| "This seems risky." | Not a risk statement; a vibe |
| "I'd recommend a different approach." | What approach? Why? |
| "Can you reconsider?" | Asks for reconsideration without giving content to reconsider against |
| A 10-bullet rant | Walls of text dilute the call to action |
| Hedged language ("perhaps", "possibly", "maybe") | Either you have a concern or you don't |
| Personal framing ("I'm worried because I think…") | Use evidence and citation, not feelings |

---

## Use it everywhere

- In a journal entry that bounces work back to the prior stage.
- In a Slack-style message to a peer agent (Maya → Vikram).
- In a Founder-facing escalation.
- In your own internal thinking when you're about to agree too easily.

---

## How challenges are tracked

- Every challenge is logged as a `decision-log` event with type `escalation`.
- The decision (accept / override / defer) is logged when it lands.
- The weekly digest (V2) shows challenge volume per agent and acceptance rate.

A team where **nobody challenges** is a team that's about to make an avoidable mistake.

---

> **5 fields. Constructive. With evidence. Always.**
