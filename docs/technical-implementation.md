# Section 4.2 — Technical Implementation

> Concrete artifacts the plugin produces and consumes: example state shapes, example workflow payload, example decision-log entries, example agent invocation, example end-to-end run trace.

This document gives a developer enough concrete material to extend the plugin without guessing.

---

## State file shapes

### `.engineering-os/state/active.json`

Tracks every requirement currently in flight (anything not yet `shipped`, `rejected`, or `killed`).

```json
{
  "schema_version": 1,
  "updated_at": "2026-05-17T14:32:00Z",
  "updated_by": "rishabh",
  "active_requirements": [
    {
      "req_id": "feat-abandoned-cart-recovery-gcc",
      "title": "Abandoned cart recovery for COD orders in GCC",
      "submitted_by": "rishabh",
      "submitted_at": "2026-05-15T09:14:00Z",
      "status": "security-review",
      "stage": 4,
      "current_owner": "security-reviewer",
      "current_owner_persona": "shreya",
      "tagged_builders": ["backend-developer", "intelligence-engineer"],
      "run_dir": ".engineering-os/runs/2026-05-15T09-15-22Z__feat-abandoned-cart-recovery-gcc__rishabh",
      "last_journal_entry_at": "2026-05-17T13:50:00Z",
      "blocking_on": null,
      "due_signal": null
    }
  ]
}
```

**Conflict policy:** Last-write-wins on this file. Every agent **re-reads it before acting**. A `.bak.<ts>` copy is written on each save so a corrupted state is recoverable.

### `.engineering-os/state/registry.json`

Append-only canonical list of every `req_id` ever seen.

```json
{
  "schema_version": 1,
  "requirements": [
    { "req_id": "feat-abandoned-cart-recovery-gcc", "first_seen": "2026-05-15T09:14:00Z", "title": "..." },
    { "req_id": "feat-cm-waterfall-rto", "first_seen": "2026-04-30T11:02:00Z", "title": "..." }
  ]
}
```

---

## Decision log shape

`.engineering-os/decision-log/<YYYY>/<MM>/<YYYY-MM-DD>.jsonl` — one JSON object per line.

### Example: stage advancement

```json
{"ts":"2026-05-15T09:31:00Z","actor":"cto-advisor","type":"stage-advance","req_id":"feat-abandoned-cart-recovery-gcc","from_stage":1,"to_stage":2,"to_owner":"architect","rationale":"Requirement is clear; 2 personas concurred; paradigm should be SQL (RFM lookup + rule-based)."}
```

### Example: persona spawn

```json
{"ts":"2026-05-15T09:18:00Z","actor":"cto-advisor","type":"persona-spawn","req_id":"feat-abandoned-cart-recovery-gcc","persona_count":2,"personas":["compliance-officer","regional-expansion-officer"]}
```

### Example: bounce

```json
{"ts":"2026-05-17T13:50:00Z","actor":"security-reviewer","type":"bounce","req_id":"feat-abandoned-cart-recovery-gcc","from_stage":4,"to_stage":3,"to_owner":"backend-developer","rationale":"Missing requireRole on POST /v1/lifecycle/recover-cod-uae","gate":"G4","finding_severity":"HIGH","blocking":true}
```

### Example: founder decision

```json
{"ts":"2026-05-18T10:02:00Z","actor":"rishabh","type":"decision","req_id":"feat-abandoned-cart-recovery-gcc","topic":"founder-approval","decision":"approved","rationale":"Cost is in budget; addresses founding-cohort UAE pilot ask."}
```

### Example: escalation (pending)

```json
{"ts":"2026-05-17T14:32:00Z","actor":"cto-advisor","type":"escalation","to":"founder","req_id":"feat-abandoned-cart-recovery-gcc","topic":"paradigm-change","summary":"Confirm Haiku over Sonnet for recovery messaging; ~10x cost saving.","decision":"pending","decided_at":null}
```

