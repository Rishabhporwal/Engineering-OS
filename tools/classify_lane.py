# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""classify_lane — deterministic trigger-surface scan (fixes the lane misclassification risk).

The lane decides which gates run. In v2 it was a judgment the cheapest model (Haiku)
made over prose — a confident miss could strip architect+security+final off a
compliance/auth change (the most expensive class of error). This tool makes the
trigger-surface scan DETERMINISTIC: keyword/path patterns over the requirement text
(+ the diff, if available). The LLM may ADD a surface it spots; it may NEVER silently
REMOVE one this tool flagged. ≥1 surface ⇒ high_stakes.

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
SURFACES = {
    "auth":            ([r"\bauth\b", r"login", r"session", r"jwt", r"\brole\b", r"permission", r"rbac", r"sso", r"oauth"],
                        [r"requireRole", r"requireWorkspaceMember", r"auth\.", r"/auth/"]),
    "multi_tenancy":   ([r"workspace_id", r"\btenant", r"\brls\b", r"row.level.security", r"cross.brand"],
                        [r"workspace_id", r"RowLevelSecurity", r"current_setting\('app"]),
    "mcp_tools":       ([r"\bmcp\b", r"mcp tool", r"tool surface"], [r"@mcp_tool", r"mcp_server", r"protos/.*mcp"]),
    "connectors":      ([r"shopify", r"meta ads", r"google ads", r"shiprocket", r"klaviyo", r"tiktok", r"\bsnap\b", r"connector", r"webhook", r"ingest"],
                        [r"connector", r"ingestion", r"/webhooks?/"]),
    "outbound_channel":([r"whatsapp", r"\bsms\b", r"\bcall\b", r"\bemail\b", r"outreach", r"campaign send", r"ad.audience", r"push notification"],
                        [r"channel.router", r"lifecycle", r"twilio", r"bolna", r"vapi"]),
    "pii":             ([r"\bpii\b", r"personal data", r"phone", r"\bemail\b", r"address", r"customer data", r"aadhaar"],
                        [r"email_hash", r"phone_hash", r"customers?\b"]),
    "schema_proto":    ([r"migration", r"schema change", r"new table", r"add column", r"\.proto\b", r"new field"],
                        [r"\.proto$", r"migrations?/", r"prisma/.*\.sql", r"CREATE TABLE", r"ALTER TABLE"]),
    # MONEY = moving/computing money, NOT merely displaying a money metric. War-game: triggering
    # on bare metric NAMES (cm2/gmv) force-routed read-only dashboard cards to high_stakes (Sim 1)
    # AND a formatMoney refactor slipped (Sim 5). So: text patterns are money-MUTATION verbs;
    # the real money-math signal is a `*_minor`/billing path in the DIFF (caught at the post-build
    # recheck). A card that merely *shows* CM2 matches neither → standard/express.
    "money":           ([r"billing", r"invoice", r"\brefund", r"settlement", r"payment", r"\bcharge\b",
                         r"charge[sd]?\b", r"\bfee\b", r"pricing", r"minor.?units", r"gmv.?meter",
                         r"(compute|calculate|recompute|meter)\s+\w*\s*(revenue|gmv|cm2|margin|fee)"],
                        [r"_minor\b", r"billing\.", r"gmv_meter", r"currency_code", r"clamp\("]),
    # METRIC_ENGINE = changing how a number is COMPUTED (formula/parity/registry) — high stakes
    # because it shifts numbers product-wide. NOT a metric NAME (a display card uses an existing one).
    "metric_engine":   ([r"metric registry", r"formula book", r"\bparity\b", r"metric definition",
                         r"new metric", r"recompute", r"lib-metrics", r"brain_metrics", r"ts.?python parity"],
                        [r"packages/lib-metrics", r"pylibs/brain_metrics", r"metric.?registry"]),
    "compliance":      ([r"\bdpdp\b", r"\bpdpl\b", r"\bdlt\b", r"\bncpr\b", r"\bdnd\b", r"consent", r"calling.hours", r"9.?am.?9.?pm",
                         r"recording", r"opt.?in", r"template", r"residency", r"in.region"],
                        [r"consent", r"compliance", r"ap-south-1"]),
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
