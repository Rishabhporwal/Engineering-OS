---
name: defense-in-depth-validation
description: Validate at every layer data passes through — entry boundary, business logic, environment guard, audit log — AND make output safe (XSS prevention via output encoding, DOMPurify, CSP, URL allowlisting). Use after fixing a data-shaped bug, when designing a new multi-tenant endpoint that touches workspace_id or PII, when wiring a new MCP write tool, when rendering user-supplied content (campaign names, brand notes, inbox/ticket text, AI-generated headlines), when adding a rich-text editor, or any time "we trust the upstream caller" is the only defence.
---

# Defense-in-Depth Validation

When you fix a bug caused by invalid data, adding validation in one place feels sufficient. But that single check can be bypassed by different code paths, refactoring, mocks, or — in Brain — a new MCP tool wired up six months later by an agent that didn't know the rule existed.

**Core principle:** Validate at EVERY layer data passes through. Make the bug **structurally impossible**, not "we fixed the bug."

## Why this matters for Brain (the slice-3 lesson)

The `.engineering-os/lessons-learned.md` slice-3 entry calls out a real CVE-class bug Brain almost shipped: `brand_id` was being read from the request body on `/ads/spend`, allowing a cross-tenant write. The fix wasn't "validate brand_id once." The fix was four layers:

1. **Entry validation** — Zod rejects any body containing `brand_id` / `brandId` (the field doesn't belong there)
2. **JWT-derived source of truth** — `workspace_id` comes from `app_metadata.workspace_id`, set as `app.workspace_id` Postgres GUC for RLS
3. **Postgres RLS** — every row read/write checked against `app.workspace_id` regardless of what the app code thinks
4. **Audit log** — every write goes to `ai.decision_log` with `(workspace_id, actor, action, payload_hash)`

Any single layer alone would have a path around it. Together, the cross-tenant write is structurally impossible.

## Why multiple layers (the general principle)

| Single layer | Multiple layers |
|---|---|
| "We fixed the bug." | "We made the bug impossible." |
| A new code path bypasses the check. | Each path is intercepted by *some* layer. |
| A refactor removes the check silently. | Removing one layer doesn't compromise the others. |
| A test mock skips the layer. | Test mocks don't bypass Postgres RLS. |

## The four layers (Brain-flavoured)

### Layer 1 — Entry validation (Zod / Pydantic)

Reject obviously invalid input at the boundary. For Brain this is the tRPC procedure input schema (Vikram) or the FastAPI Pydantic model (Maya).

```typescript
// tRPC: /ads/spend.adjust
import { z } from 'zod';

const adsSpendInput = z.object({
  campaign_id: z.string().uuid(),
  spend_minor: z.number().int().nonnegative(),     // store as integer minor units — no float
  currency:    z.enum(['INR', 'USD']),
  // NOTE: no `workspace_id` here. Comes from JWT.
}).strict();   // .strict() REJECTS any extra fields, including `brand_id` / `brandId`

export const adsRouter = router({
  spend: router({
    adjust: protectedProcedure.input(adsSpendInput).mutation(async ({ ctx, input }) => {
      // ctx.workspaceId is set from JWT by the auth hook — never from input
      return adsService.adjust(ctx.workspaceId, input);
    }),
  }),
});
```

Brain rule: **`.strict()` on every public-facing Zod schema.** Drift between client and server should fail loudly, not silently allow injection.

### Layer 2 — Business logic validation

Even with entry validation, the service layer asserts invariants. Don't trust your own callers.

```typescript
async function adjustSpend(workspaceId: string, input: AdsSpendInput) {
  assert(isUUID(workspaceId), 'workspaceId must be UUID set from JWT');
  assert(input.spend_minor >= 0, 'spend cannot be negative');

  // Check the campaign actually belongs to this workspace (defense even though RLS will block)
  const campaign = await campaignsRepo.findById(workspaceId, input.campaign_id);
  if (!campaign) throw new TRPCError({ code: 'NOT_FOUND' });

  // ... proceed
}
```

### Layer 3 — Environment guard (the RLS / Postgres layer)

For Brain, this layer is **Postgres RLS** (Supabase). Even if Layers 1 and 2 are bypassed by a buggy migration script, RLS is the structural bottom.

```sql
ALTER TABLE ad_spend ENABLE ROW LEVEL SECURITY;

CREATE POLICY rls_ad_spend ON ad_spend
  USING (workspace_id = current_setting('app.workspace_id')::uuid);
```

For ClickHouse (Maya), there's no native RLS — instead, every query goes through `pylibs/brain_clickhouse` which rejects any query without a `workspace_id =` predicate. Same intent: structural, not policy.

For service-to-service gRPC, the metadata carries `workspace_id` AND the receiving server cross-checks against the JWT used to issue the call. Mismatches are blocked + audit-logged.

### Layer 4 — Audit / debug instrumentation

Every write goes to the Decision Log with enough context to forensic-trace.

```typescript
await db.query(
  `INSERT INTO ai.decision_log
     (workspace_id, actor, action, target, payload_hash, paradigm, model, request_id, created_at)
   VALUES (current_setting('app.workspace_id')::uuid, $1, $2, $3, $4, $5, $6, $7, NOW())`,
  [actor, 'ads.spend.adjust', input.campaign_id, hash(input), 'sql', null, ctx.requestId],
);
```

If Layers 1–3 ever fail in the future, Layer 4 is what tells you *which* request did the bad write *when* and from *which actor* — the forensic floor.

## Applying the pattern (when adding a new feature / fixing a bug)

1. **Trace the data flow** — list every layer the value passes through (request → tRPC input → service → repo → SQL → audit). For Brain this is usually 4–6 layers.
2. **Map all checkpoints** — what's the validation today at each?
3. **Add a layer where one is missing** — entry / business / environment / audit.
4. **Test each layer in isolation** — bypass Layer 1 with a hand-crafted curl; verify Layer 2 catches. Mock Layer 2; verify Layer 3 (RLS) catches.

The Stripe-grade test is: **can you write a malicious curl that bypasses Layers 1–2 and successfully writes a row in another workspace?** If the answer isn't immediate "no," you don't have defense in depth yet.

## Where Brain specifically needs all four

| Surface | L1 — entry | L2 — business | L3 — environment | L4 — audit |
|---|---|---|---|---|
| Every tRPC mutation | Zod `.strict()` schema | Service assertions | Postgres RLS | `ai.decision_log` row |
| Every MCP write tool (canon/technical-requirements.md) | Tool input schema | MCP auth scope check | RLS + scope check | Decision Log + MCP-specific audit |
| ClickHouse insert path | Avro schema (Glue Schema Registry) | brain_clickhouse query gateway | Materialized view dedup | Kafka offset + ClickHouse `INSERT_TIME` |
| Every outbound message (call/SMS/WhatsApp) | Channel payload validator | India compliance engine (calling hours, DLT, NCPR, 48h cap) | Per-vendor rate limit | `lifecycle.outbound_log` |
| Auth refresh | Zod refresh-token shape | Supabase signature check | Refresh rate limit | session.refreshed audit |
| Web cookie auth | (httpOnly cookie) | api-gateway JWT verify | JWKS (Supabase) | session events |

## Layer 5 — Output safety (XSS prevention)

The four layers above guard data going *in*. This layer guards data coming *out* — the render boundary, where stored/reflected hostile content turns into executed script. Brain renders content from many untrusted sources: campaign names ingested from Meta/Google, brand-author notes, Phase 3 inbox messages (customer DMs, email bodies), AI-generated Morning Brief headlines (treat as untrusted — prompt-injection risk), Decision Log payloads, deep-link URL params, external logo URLs from Shopify settings. React escapes text by default, but the moment you reach for `dangerouslySetInnerHTML` or build URLs from input, the net is gone.

| XSS type | Vector | Brain defense |
|---|---|---|
| **Reflected** | URL params, query strings | Server Components escape by default; URL validation via `URL()` |
| **Stored** | DB content (campaign names, notes, messages) | React escapes as text; DOMPurify when rendered as HTML |
| **DOM-based** | client JS building DOM from input | Avoid `innerHTML`/`outerHTML`/`document.write`/`eval` — use `textContent`, `createTextNode` |
| **Mutation (mXSS)** | HTML-parser quirks | DOMPurify; never roll your own sanitizer |

### React defaults + DOMPurify (the only sanitizer Brain uses)

```tsx
<td>{campaign.name}</td>                                       // SAFE — React escapes text
<a href={safeURL(campaign.link)} title={campaign.name}>…</a>   // SAFE — attributes escaped + URL validated
<div dangerouslySetInnerHTML={{ __html: brand.notes }} />      // UNSAFE — bypasses escaping
<div dangerouslySetInnerHTML={{ __html: sanitizeRichText(brand.notes) }} /> // SAFE — sanitize first
```

```typescript
// packages/ui/src/sanitize.ts — isomorphic-dompurify (Server Components AND client)
import DOMPurify from 'isomorphic-dompurify';
const RICH = { ALLOWED_TAGS: ['b','i','em','strong','a','p','br','ul','ol','li','h3','h4'],
               ALLOWED_ATTR: ['href','title','target','rel'], ALLOW_DATA_ATTR: false };
export const sanitizeRichText = (dirty: string) =>
  DOMPurify.sanitize(dirty, RICH).replace(/<a /g, '<a rel="noopener noreferrer" target="_blank" ');
// Strict — AI-generated headlines: only plain inline emphasis
export const sanitizeHeadline = (dirty: string) =>
  DOMPurify.sanitize(dirty, { ALLOWED_TAGS: ['b','em','strong'], ALLOWED_ATTR: [] });
```

Sanitize at the **render boundary**, not the storage boundary — store raw, sanitize on render so rules can change without a backfill. Always **allowlist**, never blocklist.

### URL validation

```typescript
const SAFE_PROTOCOLS = new Set(['http:','https:','mailto:','tel:']);
export function safeURL(input: string | null | undefined, fallback = '#'): string {
  if (!input) return fallback;
  try { const u = new URL(input); return SAFE_PROTOCOLS.has(u.protocol) ? u.toString() : fallback; }
  catch { return fallback; }
}
// <a href={safeURL(campaign.link)}>…</a>   <img src={safeURL(brand.logo_url, '/placeholder.png')} />
```

Blocks `javascript:`, `data:`, `vbscript:` — the most common XSS vector for "open in new tab."

### Content Security Policy (the structural defense)

Brain's Next.js BFF emits a strict CSP with a per-request nonce — **no `unsafe-inline` on `script-src`**.

```typescript
// apps/web/middleware.ts
const nonce = crypto.randomUUID().replace(/-/g, '');
const csp = [`default-src 'self'`, `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'`,
  `style-src 'self' 'unsafe-inline'`,                                   // Tailwind runtime styles
  `img-src 'self' data: https://*.cdn.shopify.com https://*.fbcdn.net`, // vendor-CDN allowlist
  `connect-src 'self' https://api.brain.pipadacapital.com wss://api.brain.pipadacapital.com`,
  `frame-ancestors 'none'`, `base-uri 'self'`, `form-action 'self'`, `upgrade-insecure-requests`].join('; ');