### Querying the log

In MVP, agents query the log with `grep` and `jq`:

```bash
# Every event for a requirement
grep -h '"req_id":"feat-abandoned-cart-recovery-gcc"' .engineering-os/decision-log/**/*.jsonl | jq

# Every founder decision in May 2026
cat .engineering-os/decision-log/2026/05/*.jsonl | jq -c 'select(.actor=="rishabh" and .type=="decision")'

# Time spent in each stage for a requirement
cat .engineering-os/decision-log/**/*.jsonl | jq -c 'select(.req_id=="feat-abandoned-cart-recovery-gcc")' | sort
```

V2 adds a `/digest` slash command that wraps these queries into one weekly report.

---

## Run folder layout

`.engineering-os/runs/<ISO-ts>__<req-id>__<operator>/` — one folder per "session of activity" on a requirement. A single requirement can have multiple runs (e.g., after a bounce, the next attempt is a new run).

```
.engineering-os/runs/2026-05-15T09-15-22Z__feat-abandoned-cart-recovery-gcc__rishabh/
├── 01-requirement.md                  # raw Founder text (from /requirement)
├── 02-cto-advisor-review.md           # Stage 1 output
├── 03-persona-compliance-officer.md          # Stage 1 — persona 1 of 2 (0–2 by complexity)
├── 04-persona-regional-expansion-officer.md  # Stage 1 — persona 2 of 2
├── 06-architecture-plan.md            # Stage 2 output
├── 07-handoff-to-developer.md         # Stage 2 — calibrated dev brief
├── 08-developer-report-vikram.md      # Stage 3 — BE track (08 + persona suffix)
├── 08-developer-report-maya.md        # Stage 3 — AI track (parallel; suffix avoids collision)
├── 09-security-review.md              # Stage 4 output (PASS or BOUNCE)
├── 10-qa-review.md                    # Stage 5 output
├── 11-final-review.md                 # Stage 6 output
├── 12-founder-decision.json           # Stage 7
├── 13-deployment-report.md            # Stage 8
└── 14-retro.md                        # Stage 6 retro → lessons-learned registry
```

Numeric prefix preserves chronological ordering even when filenames don't sort alphabetically by stage.

**Conflict-proofing:** the run folder's ISO timestamp + operator suffix means **no two operators ever create the same folder path**. Two operators picking up the same requirement at the same moment produce two parallel runs; CTO Advisor reconciles on next pass.

---

## Per-agent journal shape (`.engineering-os/memory/agents/<role>.journal.md`)

Append-only. Each entry is a markdown section.

```markdown
## 2026-05-17T14:32:00Z — Vikram (backend-developer) — feat-abandoned-cart-recovery-gcc
**Stage:** 3 (parallel dev)
**Action:** Implemented Fastify route POST /v1/lifecycle/recover-cod-uae in api-gateway.
**Skills loaded:** backend-fastify-trpc-grpc, idempotency-handling, api-rate-limiting, defense-in-depth-validation, india-commerce-economics (UAE specifics), cost-routing-paradigms, verification-before-completion.
**Paradigm:** SQL (no LLM, no ML — rule-based with RFM segment lookup).
**Decisions:**
- Reused single Audience Builder (no new primitive — Single-Primitive Rule).
- Idempotency key = (workspace_id, cart_id, recovery_attempt_n).
- Wired requireRole(operator) on the mutation endpoint.
- Added rate limit override for high-volume cohort (300 rpm, justified in code comment).
**Open questions:** None.
**Handoff signal:** READY-FOR-SECURITY. Shreya tagged.
**Verification:**
- Command: `pnpm vitest run apps/api-gateway/test/recover-cod-uae.test.ts`
- Output: 14 passed, 0 failed in 421ms.
- Command: `pnpm tsx scripts/smoke/recover-real-network.ts --region=ae`
- Output: 200 OK; idempotency-hit on 2nd call (HTTP 200 + same body); audit log entry visible.
- Command: `pnpm eslint apps/api-gateway/src/routes/lifecycle/`
- Output: 0 errors, 0 warnings.
```

