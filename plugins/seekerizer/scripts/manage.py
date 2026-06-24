#!/usr/bin/env python3
"""Manage the tracked stock tickers used by the status line.

Usage:
    manage.py list
    manage.py add <SYMBOL> [<SYMBOL> ...]
    manage.py remove <SYMBOL> [<SYMBOL> ...]
    manage.py clear

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
from common import load_tickers, save_tickers  # noqa: E402


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
    print("Tracked symbols:")
    for t in tickers:
        print(f"  - {t}")


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
    targets = {s.strip().upper() for s in symbols}
    removed = [t for t in tickers if t.upper() in targets]
    kept = [t for t in tickers if t.upper() not in targets]
    for t in removed:
        print(f"Removed: {t}")
    if not removed:
        print("No matching symbols.")
    save_tickers(kept)


def cmd_clear():
    save_tickers([])
    print("Cleared all symbols.")


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
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
