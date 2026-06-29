#!/usr/bin/env python3
"""Claude Code status line: inline stock price ticker.

Wired up via the user's settings.json `statusLine` command (installed by
setup.py). On each status update it reads the watchlist, gets quotes through the
shared cache (common.get_quotes — no duplicate API calls when monitor.py is also
running). A 🔔 marks any watchlist symbol that has touched its price target.

Output wraps to the terminal width: Claude Code renders each printed line as a
separate status row, but does not wrap a too-wide line cleanly, so we pack the
symbols across as many rows as needed to fit. Width comes from the COLUMNS env
var Claude Code sets before running us (v2.1.153+), falling back to the terminal
size. Claude Code passes session info as JSON on stdin; we ignore it.
"""
import os
import re
import shutil
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (  # noqa: E402
    load_tickers, load_targets, load_aliases, get_quotes, format_price,
    is_touched, display_name,
)

SEP = "  │  "
PREFIX = "📈 "
INDENT = "   "   # aligns wrapped rows under the first symbol

# Korean market convention: gains red, losses blue.
RED = "\033[31m"
BLUE = "\033[34m"
RESET = "\033[0m"

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def visible_width(s):
    """Display columns of a string, ignoring ANSI codes; CJK/emoji count as 2."""
    width = 0
    for ch in _ANSI.sub("", s):
        if unicodedata.east_asian_width(ch) in ("W", "F") or ord(ch) >= 0x1F000:
            width += 2
        else:
            width += 1
    return width


def wrap(parts, width):
    """Greedily pack parts into rows no wider than `width` columns."""
    if not parts:
        return PREFIX.rstrip()
    lines, cur, cur_w, has_part = [], PREFIX, visible_width(PREFIX), False
    sep_w = visible_width(SEP)
    for p in parts:
        pw = visible_width(p)
        if not has_part:
            cur, cur_w, has_part = cur + p, cur_w + pw, True
        elif cur_w + sep_w + pw <= width:
            cur, cur_w = cur + SEP + p, cur_w + sep_w + pw
        else:
            lines.append(cur)
            cur, cur_w = INDENT + p, visible_width(INDENT) + pw
    lines.append(cur)
    return "\n".join(lines)


def render(tickers, quotes, targets, aliases=None, width=None):
    aliases = aliases or {}
    parts = []
    for t in tickers:
        q = quotes.get(t)
        if not q:
            parts.append(f"{display_name(t, alias=aliases.get(t))} —")
            continue
        price, prev = q["price"], q.get("prev")
        chunk = f"{display_name(t, q, aliases.get(t))} {format_price(t, price)}"
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
    # width=None -> single line (no wrapping); callers pass the terminal width.
    return wrap(parts, width if width is not None else 10 ** 9)


def term_width():
    try:
        cols = int(os.environ.get("COLUMNS", "") or 0)
    except ValueError:
        cols = 0
    return cols if cols > 0 else shutil.get_terminal_size((80, 20)).columns


def main():
    try:
        sys.stdin.read()   # drain session JSON; unused
    except Exception:
        pass

    tickers = load_tickers()
    if not tickers:
        print("📈 No symbols tracked — add one with /seekerizer:add-symbol")
        return

    print(render(tickers, get_quotes(tickers), load_targets(), load_aliases(),
                 term_width()))


if __name__ == "__main__":
    main()
