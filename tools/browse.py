#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright>=1.40"]
# ///
"""
Engineering OS — real-browser + visual QA engine (gstack-inspired, Point: browser QA).

Drives a REAL Chromium (via Playwright) so QA (Tanvi) and the web dev (Ananya)
verify actual rendered behaviour — console errors, failed requests, broken
flows, visual state — instead of trusting mocks. This is plugin-side DEV
TOOLING (in tools/), NOT a Brain product runtime dependency, so it does not
touch Brain's locked product stack.

Subcommands (all print JSON to stdout; human note to stderr):
  check <url> [--screenshot OUT] [--full-page] [--headed] [--wait load|domcontentloaded|networkidle]
        Load a page; capture console errors/warnings, page errors, failed
        requests, HTTP>=400 responses, title. The "is this page actually healthy" smoke.
  screenshot <url> --out FILE [--full-page] [--headed]
        Capture a screenshot (for /design-review before/after).
  extract <url> --selector CSS [--attr NAME] [--headed]
        Pull text (or an attribute) from matching elements.
  run <scenario.json> [--headed] [--artifacts DIR]
        Execute a multi-step flow in ONE session (navigate/fill/click/wait/
        expect_text/expect_url/screenshot), capturing console+network the whole
        time. The exploratory QA walk + the basis for a generated regression test.

First run auto-installs the Chromium binary if missing (set EOS_NO_BROWSER_INSTALL=1 to disable).

Usage:
  uv run tools/browse.py check https://example.com --screenshot /tmp/x.png
  uv run tools/browse.py run flow.json --artifacts ./shots
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def _log(msg: str) -> None:
    print(f"[browse] {msg}", file=sys.stderr)


def ensure_chromium() -> None:
    """Install the Chromium binary on first use (idempotent, network-failure-safe)."""
    if os.environ.get("EOS_NO_BROWSER_INSTALL") == "1":
        return
    try:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=False, capture_output=True, text=True, timeout=600,
        )
    except Exception as e:  # never fatal here; launch() will surface a clear error
        _log(f"chromium auto-install skipped ({e})")


class Capture:
    """Collects console errors/warnings, page errors, failed + 4xx/5xx requests.
    With live=True, also streams each event to stderr the moment it fires (for
    monitoring mode — the operator watches issues appear in real time)."""

    def __init__(self, live: bool = False):
        self.console_errors: list[dict] = []
        self.page_errors: list[str] = []
        self.failed_requests: list[dict] = []
        self.bad_responses: list[dict] = []
        self.live = live

    def _emit(self, kind: str, detail: str) -> None:
        if self.live:
            print(f"[monitor] {kind}: {detail[:200]}", file=sys.stderr, flush=True)

    def wire(self, page) -> None:
        def on_console(m):
            if m.type in ("error", "warning"):
                self.console_errors.append({"type": m.type, "text": m.text[:500]})
                self._emit(f"console.{m.type}", m.text)
        page.on("console", on_console)

        def on_pageerror(e):
            self.page_errors.append(str(e)[:500])
            self._emit("page-error", str(e))
        page.on("pageerror", on_pageerror)

        def on_reqfail(r):
            self.failed_requests.append({"url": r.url[:300], "failure": (r.failure or "")[:200]})
            self._emit("request-failed", f"{r.url} ({r.failure or ''})")
        page.on("requestfailed", on_reqfail)

        def on_response(resp):
            if resp.status >= 400:
                self.bad_responses.append({"url": resp.url[:300], "status": resp.status})
                self._emit("http-error", f"{resp.status} {resp.url}")
        page.on("response", on_response)

    def summary(self) -> dict:
        return {
            "console_errors": self.console_errors,
            "page_errors": self.page_errors,
            "failed_requests": self.failed_requests,
            "bad_responses": self.bad_responses,
            "clean": not (self.console_errors or self.page_errors
                          or self.failed_requests or self.bad_responses),
        }


def _launch(p, headed: bool):
    return p.chromium.launch(headless=not headed)


def cmd_check(args) -> dict:
    from playwright.sync_api import sync_playwright

    cap = Capture()
    with sync_playwright() as p:
        browser = _launch(p, args.headed)
        page = browser.new_page()
        cap.wire(page)
        status = None
        try:
            resp = page.goto(args.url, wait_until=args.wait, timeout=30000)
            status = resp.status if resp else None
            title = page.title()
            if args.screenshot:
                Path(args.screenshot).parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=args.screenshot, full_page=args.full_page)
            ok = True
        except Exception as e:
            title, ok = None, False
            cap.page_errors.append(f"navigation: {e}")
        browser.close()
    s = cap.summary()
    return {"command": "check", "url": args.url, "ok": ok and s["clean"],
            "http_status": status, "title": title,
            "screenshot": args.screenshot, **s}


def cmd_screenshot(args) -> dict:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = _launch(p, args.headed)
        page = browser.new_page()
        page.goto(args.url, wait_until="networkidle", timeout=30000)
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=args.out, full_page=args.full_page)
        browser.close()
    return {"command": "screenshot", "url": args.url, "out": args.out,
            "full_page": args.full_page, "ok": True}


def cmd_extract(args) -> dict:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = _launch(p, args.headed)
        page = browser.new_page()
        page.goto(args.url, wait_until="networkidle", timeout=30000)
        els = page.query_selector_all(args.selector)
        out = []
        for el in els[:50]:
            out.append(el.get_attribute(args.attr) if args.attr else (el.inner_text() or "").strip()[:300])
        browser.close()
    return {"command": "extract", "url": args.url, "selector": args.selector,
            "attr": args.attr, "count": len(out), "values": out, "ok": True}


def cmd_run(args) -> dict:
    from playwright.sync_api import sync_playwright

    scenario = json.loads(Path(args.scenario).read_text())
    base = scenario.get("base_url", "")
    steps = scenario.get("steps", [])
    artifacts = Path(args.artifacts or ".")
    artifacts.mkdir(parents=True, exist_ok=True)
    cap = Capture()
    results = []
    passed = True

    with sync_playwright() as p:
        browser = _launch(p, args.headed)
        page = browser.new_page()
        cap.wire(page)
        for i, step in enumerate(steps):
            action = step.get("action")
            r = {"step": i, "action": action, "ok": True}
            try:
                if action == "navigate":
                    url = step["url"] if step["url"].startswith(("http", "file")) else base + step["url"]
                    page.goto(url, wait_until=step.get("wait", "networkidle"), timeout=30000)
                elif action == "fill":
                    page.fill(step["selector"], step["value"])
                elif action == "click":
                    page.click(step["selector"], timeout=10000)
                elif action == "wait":
                    if "selector" in step:
                        page.wait_for_selector(step["selector"], timeout=step.get("timeout", 10000))
                    else:
                        page.wait_for_timeout(step.get("ms", 500))
                elif action == "expect_text":
                    txt = page.inner_text(step["selector"])
                    if step["text"] not in txt:
                        raise AssertionError(f"expected '{step['text']}' in '{txt[:120]}'")
                elif action == "expect_url":
                    if step["contains"] not in page.url:
                        raise AssertionError(f"url '{page.url}' missing '{step['contains']}'")
                elif action == "screenshot":
                    out = artifacts / step.get("name", f"step-{i}.png")
                    page.screenshot(path=str(out), full_page=step.get("full_page", False))
                    r["screenshot"] = str(out)
                else:
                    raise ValueError(f"unknown action: {action}")
            except Exception as e:
                r["ok"] = False
                r["error"] = str(e)[:300]
                passed = False
                # capture a failure screenshot
                try:
                    fail_shot = artifacts / f"FAIL-step-{i}.png"
                    page.screenshot(path=str(fail_shot))
                    r["screenshot"] = str(fail_shot)
                except Exception:
                    pass
                results.append(r)
                break  # stop on first failure (a flow is sequential)
            results.append(r)
        browser.close()

    s = cap.summary()
    return {"command": "run", "scenario": scenario.get("name", args.scenario),
            "passed": passed and s["clean"], "steps_run": len(results),
            "steps": results, **s}


def cmd_monitor(args) -> dict:
    """LIVE MONITORING MODE — keep a real browser open on the running app and
    capture console/page/network errors AS THEY HAPPEN for --duration seconds,
    optionally re-sweeping each URL every --interval seconds. Streams each issue
    to stderr live; returns a JSON summary (exit 2 if any issue seen)."""
    from playwright.sync_api import sync_playwright

    urls = args.url
    print(f"[monitor] watching {len(urls)} url(s) for {args.duration}s "
          f"(interval={args.interval}s)…", file=sys.stderr, flush=True)
    cap = Capture(live=True)
    deadline = time.time() + args.duration
    sweeps = 0
    with sync_playwright() as p:
        browser = _launch(p, args.headed)
        page = browser.new_page()
        cap.wire(page)
        # initial load of each url
        for u in urls:
            try:
                page.goto(u, wait_until="networkidle", timeout=30000)
            except Exception as e:
                cap.page_errors.append(f"navigation {u}: {e}")
                cap._emit("nav-error", f"{u}: {e}")
        sweeps += 1
        # watch window: idle-wait, or periodic re-sweep if interval>0
        while time.time() < deadline:
            if args.interval and args.interval > 0:
                page.wait_for_timeout(min(args.interval, max(0, deadline - time.time())) * 1000)
                for u in urls:
                    if time.time() >= deadline:
                        break
                    try:
                        page.goto(u, wait_until="networkidle", timeout=30000)
                    except Exception as e:
                        cap._emit("nav-error", f"{u}: {e}")
                sweeps += 1
            else:
                page.wait_for_timeout(min(2, max(0, deadline - time.time())) * 1000)
        browser.close()
    s = cap.summary()
    total = (len(s["console_errors"]) + len(s["page_errors"])
             + len(s["failed_requests"]) + len(s["bad_responses"]))
    print(f"[monitor] done — {sweeps} sweep(s), {total} issue(s) captured.", file=sys.stderr, flush=True)
    return {"command": "monitor", "urls": urls, "duration_s": args.duration,
            "sweeps": sweeps, "issue_count": total, "ok": total == 0, **s}


def main() -> int:
    ap = argparse.ArgumentParser(description="Engineering OS browser + visual QA engine")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check"); c.add_argument("url")
    c.add_argument("--screenshot"); c.add_argument("--full-page", action="store_true")
    c.add_argument("--headed", action="store_true")
    c.add_argument("--wait", default="networkidle", choices=["load", "domcontentloaded", "networkidle"])

    s = sub.add_parser("screenshot"); s.add_argument("url"); s.add_argument("--out", required=True)
    s.add_argument("--full-page", action="store_true"); s.add_argument("--headed", action="store_true")

    e = sub.add_parser("extract"); e.add_argument("url"); e.add_argument("--selector", required=True)
    e.add_argument("--attr"); e.add_argument("--headed", action="store_true")

    r = sub.add_parser("run"); r.add_argument("scenario"); r.add_argument("--headed", action="store_true")
    r.add_argument("--artifacts")

    m = sub.add_parser("monitor"); m.add_argument("url", nargs="+", help="one or more app URLs to watch")
    m.add_argument("--duration", type=int, default=60, help="seconds to watch (default 60)")
    m.add_argument("--interval", type=int, default=0, help="re-sweep each URL every N seconds (0 = watch idle)")
    m.add_argument("--headed", action="store_true")

    args = ap.parse_args()
    ensure_chromium()
    fn = {"check": cmd_check, "screenshot": cmd_screenshot,
          "extract": cmd_extract, "run": cmd_run, "monitor": cmd_monitor}[args.cmd]
    try:
        out = fn(args)
    except Exception as ex:
        msg = str(ex)
        if "Executable doesn't exist" in msg or "playwright install" in msg:
            _log("Chromium not installed. Run: uv run --with playwright python -m playwright install chromium")
        print(json.dumps({"command": args.cmd, "ok": False, "error": msg[:500]}))
        return 1
    print(json.dumps(out, ensure_ascii=False, indent=2))
    # exit non-zero if the page/flow was not clean, so CI + agents can gate on it
    return 0 if out.get("ok", out.get("passed", True)) else 2


if __name__ == "__main__":
    sys.exit(main())
