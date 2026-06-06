# INVARIANTS — the non-negotiables (TEMPLATE)

> Copy to `.engineering-os/knowledge-base/INVARIANTS.md`. The rules that must **always** hold for this
> product — the "never" list. A change that would break an invariant is a Foundation amendment, not a
> normal requirement. The Security/QA/Final gates enforce these.

> The OS already enforces its universal Iron Laws (`engineering-os-blueprint/00-first-principles.md §2`).
> List here only the **product-specific** invariants on top of those. Examples of the *kind* of rule
> (replace with yours):

| # | Invariant (must always hold) | Enforced by |
|---|---|---|
| 1 | `<e.g. every row/event/log carries the tenant key>` | data layer + review |
| 2 | `<e.g. money is integer minor units + currency_code; never floats>` | review + tests |
| 3 | `<e.g. all calculations come from the single metric registry; models never invent numbers>` | parity gate |
| 4 | `<e.g. every mutating endpoint and external side-effect is idempotent>` | review + tests |
| 5 | `<e.g. one cross-cutting concern is built once, consumed N times>` | architecture review |
| … | `<add yours>` | |

## Anti-patterns (product-specific "do not")
- `<e.g. no offset pagination on growable lists>`
- `<e.g. no synchronous call into context X from context Y>`
- `<add yours>`
