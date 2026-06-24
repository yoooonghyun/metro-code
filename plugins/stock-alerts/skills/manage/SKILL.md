---
name: manage
description: >-
  Add, remove, list, or clear the stocks shown in the Claude Code inline status
  line. Use when the user mentions stocks/quotes/watchlist — e.g. "주식 종목
  추가해줘", "삼성전자 추가", "테슬라 빼줘", "추적 중인 종목 보여줘",
  "add AAPL to my ticker", "show my watchlist", "clear stocks".
---

# Stock Alerts — watchlist management

Manage the watchlist that the status line renders inline at the bottom of Claude
Code. The watchlist is stored in the plugin's persistent data dir and edited
through `stock_manage.py`.

> If the status line isn't showing yet, the user needs to run the setup skill
> once: `/stock-alerts:setup`. Mention this if they ask "why don't
> I see any prices".

## Symbol format (Yahoo Finance notation)

| Market                | Example       |
|-----------------------|---------------|
| US stock              | `AAPL`, `TSLA`|
| KOSPI (한국 유가증권) | `005930.KS` (삼성전자) |
| KOSDAQ                | `035720.KQ`   |
| Crypto                | `BTC-USD`     |
| Tokyo                 | `7203.T`      |

Map company names to symbols (삼성전자 → `005930.KS`, SK하이닉스 → `000660.KS`,
애플 → `AAPL`, 테슬라 → `TSLA`, 엔비디아 → `NVDA`). If unsure of the exact
code, ask the user to confirm before adding.

## Commands

Run with the plugin's bundled script. `add` validates each symbol against the
Yahoo Finance API before saving and prints the resolved company name.

```bash
# Add one or more tickers
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stock_manage.py" add AAPL 005930.KS

# Remove tickers
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stock_manage.py" remove TSLA

# List the current watchlist
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stock_manage.py" list

# Clear everything
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stock_manage.py" clear
```

## Workflow

1. Resolve the Yahoo symbol(s) from what the user said (confirm if ambiguous).
2. Run the appropriate `stock_manage.py` command.
3. Report the result. If `add` printed "확인 실패", the symbol was rejected —
   double-check the code with the user.
4. The status line refreshes on its own; a new quote appears within ~60s (the
   quote cache window). No restart needed.
