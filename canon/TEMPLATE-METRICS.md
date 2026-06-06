# METRICS — the single-source registry (TEMPLATE)

> Copy to `.engineering-os/knowledge-base/METRICS.md`. The **one** place every metric/calculation is
> defined. If a value is computed in more than one runtime/language, the definitions must be **identical**
> and parity is checked against an **independent oracle** (Iron Law: deterministic truth). Models never
> invent these numbers — they classify/explain/synthesize.

| Metric / calculation | Definition (the formula / rule) | Unit | Owner runtime(s) | Parity check |
|---|---|---|---|---|
| `<name>` | `<exact formula or rule>` | `<unit; money = minor units + currency_code>` | `<e.g. backend + client>` | `<test that asserts cross-runtime equality vs an independent fixture>` |
| … | | | | |

## Rules
- **One definition, many consumers.** No metric is redefined in a dashboard, a report, or a model prompt.
- **Money:** integer **minor units** + a `currency_code`; never floats; never bare numbers.
- **Quality-gated:** a metric whose inputs fail the data-quality gate is marked *estimated/untrusted*
  until the gate passes — never presented as authoritative.
