#!/usr/bin/env python3
"""Claude Code status line: inline stock price ticker.

Wired up via the plugin's settings.json `statusLine` command. On each status
update it reads the watchlist, fetches quotes from the Yahoo Finance public
chart API (no API key), caches them for a short interval, and prints one inline
line. Claude Code passes session info as JSON on stdin; we ignore it.
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import load_tickers, cache_path, currency_for  # noqa: E402

CACHE_TTL = 60          # seconds before re-fetching quotes
HTTP_TIMEOUT = 4        # per-request timeout, keep the status line snappy
SEP = "  │  "


def fetch_quote(symbol):
    """Return (price, prev_close) from Yahoo Finance, or None on failure."""
    url = "https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(symbol)
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
        with open(cache_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_cache(cache):
    try:
        with open(cache_path(), "w", encoding="utf-8") as f:
            json.dump(cache, f)
    except OSError:
        pass


def get_quotes(tickers):
    """Return {symbol: {price, prev}} using cache when fresh."""
    cache = load_cache()
    now = time.time()
    entries = cache.get("entries", {})
    fresh = (now - cache.get("ts", 0)) < CACHE_TTL

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
    if cur in ("₩", "¥"):           # whole-number currencies read better plain
        return f"{cur}{price:,.0f}"
    return f"{cur}{price:,.2f}"


def render(tickers, quotes):
    parts = []
    for t in tickers:
        q = quotes.get(t)
        if not q:
            parts.append(f"{t} —")
            continue
        price, prev = q["price"], q.get("prev")
        chunk = f"{t} {fmt_price(t, price)}"
        if prev:
            pct = (price - prev) / prev * 100
            chunk += f" {'▲' if pct >= 0 else '▼'}{abs(pct):.2f}%"
        parts.append(chunk)
    return "📈 " + SEP.join(parts)


def main():
    try:
        sys.stdin.read()   # drain session JSON; unused
    except Exception:
        pass

    tickers = load_tickers()
    if not tickers:
        print("📈 추적 중인 종목 없음 — /stock-alerts:add-stock 로 종목을 추가하세요")
        return

    print(render(tickers, get_quotes(tickers)))


if __name__ == "__main__":
    main()