res.headers.set('Content-Security-Policy', csp);
res.headers.set('X-Content-Type-Options', 'nosniff');
res.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
```

`app/layout.tsx` reads the nonce from headers for the rare inline script that must run.

### Mobile (RN) — narrower but not zero

`WebView` (disable JS unless needed; strict `originWhitelist`); `Linking.openURL(input)` (run `safeURL()` first, block `javascript:`); push payload → deep link → screen (Zod-validate the payload before routing — this is Layer 1 reused for navigation).

### PR-time output-safety checklist

- [ ] Any new `dangerouslySetInnerHTML` wraps its value in `sanitizeRichText` / `sanitizeHeadline`
- [ ] Any new `<a href={…}>` from data uses `safeURL()`; any new `<img src={…}>` validates the host against the CSP `img-src` allowlist
- [ ] CSP unchanged OR change documented + Shreya-approved
- [ ] Cypress test renders a known payload (`<script>alert(1)</script>`, `<img src=x onerror=alert(1)>`) and asserts it appears literally (escaped)

## Anti-patterns

- "We can validate at the service layer; the route doesn't need Zod" — until a new tRPC route gets added by an agent that doesn't know the convention.
- "RLS is enough; we don't need application-layer checks" — RLS gives row-level. It doesn't catch logic errors like "user tried to set negative spend."
- "It's an internal service-to-service call; we trust the caller" — gRPC across services is the *exact* boundary where to NOT trust.
- "We'll just code-review carefully" — defence in depth is the structural alternative to relying on code review.

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| tRPC `.strict()` + Zod schemas | **Vikram** + **Ananya** (input shape) | canon/technical-requirements.md (input validation) |
| MCP tool schemas | **Vikram** + **Maya** | canon/technical-requirements.md |
| Postgres RLS policy review | **Shreya** + Aryan | canon/technical-requirements.md (multi-tenancy) |
| ClickHouse query gateway | **Maya** | canon/technical-requirements.md (OLAP discipline) |
| Decision Log row spec | **Aryan** + Vikram | canon/technical-requirements.md (Decision Log) |
| India compliance engine guards | **Maya** + Shreya | canon/technical-requirements.md |
| Web XSS surface + sanitizer in `packages/ui` | **Ananya** | canon/technical-requirements.md (frontend security) |
| CSP config | **Ananya** + **Shreya** | this skill (Layer 5) + `security-baseline` |
| Mobile WebView usage | **Karan** | canon/technical-requirements.md (avoid where possible) |
| PR-time XSS payload test | **Tanvi** | Cypress payload assertions |

Related Brain skills (security trio): `security-baseline` (the index + Shreya's gate — this skill is its multi-tenant + output-safety deep dive), `auth-and-access` (role-level access + `workspace_id` from JWT). Also: `idempotency-handling` (Layer 1 for retries), `mcp-protocol`, `frontend-web` (where Layer 5 lives).

## The key insight

When all four layers exist, each layer catches what the others miss. Different code paths bypass entry. Mocks bypass business logic. Edge cases need environment guards. Audit logging is what makes the structural misuse visible when (not if) someone introduces a new path that bypasses everything else. **Don't stop at one validation point.**
