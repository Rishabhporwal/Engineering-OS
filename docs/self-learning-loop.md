# Self-Learning Loop (Point B)

> ruflo's "ReasoningBank" logs trajectories and feeds successful patterns back into routing — automatically, ungoverned. You already had the pieces (lessons registry, `propose-rule`/`adopt-rule`, retros). Point B closes the loop **without** giving up the human gate: the system *proposes* rules from recurring patterns; a human *adopts* them.

---

## The closed loop

```
Stage 6 retro (14-retro.md)                       ← written every standard/high-stakes run
        │
        ▼  Rohan checks: is this bounce/failure a REPEAT?
   semantic recall over past retros + decision-log bounces  (Point A)
   + grep lessons-learned.md
        │
   same root cause in ≥3 distinct runs?
        │ yes                                   │ no
        ▼                                       ▼
   write rule-proposal  ───────────────▶   nothing (it's a lesson, not yet a rule)
   .engineering-os/rule-proposals/<slug>.md
   + line in pending-founder-attention.md
        │
        ▼  HUMAN GATE
   /adopt-rule <slug>      |     /reject-rule <slug> <reason>
        │
        ▼
   durable rule  ──▶  consulted by Rohan at every Stage 1 intake
```

The only new behaviour is the **detection + proposal** step (Rohan Stage 6, step 8a). Everything downstream — `rule-proposals/`, `durable-rules/`, `/adopt-rule`, `/reject-rule`, the lessons registry — already existed.

---

## Why ≥3, and why human-gated

- **≥3 occurrences** is the threshold between *coincidence* and *pattern*. One bounce is a lesson (it lives in the retro). Three identical root causes across distinct features is a process gap worth a durable rule. This keeps the rule set small and high-signal.
- **Human-gated adoption** is the deliberate difference from ruflo. A system that silently rewrites its own rules is unauditable and can drift into nonsense. Here, a human reads the evidence (the ≥3 cited `req_id`s) and decides. The proposal is automatic; the commitment is human. That preserves the audit moat.

---

## What composes here

- **Point A (semantic memory)** does the detection — finding past retros/bounces with the *same meaning*, which a keyword grep would miss (e.g., "UAE DLT registration missing" ≈ "GCC telecom registration not wired").
- **The existing self-improvement substrate** (`propose-rule`/`adopt-rule`/`reject-rule` + `rule-proposals/` + `durable-rules/` + `lessons-learned.md`) does everything after detection.

Point B is the thin connective tissue that turns a pile of retros into a governed, compounding rule set.

---

## Verification boundary

The detection step runs inside Rohan's Stage 6, which requires a real multi-run history to fire (it needs ≥3 prior matching retros). Exercise it after the OS has accumulated several runs, or seed `lessons-learned.md` + a few retros and confirm a proposal is generated and lands in `rule-proposals/` (not auto-adopted).
