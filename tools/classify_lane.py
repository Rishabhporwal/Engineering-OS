# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""classify_lane — deterministic trigger-surface scan (fixes the lane misclassification risk).

The lane decides which gates run. Letting the cheapest model classify the lane over
prose risks a confident miss that strips architect+security+final off a
compliance/auth change (the most expensive class of error). This tool makes the
trigger-surface scan DETERMINISTIC: keyword/path patterns over the requirement text
(+ the diff, if available). The model may ADD a surface it spots; it may NEVER silently
REMOVE one this tool flagged. ≥1 surface ⇒ high_stakes.

The patterns below are GENERIC, PRODUCT-CONFIGURABLE EXAMPLES. A product binds these
to its own surfaces via its Canon (TRIGGER-SURFACES.md / COMPLIANCE.md) — e.g. the
specific connector names, channel types, or regulatory-regime keywords. De-braining
the examples does NOT change the function's contract: the surface KEYS (auth,
multi_tenancy, money, compliance, …) are the cross-file interface the pipeline and
orchestrator depend on, and are preserved exactly.

Usage:
  uv run classify_lane.py --text "requirement text…" [--diff <file-with-staged-diff>]

Prints JSON: { feature_class, trigger_surfaces_touched, rationale }.
Exit 0 always (it's an advisor to the orchestrator, not a gate); the orchestrator
records the result and the intake agent validates it.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

# surface -> (text patterns, path/code patterns). Conservative: err toward flagging.
# These are GENERIC, PRODUCT-CONFIGURABLE EXAMPLES — bind your own surface keywords in the
# Canon (TRIGGER-SURFACES.md / COMPLIANCE.md). The KEYS are the cross-file contract; the
# patterns are illustrative and meant to be extended per product.
SURFACES = {
    "auth":            ([r"\bauth\b", r"login", r"session", r"jwt", r"\brole\b", r"permission", r"rbac", r"sso", r"oauth"],
                        [r"requireRole", r"requireTenantMember", r"auth\.", r"/auth/"]),
    "multi_tenancy":   ([r"tenant_id", r"\btenant", r"\brls\b", r"row.level.security", r"cross.tenant"],
                        [r"tenant_id", r"RowLevelSecurity", r"current_setting\('app"]),
    "mcp_tools":       ([r"\bmcp\b", r"mcp tool", r"tool surface"], [r"@mcp_tool", r"mcp_server", r"protos/.*mcp"]),
    # CONNECTORS = any external-system integration / vendor connector. Add your product's
    # specific connector vendor names here (the generic markers below catch the rest).
    "connectors":      ([r"connector", r"integration", r"\bvendor\b", r"third.?party", r"webhook", r"ingest"],
                        [r"connector", r"ingestion", r"/webhooks?/"]),
    # OUTBOUND_CHANNEL = any outbound contact/messaging channel (call / message / email /
    # push / audience). Bind the product's concrete channels in the Canon.
    "outbound_channel":([r"\bsms\b", r"\bcall\b", r"\bemail\b", r"\bmessage\b", r"outreach", r"campaign send", r"\baudience\b", r"push notification"],
                        [r"channel.router", r"messaging", r"notification.service"]),
    "pii":             ([r"\bpii\b", r"personal data", r"phone", r"\bemail\b", r"address", r"customer data", r"national.?id"],
                        [r"email_hash", r"phone_hash", r"customers?\b"]),
    "schema_proto":    ([r"migration", r"schema change", r"new table", r"add column", r"\.proto\b", r"new field"],
                        [r"\.proto$", r"migrations?/", r"migrations?/.*\.sql", r"CREATE TABLE", r"ALTER TABLE"]),
    # MONEY = moving/computing money, NOT merely displaying a money-derived metric. Triggering
    # on bare metric NAMES would force-route read-only display cards to high_stakes AND let a
    # money-formatting refactor slip. So: text patterns are money-MUTATION verbs; the real
    # money-math signal is a `*_minor`/billing path in the DIFF (caught at the post-build
    # recheck). A card that merely *shows* a financial metric matches neither → standard/express.
    "money":           ([r"billing", r"invoice", r"\brefund", r"settlement", r"payment", r"\bcharge\b",
                         r"charge[sd]?\b", r"\bfee\b", r"pricing", r"minor.?units", r"\bmeter\b",
                         r"(compute|calculate|recompute|meter)\s+\w*\s*(revenue|amount|margin|fee|price)"],
                        [r"_minor\b", r"billing\.", r"\bmeter\b", r"currency_code", r"clamp\("]),
    # METRIC_ENGINE = changing how a number is COMPUTED (formula/parity/registry) — high stakes
    # because it shifts numbers product-wide. NOT a metric NAME (a display card uses an existing
    # one). "parity" = cross-runtime metric parity from the single-source metric registry.
    "metric_engine":   ([r"metric registry", r"formula book", r"\bparity\b", r"metric definition",
                         r"new metric", r"recompute", r"metric.?lib", r"cross.?runtime parity"],
                        [r"metric.?registry", r"lib.?metrics", r"metric.?engine"]),
    # COMPLIANCE = anything the product's COMPLIANCE.md regime governs (data-protection,
    # residency, retention, consent, channel/contact rules). The keywords below are GENERIC
    # regime markers — bind your product's specific statutes/rules in COMPLIANCE.md.
    "compliance":      ([r"data.?protection", r"privacy law", r"\bconsent\b", r"contact.?hours", r"calling.?window",
                         r"recording", r"opt.?in", r"retention", r"residency", r"in.?region", r"regulat"],
                        [r"consent", r"compliance", r"residency"]),
}


def scan(text: str, diff: str) -> list[str]:
    blob = (text + "\n" + diff).lower()
    hits = []
    for surface, (text_pats, path_pats) in SURFACES.items():
        for pat in text_pats + path_pats:
            if re.search(pat, blob, re.I):
                hits.append(surface)
                break
    return sorted(set(hits))


def main() -> int:
    ap = argparse.ArgumentParser(prog="classify_lane")
    ap.add_argument("--text", required=True)
    ap.add_argument("--diff", help="path to a file containing the staged diff (optional). At the "
                    "build→review transition, pass the ACTUAL staged diff — surfaces a 'trivial' "
                    "requirement text missed but the code touched are caught here (the post-build recheck).")
    ap.add_argument("--prior", help="comma-list of surfaces recorded at intake. If set, the tool reports "
                    "new_surfaces (in the diff but NOT in --prior) and escalate=true when any appear — "
                    "this is the express/standard VOID-and-restart signal.")
    args = ap.parse_args()
    diff = ""
    if args.diff and Path(args.diff).exists():
        diff = Path(args.diff).read_text(errors="ignore")
    elif args.diff:                                  # allow inline diff text too
        diff = args.diff

    surfaces = scan(args.text, diff)
    out = {
        "feature_class": "high_stakes" if surfaces else "standard_or_express",
        "trigger_surfaces_touched": surfaces,
        "rationale": (f"trigger surface(s): {', '.join(surfaces)}" if surfaces
                      else "no trigger surface detected (intake agent picks express vs standard on triviality)"),
        "rule": "deterministic scan — may ADD a surface, never silently REMOVE one; >=1 surface => high_stakes (conservative).",
    }
    if args.prior is not None:
        prior = {s.strip() for s in args.prior.split(",") if s.strip()}
        new_surfaces = [s for s in surfaces if s not in prior]
        out["prior_surfaces"] = sorted(prior)
        out["new_surfaces"] = new_surfaces
        out["escalate"] = bool(new_surfaces)
        out["recheck"] = (
            f"POST-BUILD RECHECK: the diff revealed {new_surfaces} that the requirement text missed — "
            f"VOID the current lane and RESTART as high_stakes (reinstate architect/security/final)."
            if new_surfaces else
            "POST-BUILD RECHECK: the diff introduced no surface beyond the intake classification — lane stands."
        )
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
