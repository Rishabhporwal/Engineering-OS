# COMPLIANCE — the regulatory regime (TEMPLATE)

> Copy to `.engineering-os/knowledge-base/COMPLIANCE.md`. The OS carries **no** regulatory knowledge —
> it supplies the enforcement machinery; you declare the regime. If no regime applies, say so
> explicitly. See `engineering-os-blueprint/08-technical-governance.md §5`.

## Applicable regime
`<List the regulations/standards that apply: data-protection laws, residency requirements, industry
standards, channel/communication rules, certifications. If NONE apply, write: "No external regulatory
regime applies." — do not leave blank.>`

## Controls (each becomes an enforced rule + a Security VETO surface)
| Control | Requirement | How enforced | Evidence (for audits) |
|---|---|---|---|
| `<e.g. data residency>` | `<data stays in region X>` | `<infra config + review>` | `<gate record>` |
| `<e.g. consent>` | `<…>` | `<…>` | `<…>` |
| `<e.g. retention/deletion>` | `<…>` | `<…>` | `<…>` |
| `<e.g. PII minimization>` | `<…>` | `<…>` | `<…>` |

## Audit-trail integrity
`<If a regime requires tamper-evidence: describe the immutable, append-only, integrity-verifiable
record (hash-chaining / write-once storage). Otherwise: "not required.">`

## Evidence-as-you-build
`<Where attestation is required, controls map to gates and the gate's record IS the evidence — not
reconstructed before an audit.>`
