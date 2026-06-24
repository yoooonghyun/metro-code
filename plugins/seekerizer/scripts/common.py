"""Shared helpers for the seekerizer plugin scripts.

This module is the single source of truth for:
  - where user state lives (watchlist, price targets, quote cache),
  - fetching quotes from Yahoo Finance, and
  - the shared quote cache.

Quote fetching goes through get_quotes(), which is backed by one cache file
(cache.json) keyed per symbol with a timestamp. statusline.py and monitor.py
both call get_quotes(), so whichever runs first within the TTL warms the cache
and the other reuses it — there is never a duplicate API call for a symbol that
is already fresh.

State location resolution (so data survives plugin updates, which change
${CLAUDE_PLUGIN_ROOT}):
    1. $SEEKERIZER_DATA_DIR   (explicit override, e.g. for testing)
    2. $CLAUDE_PLUGIN_DATA    (per-plugin persistent dir, set by Claude Code)
    3. ~/.claude/seekerizer   (fallback when run outside a plugin context)
"""
import json
import os
import re
import time
import urllib.request
import urllib.error
import urllib.parse

SUFFIX_CURRENCY = {".KS": "₩", ".KQ": "₩", ".T": "¥", ".L": "£", ".HK": "HK$"}

CACHE_TTL = 60       # seconds a cached quote stays fresh (shared by all callers)
HTTP_TIMEOUT = 4     # per-request timeout


# --- paths -----------------------------------------------------------------

def data_dir():
    base = (
        os.environ.get("SEEKERIZER_DATA_DIR")
        or os.environ.get("CLAUDE_PLUGIN_DATA")
        or os.path.expanduser("~/.claude/seekerizer")
    )
    os.makedirs(base, exist_ok=True)
    return base


def tickers_path():
    return os.path.join(data_dir(), "tickers.json")


def targets_path():
    return os.path.join(data_dir(), "targets.json")


def cache_path():
    return os.path.join(data_dir(), "cache.json")


def aliases_path():
    return os.path.join(data_dir(), "aliases.json")


def _read_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _atomic_write(path, obj):
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except OSError:
        pass


# --- watchlist -------------------------------------------------------------

def load_tickers():
    data = _read_json(tickers_path(), [])
    if isinstance(data, list):
        return [str(t).strip() for t in data if str(t).strip()]
    return []


def save_tickers(tickers):
    _atomic_write(tickers_path(), tickers)


# --- price targets ---------------------------------------------------------
# targets.json: { "AAPL": {"price": 300.0, "direction": "above", "fired": false} }
#   direction "above" -> touched when price >= target
#   direction "below" -> touched when price <= target

def load_targets():
    data = _read_json(targets_path(), {})
    return data if isinstance(data, dict) else {}


def save_targets(targets):
    _atomic_write(targets_path(), targets)


# --- display aliases -------------------------------------------------------
# aliases.json: { "005930.KS": "삼성전자" } — a user-chosen label that overrides
# the auto company name (e.g. to show Korean names Yahoo doesn't provide).

def load_aliases():
    data = _read_json(aliases_path(), {})
    return data if isinstance(data, dict) else {}


def save_aliases(aliases):
    _atomic_write(aliases_path(), aliases)


def is_touched(target, price):
    if price is None:
        return False
    if target["direction"] == "above":
        return price >= target["price"]
    return price <= target["price"]


# --- formatting ------------------------------------------------------------

def currency_for(symbol):
    for suffix, sym in SUFFIX_CURRENCY.items():
        if symbol.upper().endswith(suffix):
            return sym
    return "$"


def format_price(symbol, price):
    cur = currency_for(symbol)
    if cur in ("₩", "¥"):           # whole-number currencies read better plain
        return f"{cur}{price:,.0f}"
    return f"{cur}{price:,.2f}"


# Trailing corporate suffixes that just add noise on a status line.
_SUFFIX_RE = re.compile(
    r"(?:[,\s]+(?:Co\.,?\s*Ltd\.?|Holdings?|Incorporated|Inc\.?|Corporation|"
    r"Corp\.?|Company|Limited|Ltd\.?|PLC|plc|S\.A\.|AG|N\.V\.|Group))+$", re.I)


def clean_name(name):
    """Strip corporate suffixes: 'Samsung Electronics Co., Ltd.' -> 'Samsung Electronics'."""
    out = _SUFFIX_RE.sub("", name).strip(" ,.")
    return out or name


def display_name(symbol, quote=None, alias=None):
    """Human-readable label for a symbol.

    Priority: user alias > cleaned company name > the symbol itself. Korean
    tickers are numeric (e.g. 005930.KS), so a name/alias makes the status line
    readable. `quote` is an entry from get_quotes(); `alias` is from load_aliases().
    """
    if alias:
        return alias
    name = (quote or {}).get("name")
    return clean_name(name) if name else symbol


# --- quotes (single fetch path + shared cache) -----------------------------

def fetch_quote(symbol):
    """Raw Yahoo Finance call. Returns (price, prev_close, name) or None on failure."""
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
        # Prefer longName; shortName is sometimes a junk id string for KOSDAQ.
        name = meta.get("longName") or meta.get("shortName")
        if name and symbol.split(".")[0] in name:
            name = None
        return float(price), float(prev) if prev is not None else None, name
    except (urllib.error.URLError, KeyError, IndexError, ValueError, TypeError):
        return None


def _load_cache():
    data = _read_json(cache_path(), {})
    # Expected shape: { "AAPL": {"price":.., "prev":.., "ts":..}, ... }
    return data if isinstance(data, dict) else {}


def get_quotes(symbols, ttl=CACHE_TTL):
    """Return {symbol: {"price", "prev"}} for symbols, using the shared cache.

    A symbol is fetched only if it is missing or older than `ttl` in the cache;
    otherwise the cached value is reused. On a fetch failure the last known
    cached value (if any) is kept. This is the ONLY place quotes are fetched, so
    statusline.py and monitor.py never make redundant calls for fresh symbols.
    """
    cache = _load_cache()
    now = time.time()
    changed = False
    out = {}
    for s in symbols:
        c = cache.get(s)
        if c and (now - c.get("ts", 0)) < ttl and "price" in c:
            out[s] = {"price": c["price"], "prev": c.get("prev"), "name": c.get("name")}
            continue
        q = fetch_quote(s)
        if q is not None:
            price, prev, name = q
            # Keep a previously known name if this response omitted one.
            name = name or (c or {}).get("name")
            cache[s] = {"price": price, "prev": prev, "name": name, "ts": now}
            out[s] = {"price": price, "prev": prev, "name": name}
            changed = True
        elif c and "price" in c:
            out[s] = {"price": c["price"], "prev": c.get("prev"), "name": c.get("name")}
    if changed:
        _atomic_write(cache_path(), cache)
    return out
