# Background Workers (Point C)

> ruflo runs ~12 auto-triggered workers that proactively hunt problems. Your pipeline is **reactive** — gates only fire when a requirement flows through. These three workers close that gap: they scan the Brain product repo **between** requirements, out-of-band, on a schedule, on Haiku — so they cost little and never slow the critical path.

We build **3**, not 12 — each mapped to an existing VETO owner. Adding more is easy later, but discipline beats count.

| Worker | Skill | Maps to | Cadence (suggested) |
|---|---|---|---|
| Test-gap | `/worker-test-gap` | Tanvi (QA) | daily |
| Canon-drift | `/worker-canon-drift` | Architect / CTO Advisor | every 2–3 days |
| Compliance-drift | `/worker-compliance-drift` | Shreya (Security) — **P0** | twice daily |

---

## Principles

1. **Read-only on product code.** Workers write *findings*, never edit the repo.
2. **Out-of-band.** They never touch `state/active.json` or advance a requirement. They raise findings for humans + the relevant VETO owner.
3. **Cheap.** Bounded scans with a deterministic git/grep pre-filter + a Haiku judgment pass. Schedule them on Haiku.
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

Severe findings also append a line to `.engineering-os/pending-founder-attention.md` and may suggest a remediation `/requirement`. A compliance gap is at least HIGH; a production DND/NCPR risk is P0 and surfaced loudly.

---

## Scheduling

Use the `/schedule` skill (Claude Code routines / cron) to run each worker, ideally on Haiku:

```
/schedule create worker-test-gap        --cron "0 6 * * *"   --model haiku
/schedule create worker-canon-drift     --cron "0 7 */2 * *" --model haiku
/schedule create worker-compliance-drift --cron "0 6,18 * * *" --model haiku
```

(Adjust to your tracker's exact `/schedule` syntax. If you don't schedule them, you can also run any worker manually at any time — they're idempotent and de-duped.)

---

## Why these three (and not a generic "auditor")

Each worker maps to a place the pipeline already has a VETO:

- **Test-gap → Tanvi.** Her G5 gate already blocks on missing tests *during* a requirement; this finds gaps that accumulated *outside* one (e.g., a hot-fix that skipped tests, a coverage regression from a refactor).
- **Canon-drift → Architect/CTOA.** Stage 2 + Stage 6 enforce canon *per requirement*; this catches slow architectural erosion across many requirements.
- **Compliance-drift → Shreya.** Her G4 gate is P0 per requirement; this re-verifies the *whole live surface* regularly, because a compliance regression anywhere is a regulatory incident.

---

## Verification boundary

These workers operate on the **consuming Brain product repo's source**, not on this plugin repo. They can only be exercised against real Brain code. Before relying on them: run each once manually in a Brain repo, confirm the pre-filter returns sensible candidates, and tune the cadence + the grep patterns to the actual directory layout.
