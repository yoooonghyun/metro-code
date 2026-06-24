#!/usr/bin/env python3
"""Claude Code status line: inline stock price ticker.

Wired up via the user's settings.json `statusLine` command (installed by
setup.py). On each status update it reads the watchlist, gets quotes through the
shared cache (common.get_quotes — no duplicate API calls when monitor.py is also
running), and prints one inline line. A 🔔 marks any watchlist symbol that has
touched its price target. Claude Code passes session info as JSON on stdin; we
ignore it.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (  # noqa: E402
    load_tickers, load_targets, get_quotes, format_price, is_touched,
    display_name,
)

SEP = "  │  "

# Korean market convention: gains red, losses blue.
RED = "\033[31m"
BLUE = "\033[34m"
RESET = "\033[0m"


def render(tickers, quotes, targets):
    parts = []
    for t in tickers:
        q = quotes.get(t)
        if not q:
            parts.append(f"{t} —")
            continue
        price, prev = q["price"], q.get("prev")
        chunk = f"{display_name(t, q)} {format_price(t, price)}"
        color = ""
        if prev:
            pct = (price - prev) / prev * 100
            chunk += f" {'▲' if pct >= 0 else '▼'}{abs(pct):.2f}%"
            if pct > 0:
                color = RED
            elif pct < 0:
                color = BLUE
        if color:
            chunk = f"{color}{chunk}{RESET}"
        if t in targets and is_touched(targets[t], price):
            chunk = "🔔 " + chunk
        parts.append(chunk)
    return "📈 " + SEP.join(parts)


def main():
    try:
        sys.stdin.read()   # drain session JSON; unused
    except Exception:
        pass

    tickers = load_tickers()
    if not tickers:
        print("📈 No symbols tracked — add one with /seekerizer:add-symbol")
        return

    print(render(tickers, get_quotes(tickers), load_targets()))


if __name__ == "__main__":
    main()
