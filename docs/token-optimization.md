# Token & cost optimization — the Engineering-OS program

> How we keep the *cost of building Brain* low. This is build-tooling discipline for the Engineering-OS pipeline (the 11 agents), distinct from the **Brain product's** own runtime LLM cost (the LiteLLM gateway — §B). Origin: the `chore-scaffold-monorepo` run cost **~513K tokens / ~$9.27 / ~40 min**; investigation + web research (May 2026) showed **>50% was structurally recoverable** with no loss of the safety gates that caught real bugs.

## A. Diagnosis (the scaffold case study)
| Bucket | Share | Cause |
|---|---|---|
| Re-reading the ~23K blueprint + primers on every spawn | ~35% | each agent loaded the full canon every turn |
| opus-heavy stages + uncapped thinking | 53% of spend was opus | intake/synthesis/architect/security on opus |
| The bounce (a one-character bad version pin) | ~18% | invented `betterproto v0.0.3` + buf missing → caught at QA not build → full re-run |

## B. Levers — status

### Implemented (✅ live now)
1. **Targeted-index context discipline.** `IMPLEMENTATION-BLUEPRINT.md` carries a §0 "do NOT load whole" banner + section map; the primers, TRD, and system-prompt point to it as a *targeted index* (read the §0 map → open only the one `§` you need). System-prompt token-discipline covers it + "be concise in artifacts." *Target: ~30–35%/run.*
2. **Version-pin + no-SKIP rule (#3).** Architect plan checklist: never invent a version pin (verify it exists or tell the builder to resolve+pin latest-stable). Verification principle #10: a required check that can't run (missing tool / unresolved pin) is a **blocker, not a SKIP that passes downstream**. DoD (blueprint App E) matches. *Kills the bounce class (~18%).*
3. **Lane calibration (#7, Founder-ratified 2026-05-24).** Foundational scaffolding that touches structural surfaces (`schema-proto`/`multi-tenancy`/`mcp-tools`) *only* by creating empty homes/config — no live contract, consumers, business logic, migration-on-existing-data, runtime, or money/PII/outbound/connector/compliance surface — is `standard`, not high-stakes. **Architect + Security + QA + final all still run** (they catch the real defects); only the **persona escalation + mutation-test mandate** drop. On any doubt → high-stakes. (`docs/feature-tiering.md` + `agents/cto-advisor.md`.) *Saves ~persona+synthesis (~100K) on scaffold-class.*
4. **`rtk` command-output compression.** Build/QA/security/devops stages prefix noisy dev commands with `rtk` (`rtk pnpm install`, `rtk buf generate`, `rtk pnpm test`, `rtk turbo build`) → 60–90% fewer output tokens, same signal. `brew install rtk` (v0.41.0). Wired in the system-prompt token-discipline section. MIT, single Rust binary, Claude-Code-native.
5. **Toolchain-present-before-build** (env): `buf` + Node 24 installed so codegen fails at *build* (Stage 3), not QA — no full bounce.
6. **Token-breakdown logging (2026-05-24).** `usage.jsonl` now logs `input_tokens` / `output_tokens` / `cache_read_tokens` / `cache_creation_tokens` alongside `total_tokens` (orchestrator + `/approve`). This separates **context-load (input+cache)** — what the targeted-index / `rtk` / concise-artifact levers cut — from **reasoning (output)**, and exposes cache-hit rate. *Without it, per-stage savings were invisible on non-identical tasks (the confound that made the scaffold↔spike comparison meaningless).* This is the measurement fix.
7. **Spike / planning lane depth-modifier (2026-05-24, Founder-ratified).** A no-code spike (design/architecture artifact, `no-prod-code` guardrail) keeps its risk lane but **right-sizes review depth**: Security + QA vet the *design* (soundness + compliance/PII/residency/tenancy/money decisions + plan testability) and mark code-level machinery (vuln scans, real-network smoke, contract/mutation tests) **N/A — no code exists** (declared, not skipped). Targets the ~40%-of-spike that went to full-depth review of a document (the Child-0 spike: 347K of 860K on review). Full depth returns on build slices. (`feature-tiering.md` + `security-reviewer.md` + `qa-agent.md`.)
8. **Persona model-tiering (2026-05-24).** Rohan tags each persona `:haiku` (bounded/checklist) or `:sonnet` (reasoning-heavy); the orchestrator spawns at that model (Haiku ~6× cheaper). Most single-dimension personas are bounded → Haiku; Sonnet reserved for genuine depth. (`cto-advisor.md` + `requirement` orchestrator.) *Origin: the Child-0 spike ran 2 personas on Sonnet (~123K) where the scaffold's bounded persona ran fine on Haiku (59K).*

### Scheduled (gated on a trigger — honest: not actionable yet)
6. **Graphify** (knowledge-graph codebase navigation). **Trigger: when the Brain codebase has real substance** (several implemented services, not the current empty scaffold). Then pilot: build a graph of `apps/`+`packages/`+`pylibs/`, have the architect/build/security/QA stages query subgraphs instead of exploratory file-reads; **measure graph-build cost vs per-run read savings before adopting**; gate on maturity (it's pre-1.0). *Not for the canon (right-sizing + the index already cover that), and worthless on an empty scaffold.* `uv tool install graphifyy`.
7. **Prompt caching of the stable canon block.** Anthropic `cache_control` gives ~90% off cached reads. Claude Code auto-caches system prompt/tools; the gap is the per-task files agents Read fresh — which lever #1 already minimizes. Revisit if the harness exposes more control.

### Brain *product* runtime (separate from build cost — verify when built)
8. **LiteLLM gateway caching.** When `intelligence-service` + the gateway are built, **prompt caching + Redis/Qdrant semantic caching MUST be enabled** (canon already specifies "semantic cache (Redis)" on the gateway; blueprint §5.8). It cuts the *product's* runtime LLM bill, not the build bill. This is a gateway-build DoD item — there is nothing to verify until the gateway exists.

## C. Measurement plan (prove it, don't assume it)
**Lesson learned (the hard way):** raw `total_tokens` across *non-identical* tasks proves nothing — the scaffold (513K, shipped code) vs the migration spike (860K, no code) weren't comparable, so the per-stage context win was unmeasurable. **Lever 6 (token-breakdown logging) fixes this:** with `input/cache` separated from `output`, the context-load a stage carries is **directly visible on any task** — no identical-task A/B needed. From the next requirement run on the updated plugin:
- **Per-stage context-load** = `input_tokens + cache_creation_tokens` (and how much rides cache via `cache_read_tokens`) — this is what the targeted-index / `rtk` / concise levers should shrink; reasoning (`output_tokens`) scales with task difficulty and is *expected* to vary.
- **Cache-hit rate** = `cache_read / (cache_read + cache_creation + input)` — higher = more context served from cache.
- **Structural wins** stay observable directly: a challenge-back/decompose that skips stages; a spike whose Security/QA ran focused depth; persona rows logged at Haiku not Sonnet.
Watch the dashboard Tokens tab + `/watch`; re-tune any lever that underperforms.

## Sources
[RTK (rtk-ai/rtk)](https://github.com/rtk-ai/rtk) · [Anthropic prompt caching 2026](https://technspire.com/en/blog/prompt-caching-2026-real-cost-wins) · [Claude Code token optimization](https://buildtolaunch.substack.com/p/claude-code-token-optimization) · [RCR-Router (arXiv)](https://arxiv.org/pdf/2508.04903) · [AgentDropout (arXiv)](https://arxiv.org/pdf/2503.18891) · [LLMLingua](https://www.llmlingua.com/) · [LiteLLM caching](https://docs.litellm.ai/docs/proxy/caching) · [Graphify](https://github.com/safishamsi/graphify)
