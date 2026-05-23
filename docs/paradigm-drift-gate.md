# Paradigm-Drift Gate (Point D)

> Your cost discipline (`cost-routing-paradigms`: SQL > ML > small_llm > frontier_llm, ratio 1:100:1,000:10,000) is the engineering invariant behind GMV-% pricing. (Paradigms 3 & 4 are model-agnostic, gateway-routed policy tiers; the legacy `haiku`/`sonnet` decorator spellings still resolve to small_llm/frontier_llm.) Today it's enforced by **convention** (`@paradigm` decorator) + **audit** (Rohan at Stage 1/6). This makes it **mechanical**: a CI gate that fails the build on drift.

It's a fast **heuristic** signal, not a proof — line-based, not full AST. It catches the common, expensive mistakes cheaply.

---

## What it flags

| Class | Meaning |
|---|---|
| **MISSING** | An LLM call (Anthropic SDK / `claude-*` model) with no `@paradigm` marker within 40 lines above it. Every LLM path must declare its paradigm. |
| **NON_LLM** | An LLM call inside a path declared `sql` or `ml` — those paradigms must not call an LLM at all. |
| **ESCALATED** | A `sonnet`/`opus` (frontier-class) model used under a path declared `small_llm` — silent cost escalation beyond the declared tier. |

Markers recognised (Python decorator or TS/JS comment):
`@paradigm("frontier_llm")` · `@paradigm(Paradigm.SMALL_LLM)` · `// @paradigm: sql` · `# @paradigm small_llm` (legacy `haiku`/`sonnet` still accepted)

---

## Run

```sh
uv run tools/paradigm_check.py            # whole repo
uv run tools/paradigm_check.py --changed  # only files changed vs origin/HEAD (CI default)
```

Exit code `1` on any violation → fails CI.

Verified against a fixture: catches NON_LLM, ESCALATED, and MISSING; passes a clean `frontier_llm`-tier path (sonnet model) and a pure-`sql` path.

---

## Wire into CI (Brain product repo)

```yaml
# .github/workflows/ci.yml — add a job
  paradigm-drift:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }          # need history for --changed
      - uses: astral-sh/setup-uv@v5
      - run: uv run path/to/plugin/tools/paradigm_check.py --changed
        env:
          PARADIGM_BASE_REF: origin/${{ github.base_ref || 'main' }}
```

This complements — does not replace — the build's existing `@paradigm` decorator requirement and Rohan's Stage 6 audit. Three layers: decorator (write-time), this gate (CI), Rohan (review).

---

## Limits (be honest)

- **Heuristic, not AST.** Function/block association is line-window based; an LLM call >40 lines below its decorator could false-negative. Tune `WINDOW` if your code style needs it.
- **Regex model detection.** It keys on Anthropic SDK call shapes + `claude-*`/tier strings. A call wrapped behind a custom helper that hides the model string won't be seen — keep the model string at the call site (you should anyway, for grep-ability).
- **Verification boundary.** Verified in isolation on a fixture; run it once on the real Brain repo and tune patterns to your actual call sites before making it a blocking gate.
