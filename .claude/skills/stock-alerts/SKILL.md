---
name: stock-alerts
description: >-
  Manage the stock tickers shown in the Claude Code inline status line. Use when
  the user wants to add, remove, list, or clear tracked stocks/quotes — e.g.
  "주식 종목 추가해줘", "삼성전자 추가", "테슬라 빼줘", "추적 중인 종목 보여줘",
  "add AAPL to my ticker", "show my watchlist", "clear stocks".
---

# Stock Alerts

Manage the watchlist that the status line renders inline at the bottom of
Claude Code. The watchlist lives in `.claude/stock-alerts/tickers.json` and is
edited through `.claude/scripts/stock_manage.py`.

## How it works

- `.claude/scripts/stock_statusline.py` is wired up as the `statusLine` command
  in `.claude/settings.json`. On each status update it reads the watchlist,
  fetches quotes from the Yahoo Finance public API (cached for 60s), and prints
  one inline line like:
  `📈 AAPL $195.23 ▲1.20%  │  TSLA $242.10 ▼0.80%  │  005930.KS ₩71,200 ▲0.50%`
- You manage the watchlist with `stock_manage.py`.

## Symbol format (Yahoo Finance notation)

| Market                | Example       |
|-----------------------|---------------|
| US stock              | `AAPL`, `TSLA`|
| KOSPI (한국 유가증권) | `005930.KS` (삼성전자) |
| KOSDAQ                | `035720.KQ`   |
| Crypto                | `BTC-USD`     |
| Tokyo                 | `7203.T`      |

When the user names a company in Korean/English, map it to the correct symbol
(e.g. 삼성전자 → `005930.KS`, SK하이닉스 → `000660.KS`, 애플 → `AAPL`,
테슬라 → `TSLA`). If unsure of the exact code, ask the user to confirm.

## Commands

Run from the project root. `add` validates the symbol against Yahoo Finance
before saving and prints the resolved company name.

```bash
# Add one or more tickers
python3 .claude/scripts/stock_manage.py add AAPL 005930.KS

# Remove tickers
python3 .claude/scripts/stock_manage.py remove TSLA

# List the current watchlist
python3 .claude/scripts/stock_manage.py list

# Clear everything
python3 .claude/scripts/stock_manage.py clear
```

## Workflow

1. Figure out the Yahoo symbol(s) from what the user said (confirm if ambiguous).
2. Run the appropriate `stock_manage.py` command.
3. Report the result. If `add` printed "확인 실패", the symbol was rejected —
   double-check the code with the user.
4. The status line refreshes automatically; no restart needed (a new quote
   appears within the 60s cache window).
