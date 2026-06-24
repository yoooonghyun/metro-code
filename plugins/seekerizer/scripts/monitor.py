#!/usr/bin/env python3
"""Background monitor: alert when a tracked stock touches its price target.

Registered as a plugin monitor (experimental.monitors in plugin.json). Claude
Code runs it as a persistent background process for the session; each line we
print to stdout is delivered to Claude as a notification, so Claude can tell the
user "AAPL touched your target".

It polls the union of the watchlist and target symbols through
common.get_quotes(), which is backed by the SAME shared cache statusline.py
reads. So this monitor is the single price poller: it keeps the cache warm and
the status line reuses it — no duplicate API calls. Each symbol is fetched at
most once per CACHE_TTL across both.

Once a target is touched it is marked `fired` and won't alert again until the
user re-sets it (which re-arms it).
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (  # noqa: E402
    load_tickers, load_targets, save_targets, load_aliases, get_quotes,
    format_price, is_touched, display_name, CACHE_TTL,
)

POLL_INTERVAL = CACHE_TTL  # align polling with cache freshness


def check_once():
    targets = load_targets()
    armed = {s: t for s, t in targets.items() if not t.get("fired")}
    if not armed:
        # Still keep the watchlist cache warm for the status line.
        tickers = load_tickers()
        if tickers:
            get_quotes(tickers)
        return

    # One fetch pass over everything we care about (shared cache dedupes).
    symbols = sorted(set(load_tickers()) | set(targets))
    quotes = get_quotes(symbols)
    aliases = load_aliases()

    fired_any = False
    for sym, t in armed.items():
        q = quotes.get(sym)
        if not q:
            continue
        price = q["price"]
        if is_touched(t, price):
            arrow = "↑" if t["direction"] == "above" else "↓"
            print(f"🔔 seekerizer alert: {display_name(sym, q, aliases.get(sym))} touched target "
                  f"{arrow} {format_price(sym, t['price'])} "
                  f"(now {format_price(sym, price)})", flush=True)
            targets[sym]["fired"] = True
            fired_any = True
    if fired_any:
        save_targets(targets)


def main():
    try:
        sys.stdout.reconfigure(line_buffering=True)  # timely notification delivery
    except Exception:
        pass
    while True:
        try:
            check_once()
        except Exception:
            pass  # never let a transient error kill the monitor
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
