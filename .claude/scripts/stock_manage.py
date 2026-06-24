#!/usr/bin/env python3
"""Manage the tracked stock tickers used by the status line.

Usage:
    stock_manage.py list
    stock_manage.py add <SYMBOL> [<SYMBOL> ...]
    stock_manage.py remove <SYMBOL> [<SYMBOL> ...]
    stock_manage.py clear

Symbols use Yahoo Finance notation:
    AAPL          Apple (US)
    TSLA          Tesla (US)
    005930.KS     Samsung Electronics (KOSPI)
    035720.KQ     Kakao-style KOSDAQ listing
    BTC-USD       Bitcoin
"""
import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "stock-alerts")
TICKERS_FILE = os.path.join(DATA_DIR, "tickers.json")


def load():
    try:
        with open(TICKERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [str(t) for t in data] if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def save(tickers):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(TICKERS_FILE, "w", encoding="utf-8") as f:
        json.dump(tickers, f, ensure_ascii=False, indent=2)


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
    tickers = load()
    if not tickers:
        print("추적 중인 종목이 없습니다.")
        return
    print("추적 중인 종목:")
    for t in tickers:
        print(f"  - {t}")


def cmd_add(symbols):
    tickers = load()
    for raw in symbols:
        sym = raw.strip().upper()
        if not sym:
            continue
        if sym in tickers:
            print(f"이미 추가됨: {sym}")
            continue
        ok, name = validate(sym)
        if not ok:
            print(f"확인 실패(유효하지 않은 심볼일 수 있음): {sym}")
            continue
        tickers.append(sym)
        print(f"추가됨: {sym}  ({name})")
    save(tickers)


def cmd_remove(symbols):
    tickers = load()
    targets = {s.strip().upper() for s in symbols}
    kept = [t for t in tickers if t.upper() not in targets]
    removed = [t for t in tickers if t.upper() in targets]
    for t in removed:
        print(f"삭제됨: {t}")
    if not removed:
        print("일치하는 종목이 없습니다.")
    save(kept)


def cmd_clear():
    save([])
    print("모든 종목을 삭제했습니다.")


def main(argv):
    if not argv:
        print(__doc__)
        return 1
    cmd, rest = argv[0], argv[1:]
    if cmd == "list":
        cmd_list()
    elif cmd == "add":
        if not rest:
            print("사용법: stock_manage.py add <SYMBOL> ...")
            return 1
        cmd_add(rest)
    elif cmd == "remove":
        if not rest:
            print("사용법: stock_manage.py remove <SYMBOL> ...")
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
