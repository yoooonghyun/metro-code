#!/usr/bin/env python3
"""Manage the tracked stock tickers used by the status line.

Usage:
    manage.py list
    manage.py add <SYMBOL> [<SYMBOL> ...]
    manage.py remove <SYMBOL> [<SYMBOL> ...]
    manage.py clear
    manage.py alias <SYMBOL> <NAME...>     # custom display label (e.g. Korean)
    manage.py unalias <SYMBOL> [...]       # drop the custom label

Symbols use Yahoo Finance notation:
    AAPL          Apple (US)
    TSLA          Tesla (US)
    005930.KS     Samsung Electronics (KOSPI)
    035720.KQ     a KOSDAQ listing
    BTC-USD       Bitcoin
"""
import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (  # noqa: E402
    load_tickers, save_tickers, load_aliases, save_aliases, load_targets,
)


def validate(symbol):
    """Confirm the symbol resolves on Yahoo Finance. Returns (ok, name)."""
    url = "https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(symbol)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            payload = json.load(resp)
        result = payload.get("chart", {}).get("result")
        if not result:
            return False, None
        meta = result[0].get("meta", {})
        if meta.get("regularMarketPrice") is None:
            return False, None
        return True, meta.get("longName") or meta.get("shortName") or symbol
    except (urllib.error.URLError, ValueError, KeyError, IndexError):
        return False, None


def cmd_list():
    tickers = load_tickers()
    if not tickers:
        print("No symbols tracked.")
        return
    aliases = load_aliases()
    print("Tracked symbols:")
    for t in tickers:
        alias = aliases.get(t)
        print(f"  - {t}" + (f"  ({alias})" if alias else ""))


def cmd_add(symbols):
    tickers = load_tickers()
    for raw in symbols:
        sym = raw.strip().upper()
        if not sym:
            continue
        if sym in tickers:
            print(f"Already tracked: {sym}")
            continue
        ok, name = validate(sym)
        if not ok:
            print(f"Validation failed (symbol may not exist): {sym}")
            continue
        tickers.append(sym)
        print(f"Added: {sym}  ({name})")
    save_tickers(tickers)


def cmd_remove(symbols):
    tickers = load_tickers()
    wanted = {s.strip().upper() for s in symbols}
    removed = [t for t in tickers if t.upper() in wanted]
    kept = [t for t in tickers if t.upper() not in wanted]
    if not removed:
        print("No matching symbols.")
        return
    save_tickers(kept)
    # Drop any display alias for the removed symbols (cosmetic, tied to the ticker).
    aliases = load_aliases()
    if any(s in aliases for s in removed):
        for s in removed:
            aliases.pop(s, None)
        save_aliases(aliases)
    price_targets = load_targets()
    for t in removed:
        print(f"Removed: {t}")
        if t in price_targets:
            print(f"  note: {t} still has a price target — "
                  f"remove it with: targets.py remove {t}")


def cmd_clear():
    save_tickers([])
    print("Cleared all symbols.")


def cmd_alias(args):
    if len(args) < 2:
        print("Usage: manage.py alias <SYMBOL> <NAME...>")
        return 1
    sym = args[0].strip().upper()
    name = " ".join(args[1:]).strip()
    if not name:
        print("Alias name is empty.")
        return 1
    aliases = load_aliases()
    aliases[sym] = name
    save_aliases(aliases)
    print(f"Alias set: {sym} -> {name}")
    return 0


def cmd_unalias(symbols):
    aliases = load_aliases()
    removed = []
    for raw in symbols:
        sym = raw.strip().upper()
        if sym in aliases:
            del aliases[sym]
            removed.append(sym)
    save_aliases(aliases)
    if removed:
        for s in removed:
            print(f"Alias removed: {s}")
    else:
        print("No matching aliases.")
    return 0


def main(argv):
    if not argv:
        print(__doc__)
        return 1
    cmd, rest = argv[0], argv[1:]
    if cmd == "list":
        cmd_list()
    elif cmd == "add":
        if not rest:
            print("Usage: manage.py add <SYMBOL> ...")
            return 1
        cmd_add(rest)
    elif cmd == "remove":
        if not rest:
            print("Usage: manage.py remove <SYMBOL> ...")
            return 1
        cmd_remove(rest)
    elif cmd == "clear":
        cmd_clear()
    elif cmd == "alias":
        return cmd_alias(rest)
    elif cmd == "unalias":
        if not rest:
            print("Usage: manage.py unalias <SYMBOL> ...")
            return 1
        return cmd_unalias(rest)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
