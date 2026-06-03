# Changelog — Brain Engineering OS

## v1.1.0 — Enforcement hardening (the 10-persona review)

A 10-expert adversarial review of the v1.0.0 clean-room rebuild found one systemic
flaw: **the design was excellent but the enforcement was prose** — nearly every
load-bearing guarantee (secrets, telemetry, state integrity, VETO, verification-validity,
lane classification, the spawn cap) depended on the model *remembering*. This release
moves every one of them **onto a hook, schema, or tool that fires regardless of model
behavior**, and makes the orchestrator crash-recoverable.

### Security
- **O1 actually fixed.** `hooks/on-secret-guard.sh` (PreToolUse Write|Edit) **blocks**
  any write containing a live secret value *before disk* — covering the six classes that
  actually leaked (`GOCSPX-`, `shpss_`, `shppat_`, `EAA…`, connection-string passwords).
  `tools/secret_scan.py` gates the `.engineering-os/` commit; `.gitleaks.toml` for the team.
  (v1.0.0's "fix" caught none of these and only sanitized its own journal line.)
- **Non-LLM VETO** (`tools/gate_check.py`): structurally refuses to advance to the Founder
  gate / deploy on any unresolved CRITICAL/HIGH or non-PASS review — fail-closed. A model
  can no longer route past a VETO; a Founder "approve" can't ship past an open CRITICAL.
- **Build-team prompt-injection defense:** the team's reads (legacy code, web, requirement
  text) are now treated as untrusted data; the deterministic gates hold regardless of what
  an injection makes an agent *say*.

### Reliability & telemetry
- **Hook-enforced heartbeat** (`hooks/on-subagent-usage.sh` + `tools/heartbeat_check.py`):
  every spawn return is recorded deterministically; `/watch` surfaces a STALE banner and
  reconciles spawns-vs-usage — the O13/O14 silent-stops are now *detectable*, not invisible.
- **Orchestrator is now crash-recoverable** (`tools/orchestrator_cursor.py`): its in-flight
  plan (outstanding spawns, count, last route) is persisted; `/resume` rebuilds the scheduler.
- **Orchestrator is the sole writer of `active.json`** (`tools/state_update.py`, atomic
  `os.replace`): kills the parallel-builder lost-update race; recovers from a corrupt live file.

### Quality
- **Verification-validity (O11) is now falsifiable:** `negative_control[]` schema field +
  `tools/validity_check.py` (catches BYPASSRLS/superuser/tautology; rejects an empty control
  on high-stakes paths). The #1 recurring bounce has a mechanical gate.
- **Test suite decoupled from delta scope:** every bounce-fix re-runs the full prior-passing
  suite (cheap CI) so `regression_auto_block` can actually fire.
- **Learning loop closed:** adopted `durable-rules/INDEX.md` is read at session start.
- **CI self-gate** (`.github/workflows/eos-self-gate.yml`): pipeline_doctor, secret_scan,
  validity_check, cache_lint, knowledge_lint, agent-frontmatter — the OS gates itself.

### Cost
- **cto-advisor split** → `cto-advisor` (Sonnet intake) + `final-reviewer` (Opus final): the
  #1 unrealized lever. **Projected −46% on real telemetry** (`tools/ab_project.py`, surfaced
  in the dashboard's "v2-tier headroom" KPI).
- **Deterministic lane classifier** (`tools/classify_lane.py`): a model miss can no longer
  strip Security off a compliance change.
- **Prompt-caching discipline:** cache-stable-first spawn prompts + `tools/cache_lint.py`.
- **Lane-aware pause-and-confirm spawn cap** (was a flat-20 footgun).
- **Experimental `lean` lane** + `docs/lean-vs-full-ab.md` (the strategic A/B, still pending a live run).

### DX & knowledge
- `/approve` renders a **cost/risk decision card** (was a rubber stamp).
- Onboarding fixed: 6 dead doc links, `/eos init`→`/eos-init`, the restart-to-apply rule, the
  recovery commands (`/decide`, `/resume`, `/handoff`).
- Knowledge drift fixed + `tools/knowledge_lint.py` self-enforces the single-source claim.
- Skill-loading prose made mechanism-true (no more "auto-discovered" fiction).

### Still open (needs a live run — operator-side)
1. Confirm the −46% binds live (dashboard headroom → ~0 after restart).
2. Settle lean-vs-full (`/requirement` vs `/requirement --lean` on 2 trivial reqs).
3. **Then: run → observe → fix.** The next real problem from a real run is worth more than
   any speculative feature. (Deliberately NOT built: Batch API — doesn't apply to interactive
   orchestration; eval-gated cascade — marginal until a run shows final-review cost is a problem.)

---

## v1.0.0 — Clean-room rebuild (promoted from v0.26.0)

Leaner runtime, same vision. Control-flow extracted from the Opus prompt into `pipeline/`;
delta re-review; model tiering; lazy skill loading; single-sourced canon (`canon/INDEX.md`
replaced the 924-line BLUEPRINT); enforced telemetry foundation. Static footprint cuts:
system-prompt 300→87 ln, always-on skill descriptions ~10k→2.6k tokens, 99→88 skills.
v1 recoverable via tag `v1-0.26.0-archive`.
</content>
