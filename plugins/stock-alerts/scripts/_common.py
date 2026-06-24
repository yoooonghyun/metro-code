"""Shared helpers for the stock-alerts plugin scripts.

Resolves where the watchlist and quote cache live. We deliberately avoid
storing them inside the plugin directory: ${CLAUDE_PLUGIN_ROOT} changes on every
plugin update, which would wipe the user's watchlist. ${CLAUDE_PLUGIN_DATA}
persists across updates and is the right home for user state.

Resolution order:
    1. $STOCK_ALERTS_DATA_DIR   (explicit override, e.g. for testing)
    2. $CLAUDE_PLUGIN_DATA      (per-plugin persistent dir, set by Claude Code)
    3. ~/.claude/stock-alerts   (fallback when run outside a plugin context)
"""
import json
import os

SUFFIX_CURRENCY = {".KS": "₩", ".KQ": "₩", ".T": "¥", ".L": "£", ".HK": "HK$"}


def data_dir():
    base = (
        os.environ.get("STOCK_ALERTS_DATA_DIR")
        or os.environ.get("CLAUDE_PLUGIN_DATA")
        or os.path.expanduser("~/.claude/stock-alerts")
    )
    os.makedirs(base, exist_ok=True)
    return base


def tickers_path():
    return os.path.join(data_dir(), "tickers.json")


def cache_path():
    return os.path.join(data_dir(), "cache.json")


def load_tickers():
    try:
        with open(tickers_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [str(t).strip() for t in data if str(t).strip()]
    except (OSError, ValueError):
        pass
    return []


def save_tickers(tickers):
    with open(tickers_path(), "w", encoding="utf-8") as f:
        json.dump(tickers, f, ensure_ascii=False, indent=2)


def currency_for(symbol):
    for suffix, sym in SUFFIX_CURRENCY.items():
        if symbol.upper().endswith(suffix):
            return sym
    return "$"