The journal **is** the history. When a teammate runs `git pull` and opens Claude Code, the session-start hook surfaces the last 5 entries of each relevant journal into the new session's context.

---

## Per-feature journal shape (`.engineering-os/memory/features/feat-<slug>.md`)

Same entry shape as the per-agent journal, but **every agent** that touches the feature appends here too. This is the canonical answer to "what's been done on feature X?"

```markdown
# feat-abandoned-cart-recovery-gcc

## 2026-05-15T09:14:00Z — Rishabh (founder) — submission
> Add abandoned cart recovery for COD orders in the GCC region. Use the existing RFM segment. Don't break the India path.

## 2026-05-15T09:31:00Z — Rohan (cto-advisor) — Stage 1 complete (ADVANCE)
Persona count = 2 spawned: compliance-officer, regional-expansion-officer.
All concurred. One concern from compliance-officer: GCC has no equivalent of DLT/NCPR, but UAE does have time-window constraints for outbound calls (use UAE-specific window 09:00–22:00 GST). Paradigm recommended: SQL. Handed to Aryan.

## 2026-05-15T11:02:00Z — Aryan (architect) — Stage 2 complete
Plan: extend lifecycle-service's recover flow with `region=ae|sa`. New table `gcc.recovery_windows`. New event `intelligence.recovery.recommended.v1`. Paradigm: SQL. No new primitives. 2 tracks: @vikram (api-gateway route + lifecycle-service handler), @maya (RFM segment lookup in Python). See run folder.

## 2026-05-17T13:48:00Z — Vikram (backend-developer) — Stage 3 — backend track READY-FOR-SECURITY
[full entry as above]

## 2026-05-17T13:50:00Z — Maya (intelligence-engineer) — Stage 3 — AI track READY-FOR-SECURITY
[full entry]

## 2026-05-17T14:15:00Z — Shreya (security-reviewer) — Stage 4 BOUNCE
**Finding (HIGH):** POST /v1/lifecycle/recover-cod-uae is missing the calling-window assertion. UAE calling window is 09:00–22:00 GST; current code skips the window check when `region != 'in'`. Bouncing to @vikram with a 2-line fix.

## 2026-05-17T15:40:00Z — Vikram (backend-developer) — Stage 3 (bounce-back) RESOLVED
Added UAE calling-window assertion using region-adapter. Re-ran smoke; window enforcement confirmed. Re-handoff READY-FOR-SECURITY.
```

When `/recall feat-abandoned-cart-recovery-gcc` is invoked, the agent prints this exact file.

---

## Slash command body example

`skills/requirement/SKILL.md` (a command-skill — invoked by a human typing `/brain-engineering-os:requirement <text>`):

```markdown
---
name: requirement
description: Submit a new requirement to the Engineering OS pipeline (Stage 1)
disable-model-invocation: true
argument-hint: <requirement text in natural language>
---

You are processing a new requirement submission from the Founder.

The Founder's requirement text is:
> $ARGUMENTS

Steps:
1. Read [.engineering-os/state/active.json](.engineering-os/state/active.json) and [.engineering-os/state/registry.json](.engineering-os/state/registry.json) to ensure no duplicate.
2. Generate a kebab-cased `req-<slug>` ID from the requirement summary.
3. Create the run folder: `.engineering-os/runs/<ISO-timestamp>__<req-id>__<operator>/`.
4. Write `01-requirement.md` containing the raw text + metadata (submitted_by, submitted_at).
5. Update `state/active.json` and `state/registry.json`.
6. **Invoke the `cto-advisor` subagent** with the requirement text and run folder. The CTO Advisor will run Stage 1.

When done, print:
- The generated req_id.
- The run folder path.
- A one-line "handoff to CTO Advisor (Stage 1)" confirmation.
```

