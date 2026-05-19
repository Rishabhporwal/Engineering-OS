---
name: xss-prevention
description: XSS prevention for Brain's Next.js dashboard + RN mobile — output encoding, DOMPurify for any dangerouslySetInnerHTML, CSP with nonce, URL allowlisting, safe React patterns. Use when rendering user-supplied content (campaign names, brand notes, ticket text from Phase 3 inbox, customer support replies), when adding a rich-text editor, when an audit flags a CSP gap.
---

# XSS Prevention

Brain renders content from many sources — campaign names ingested from Meta/Google, brand-author notes, Phase 3 inbox messages from customers, AI-generated headlines, Decision Log payloads. React escapes text content by default, but the moment you reach for `dangerouslySetInnerHTML` or build URLs from user input, the safety net is gone.

## Why this matters for Brain

| Surface | XSS risk |
|---|---|
| Campaign name rendered in CM Waterfall row (`{campaign.name}`) | Vendor-supplied; assume hostile until validated |
| Brand notes / Decision Log payload preview | Brand-author content; could be intentional XSS in agency context |
| Phase 3 inbox messages (customer DMs, email bodies) | Untrusted by default |
| AI-generated Morning Brief headline | Sonnet output; treat as untrusted (prompt injection risk — see `defense-in-depth-validation`) |
| Deep links into web (URL params) | Reflected XSS surface |
| External logo / image URLs (from Shopify settings) | URL validation matters; `<img src>` is not auto-safe |

## XSS attack types

| Type | Vector | Brain defense |
|---|---|---|
| **Reflected** | URL params, query strings | Server Components escape by default; URL validation via `URL()` constructor |
| **Stored** | DB content (campaign names, notes, messages) | React escapes when rendered as text; DOMPurify when rendered as HTML |
| **DOM-based** | Client-side JS that builds DOM from input | Avoid `innerHTML`, `outerHTML`, `document.write`, `eval` |
| **Mutation** | HTML parser quirks (mXSS) | Use DOMPurify; don't roll your own sanitizer |

## React + Next.js — defaults are mostly safe

```tsx
// SAFE — React escapes the campaign name automatically
<td>{campaign.name}</td>

// SAFE — attributes are escaped
<a href={String(campaign.link)} title={campaign.name}>...</a>

// UNSAFE — bypasses React's escaping
<div dangerouslySetInnerHTML={{ __html: brand.notes }} />

// SAFE — sanitize first
<div dangerouslySetInnerHTML={{ __html: sanitize(brand.notes) }} />
```

## DOMPurify — the only sanitizer Brain uses

```bash
pnpm add isomorphic-dompurify   # works in Server Components AND client
```

```typescript
// packages/ui/src/sanitize.ts (or wherever Brain's shared lib lives)
import DOMPurify from 'isomorphic-dompurify';

const RICH_TEXT_CONFIG = {
  ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'br', 'ul', 'ol', 'li', 'h3', 'h4'],
  ALLOWED_ATTR: ['href', 'title', 'target', 'rel'],
  ALLOW_DATA_ATTR: false,
  // Force safe link behavior on every <a>
  ADD_ATTR: ['target', 'rel'],
};

export function sanitizeRichText(dirty: string): string {
  const clean = DOMPurify.sanitize(dirty, RICH_TEXT_CONFIG);
  // Force every <a> to rel="noopener noreferrer" target="_blank"
  return clean.replace(/<a /g, '<a rel="noopener noreferrer" target="_blank" ');
}

// Strict (only plain inline emphasis) — used for AI-generated headlines
const HEADLINE_CONFIG = { ALLOWED_TAGS: ['b', 'em', 'strong'], ALLOWED_ATTR: [] };
export function sanitizeHeadline(dirty: string) {
  return DOMPurify.sanitize(dirty, HEADLINE_CONFIG);
}
```

Use the sanitizer at the **render boundary**, not at the storage boundary. Storing sanitized HTML is fine; storing the raw HTML and sanitizing on render keeps the option open to change sanitization rules later without a backfill.

## URL validation

```typescript
// packages/ui/src/safe-url.ts
const SAFE_PROTOCOLS = new Set(['http:', 'https:', 'mailto:', 'tel:']);

export function safeURL(input: string | null | undefined, fallback = '#'): string {
  if (!input) return fallback;
  try {
    const u = new URL(input);
    return SAFE_PROTOCOLS.has(u.protocol) ? u.toString() : fallback;
  } catch {
    return fallback;
  }
}
```

```tsx
// USE in every place a URL comes from data
<a href={safeURL(campaign.link)}>{campaign.name}</a>
<img src={safeURL(brand.logo_url, '/placeholder.png')} alt={brand.name} />
```

