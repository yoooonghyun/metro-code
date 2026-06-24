#!/usr/bin/env python3
"""Claude Code status line: inline stock price ticker.

Reads tracked tickers from .claude/stock-alerts/tickers.json, fetches quotes
from the Yahoo Finance public chart API (no API key required), caches them for
a short interval, and prints a single inline status line.

Claude Code passes session info as JSON on stdin; we ignore it and just emit
one line of output, which Claude Code renders at the bottom of the UI.
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error
import urllib.parse

# Resolve paths relative to the project root (.claude/..).
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "stock-alerts")
TICKERS_FILE = os.path.join(DATA_DIR, "tickers.json")
CACHE_FILE = os.path.join(DATA_DIR, "cache.json")

CACHE_TTL = 60          # seconds before re-fetching quotes
HTTP_TIMEOUT = 4        # per-request timeout, keep the status line snappy
SEP = "  │  "

# Currency symbol by Yahoo suffix; default to "$".
SUFFIX_CURRENCY = {".KS": "₩", ".KQ": "₩", ".T": "¥", ".L": "£", ".HK": "HK$"}


def load_tickers():
    try:
        with open(TICKERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [str(t).strip() for t in data if str(t).strip()]
    except (OSError, ValueError):
        pass
    return []


def currency_for(symbol):
    for suffix, sym in SUFFIX_CURRENCY.items():
        if symbol.upper().endswith(suffix):
            return sym
    return "$"


def fetch_quote(symbol):
    """Return (price, prev_close) from Yahoo Finance, or None on failure."""
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        + urllib.parse.quote(symbol)
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            payload = json.load(resp)
        meta = payload["chart"]["result"][0]["meta"]
        price = meta.get("regularMarketPrice")
        prev = meta.get("chartPreviousClose") or meta.get("previousClose")
        if price is None:
            return None
        return float(price), float(prev) if prev is not None else None
    except (urllib.error.URLError, KeyError, IndexError, ValueError, TypeError):
        return None


def load_cache():
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_cache(cache):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f)
    except OSError:
        pass


def get_quotes(tickers):
    """Return {symbol: {price, prev}} using cache when fresh."""
    cache = load_cache()
    now = time.time()
    entries = cache.get("entries", {})
    fresh = (now - cache.get("ts", 0)) < CACHE_TTL

    # Reuse the whole cache only if it covers every requested ticker.
    if fresh and all(t in entries for t in tickers):
        return entries

    updated = {}
    for t in tickers:
        q = fetch_quote(t)
        if q is not None:
            price, prev = q
            updated[t] = {"price": price, "prev": prev}
        elif t in entries:
            updated[t] = entries[t]  # keep last known value on failure
    save_cache({"ts": now, "entries": updated})
    return updated


def fmt_price(symbol, price):
    cur = currency_for(symbol)
    # Whole-number currencies (KRW/JPY) read better without decimals.
    if cur in ("₩", "¥"):
        return f"{cur}{price:,.0f}"
    return f"{cur}{price:,.2f}"


def render(tickers, quotes):
    parts = []
    for t in tickers:
        q = quotes.get(t)
        if not q:
            parts.append(f"{t} —")
            continue
        price = q["price"]
        prev = q.get("prev")
        label = t
        chunk = f"{label} {fmt_price(t, price)}"
        if prev:
            pct = (price - prev) / prev * 100
            arrow = "▲" if pct >= 0 else "▼"
            chunk += f" {arrow}{abs(pct):.2f}%"
        parts.append(chunk)
    return "📈 " + SEP.join(parts)


def main():
    # Drain stdin (Claude Code sends session JSON); we don't need it.
    try:
        sys.stdin.read()
    except Exception:
        pass

    tickers = load_tickers()
    if not tickers:
        print("📈 추적 중인 종목 없음 — skill로 종목을 추가하세요")
        return

    quotes = get_quotes(tickers)
    print(render(tickers, quotes))


if __name__ == "__main__":
    main()