---

## Agent invocation example (the `cto-advisor` subagent)

When invoked by `/requirement`, the CTO Advisor subagent runs in its own sub-conversation. Its system prompt is the body of [`agents/cto-advisor.md`](../agents/cto-advisor.md) (built in Section 6). Its first action is always:

1. **Load the shared system prompt** (anti-blind-agreement + journal-on-every-action discipline).
2. **Load `docs/business-context.md`** and **`docs/technical-context.md`** (the canon primers).
3. **Load the requirement** from the run folder.
4. **Load the last 5 entries of its own journal** for continuity.

Then it executes Stage 1 as defined in [workflow.md §Stage 1](workflow.md#stage-1--cto-advisor-intake--brainstorm).

For persona spawning, the CTO Advisor uses Claude Code's `Agent` tool to spawn the `dynamic-persona-generator` subagent **three times in parallel**, each with a different persona-type argument.

---

## End-to-end run trace (illustrative)

A complete trace from Founder submission to production deploy, showing what files are written when. (Realistic 3-day timeline.)

| Time | Action | Files written |
|------|--------|---------------|
| Day 1 09:14 | Founder runs `/requirement "Abandoned cart recovery for COD orders in GCC"` | `01-requirement.md`, `state/active.json` updated |
| Day 1 09:18 | Rohan (CTO Advisor) reads canon + spawns 2 personas (parallel) | (in-memory) |
| Day 1 09:24 | 2 persona reviews returned | `03-04-persona-*.md` (×2) |
| Day 1 09:31 | CTO Advisor synthesis + ADVANCE | `02-cto-advisor-review.md`, journal entry, decision-log entry, state status → `architect` |
| Day 1 09:32 | Aryan picks up Stage 2 | (in-memory) |
| Day 1 11:02 | Aryan plan complete | `06-architecture-plan.md`, journal, state → `dev-parallel`, tracks tagged `@vikram` + `@maya` |
| Day 1–2 | Vikram + Maya implement in parallel | code, tests, migrations + journal entries per task |
| Day 2 17:30 | Both post READY-FOR-SECURITY | `08-developer-report-vikram.md`, `08-developer-report-maya.md`, state → `security-review` |
| Day 2 17:35 | Shreya reads + scans | (in-memory; vuln scan output captured to artifacts/) |
| Day 2 18:01 | Shreya finds HIGH: missing UAE window assertion → BOUNCE | `09-security-review.md` (FAIL), journal, decision-log, state → `dev-parallel` (security-bounced) |
| Day 3 09:40 | Vikram fixes + re-handoff | journal entry, state → `security-review` again |
| Day 3 09:55 | Shreya re-reviews → PASS | `09-security-review.md` (overwrite/append?) — append a new section with PASS verdict, state → `qa-review` |
| Day 3 10:30 | Tanvi runs all test categories + real-network smoke + parity check | `10-qa-review.md`, all command outputs captured |
| Day 3 11:15 | Tanvi PASS | state → `final-review` |
| Day 3 12:00 | CTO Advisor final review | `11-final-review.md`, state → `awaiting-founder` |
| Day 3 14:30 | Founder runs `/approve feat-abandoned-cart-recovery-gcc` | `12-founder-decision.json`, decision-log, state → `approved` |
| Day 3 14:35 | Jatin runs CI + staging deploy | (CI logs in artifacts/) |
| Day 3 15:20 | Staging smoke green | state → `awaiting-prod-deploy` |
| Day 3 15:45 | Production deploy (canary 10%, then 100%) | (deploy log in artifacts/) |
| Day 3 16:00 | 48h monitor begins | state → `monitoring` |
| Day 5 16:00 | 48h clean | `13-deployment-report.md` final section, state → `shipped` |

Every entry above is reproducible from the git history of `.engineering-os/`.

---

## Example: re-bounce overwrite policy

When a stage bounces and is re-attempted, the artifact file (e.g., `09-security-review.md`) is **appended to, not overwritten**, with a clear "## Re-review on <ts>" heading. This preserves audit trail. The journal entry and decision log capture the bounce + the fix.

---

## Example: a parallel-operator collision

**Scenario:** Alice and Bob both pull at the same commit. Alice submits `feat-X`; Bob submits `feat-Y`. Both push.

- Alice's commit adds files in `runs/2026-05-17T10-00-00Z__feat-X__alice/` and appends to `state/active.json`.
- Bob's commit adds files in `runs/2026-05-17T10-00-00Z__feat-Y__bob/` (or different second) and appends to `state/active.json`.

**The only point of contention is `state/active.json`.** Git resolves the JSON merge conflict — usually trivially (both added to `active_requirements` array). If git can't resolve it, the second pusher resolves manually. Per-run folders never collide because of operator suffix.

Detailed mechanics: [memory-and-git-sync.md](memory-and-git-sync.md).

---

## Example: a parallel-operator collision on the **same** requirement

**Scenario:** Alice and Bob both pick up `feat-Z`'s next stage at once.

This is rare but possible. The protocol:

1. **First-to-write wins on `state/active.json`** — whoever pushes first updates the status.
2. **Second-to-write sees the change on pull** and gracefully exits ("Bob, the QA stage was already picked up by alice at 10:00; nothing to do; your work has been preserved as a parallel run at `runs/...__bob/` for reference").
3. The "loser" agent's partial work is preserved in its run folder but **doesn't advance the canonical status**.
4. If both somehow get to final-write, the merge conflict surfaces; CTO Advisor reconciles by accepting the more-complete artifact and journaling the reconciliation.

In practice: agents check `state/active.json` immediately after pulling, and the session-start hook makes this explicit ("3 requirements in flight; you have 0 to pick up").

---

## Performance + scaling

- **Repo size:** Journals + decision log accrete forever. At 50 features/month, expect ~5 MB/year of markdown + JSONL. Comfortably git-friendly indefinitely.
- **Large artifacts:** Code diffs, screenshots, perf reports — write to `artifacts/<req-id>/`. If >1 MB, [git LFS](https://git-lfs.com) is recommended.
- **Search:** `grep` over the decision log is fast at <100 MB. V2 adds an indexed query (`/digest`, `/recall <topic>`).

---

## Extensibility patterns

| Need | How |
|------|-----|
| Add an 11th agent | Create `agents/<role>.md`; add to skill matrix; update RACI; create `.engineering-os/memory/agents/<role>.journal.md` starter |
| Add a domain skill | Drop `skills/<name>/SKILL.md` (auto-discovered, no sync step); add it to `skill-mapping-matrix.md` + the owning agent's owned-skill list. See `docs/skill-authoring-guide.md`. |
| Add a new command | Create `skills/<cmd>/SKILL.md` with `disable-model-invocation: true` |
| Add a hook | Append to `hooks/hooks.json`; create the script; make executable |
| Change a quality gate | Edit `docs/quality-gates.md`; update the agent prompts that enforce the gate (enforcement is in the agents, not the hooks) |
| Add a Founder-approval channel (Slack) | Set `SLACK_WEBHOOK_URL`; extend `skills/approve/SKILL.md` to post; no plugin internals change |
| Add a region (GCC, US, EU) | Drop a new RegionAdapter section in `docs/business-context.md` and `docs/technical-context.md`; no plugin internals change |

---

## Next reads

- [memory-and-git-sync.md](memory-and-git-sync.md) — full mechanics of how shared memory survives git pull and merges.
- [../prompts/system-prompt.md](../prompts/system-prompt.md) — the shared system prompt every agent inherits.
- [../templates/](../templates/) — artifact templates the agents fill out.
- [../schemas/](../schemas/) — JSON Schemas that validate the JSON artifacts.
