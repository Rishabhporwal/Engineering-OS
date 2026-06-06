# Background Workers

> The pipeline is **reactive** — gates only fire when a requirement flows through. These three workers close that gap: they scan the consuming product repo **between** requirements, out-of-band, on a schedule, on a small model — so they cost little and never slow the critical path.

We build **3** — each mapped to an existing VETO owner. Adding more is easy later, but discipline beats count.

| Worker | Skill | Maps to | Cadence (suggested) |
|---|---|---|---|
| Test-gap | `/worker-test-gap` | QA Engineer | daily |
| Canon-drift | `/worker-canon-drift` | Architect / Engineering Advisor | every 2–3 days |
| Compliance-drift | `/worker-compliance-drift` | Security Reviewer — **P0** | twice daily |

---

## Principles

1. **Read-only on product code.** Workers write *findings*, never edit the repo.
2. **Out-of-band.** They never touch `state/active.json` or advance a requirement. They raise findings for humans + the relevant VETO owner.
3. **Cheap.** Bounded scans with a deterministic git/grep pre-filter + a small-model judgment pass. Schedule them on the cheapest sufficient model tier.
4. **Conservative.** Only flag clear issues with file:line evidence. Noise erodes trust; a "maybe" is not a finding.
5. **De-duped.** An identical open finding is not repeated.

---

## Findings format (shared)

Workers append to `.engineering-os/findings/<worker>.md` (committed — part of the audit trail):

```markdown
## <ISO_TS_UTC> — <worker> — <SEVERITY: LOW|MED|HIGH|P0>
**File(s):** path/to/file.ts:120
**Finding:** one-line description of the gap/drift.
**Canon/gate:** which rule or canon section this violates.
**Recommended action:** open /requirement | note | needs ADR
**Auto-requirement:** <req_id or none>
**Status:** open
```

Severe findings also append a line to `.engineering-os/pending-stakeholder-attention.md` and may suggest a remediation `/requirement`. A compliance gap (against whatever regime `COMPLIANCE.md` declares) is at least HIGH; a production regulatory risk is P0 and surfaced loudly.

---

## Scheduling

Use the `/schedule` skill (Claude Code routines / cron) to run each worker, ideally on the cheapest sufficient model:

```
/schedule create worker-test-gap        --cron "0 6 * * *"   --model haiku
/schedule create worker-canon-drift     --cron "0 7 */2 * *" --model haiku
/schedule create worker-compliance-drift --cron "0 6,18 * * *" --model haiku
```

(Adjust to your tracker's exact `/schedule` syntax. If you don't schedule them, you can also run any worker manually at any time — they're idempotent and de-duped.)

---

## Why these three (and not a generic "auditor")

Each worker maps to a place the pipeline already has a VETO:

- **Test-gap → QA Engineer.** The QA gate already blocks on missing tests *during* a requirement; this finds gaps that accumulated *outside* one (e.g., a hot-fix that skipped tests, a coverage regression from a refactor).
- **Canon-drift → Architect / Engineering Advisor.** The architecture and final-review stages enforce the Canon *per requirement*; this catches slow architectural erosion across many requirements.
- **Compliance-drift → Security Reviewer.** The security gate is P0 per requirement; this re-verifies the *whole live surface* regularly, because a regression against the product's compliance regime anywhere is a regulatory incident.

---

## Verification boundary

These workers operate on the **consuming product repo's source**, not on this plugin repo. They can only be exercised against real product code. Before relying on them: run each once manually in a product repo, confirm the pre-filter returns sensible candidates, and tune the cadence + the grep patterns to the actual directory layout.