`javascript:`, `data:`, and `vbscript:` are all blocked — the most common XSS vector for "open in new tab" features.

## Content Security Policy (Brain canonical)

Brain's Next.js BFF emits a strict CSP with a per-request nonce. No `unsafe-inline` on `script-src`.

```typescript
// apps/web/middleware.ts (Next.js 14 middleware)
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(req: NextRequest) {
  const nonce = crypto.randomUUID().replace(/-/g, '');
  const csp = [
    `default-src 'self'`,
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'`,
    `style-src 'self' 'unsafe-inline'`,                      // Tailwind needs unsafe-inline for runtime styles
    `img-src 'self' data: https://*.cdn.shopify.com https://*.fbcdn.net`,  // Allowlist for known vendor CDNs
    `connect-src 'self' https://api.brain.pipadacapital.com wss://api.brain.pipadacapital.com`,
    `font-src 'self' data:`,
    `frame-ancestors 'none'`,
    `base-uri 'self'`,
    `form-action 'self'`,
    `upgrade-insecure-requests`,
  ].join('; ');

  const res = NextResponse.next();
  res.headers.set('Content-Security-Policy', csp);
  res.headers.set('X-Nonce', nonce);    // exposed to layout.tsx for inline scripts that need it
  res.headers.set('X-Content-Type-Options', 'nosniff');
  res.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  return res;
}
```

The nonce is read by `app/layout.tsx` from headers and applied to any inline script that must run (rare — most can be moved to external scripts).

## Safe DOM APIs (when you must touch the DOM directly)

```javascript
// DANGEROUS — avoid these
element.innerHTML  = userInput;     // XSS risk
element.outerHTML  = userInput;     // XSS risk
document.write(userInput);          // XSS risk
eval(userInput);                    // Code injection

// SAFE
element.textContent = userInput;                 // Escaped automatically
element.setAttribute('data-id', String(id));    // Safe for attributes
element.appendChild(document.createTextNode(userInput));  // Safe text node
```

In React components, the answer is almost never to reach for the DOM directly. If you find yourself doing it, the right fix is usually a controlled component or a portal.

## Mobile (RN) — XSS surface is narrower but not zero

React Native doesn't render HTML by default; the XSS surface is:
- `WebView` components — disable JS unless absolutely needed; if needed, use `originWhitelist` strictly
- `Linking.openURL(input)` — validate with `safeURL()` first; block `javascript:` schemes
- Push notification payload → deep link → screen — Zod-validate the payload before routing

## Best Practices

**✅ DO:**
- Default to text rendering (`{value}`) — React escapes for you
- Sanitize before rendering rich HTML (`DOMPurify` with allowlist, NEVER blocklist)
- Implement strict CSP with nonce on every response
- Validate URLs with protocol allowlist (`safeURL`)
- Use `<Image>` from Next.js (handles `data:`/`javascript:` safely)
- Test with stored XSS payloads in CI (`<script>alert(1)</script>`, `<img src=x onerror=alert(1)>`)
- Treat AI-generated output as untrusted (prompt injection)

**❌ DON'T:**
- Use `dangerouslySetInnerHTML` without `sanitize()` wrapping the value
- Trust URLs from any vendor connector (campaign URLs from Meta/Google)
- Use a blocklist of "bad strings" — always allowlist
- Disable CSP "for development" — it's the structural defense
- Rely solely on client-side validation — server must validate too (`defense-in-depth-validation`)
- Roll your own HTML sanitizer

## Security checklist (PR-time)

- [ ] Any new `dangerouslySetInnerHTML` wraps its value in `sanitizeRichText` or `sanitizeHeadline`
- [ ] Any new `<a href={...}>` from data uses `safeURL()`
- [ ] Any new `<img src={...}>` from data validates the host against the CSP `img-src` allowlist
- [ ] CSP unchanged OR change documented + Shreya-approved
- [ ] Cypress test renders a known XSS payload and asserts it's escaped (e.g., `<script>alert(1)</script>` appears literally)

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| Web XSS surface | **Ananya** | canon/BRAIN_TECHNICAL.md (frontend security) |
| CSP config | **Ananya** + **Shreya** | this skill + `security-baseline` |
| Sanitizer in `packages/ui` | **Ananya** | shared lib |
| Mobile WebView usage | **Karan** | canon/BRAIN_TECHNICAL.md (avoid where possible) |
| PR-time XSS test | **Tanvi** | Cypress payload assertions |

Related Brain skills: `security-baseline` (broader OWASP), `defense-in-depth-validation` (treat AI output as untrusted), `session-management` (httpOnly cookies — separate concern), `frontend-web`.
