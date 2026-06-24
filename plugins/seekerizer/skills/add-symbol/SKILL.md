---
name: add-symbol
description: >-
  Add a stock to the Claude Code status-line watchlist. Use when the user wants
  to track/add a stock — e.g. "add AAPL", "track Tesla", "watch NVDA" (also
  Korean: "삼성전자 추가해줘", "테슬라 담아줘"). To remove use the remove-symbol
  skill; for a custom label use alias-symbol.
---

# Seekerizer — add a symbol

Add one or more symbols to the watchlist rendered in the status line. The
watchlist lives in the plugin's persistent data dir and is edited through
`manage.py`.

> If the status line isn't showing yet, run the setup skill once
> (`/seekerizer:setup`). Mention this if the user asks "why don't I see prices".

## Symbol format (Yahoo Finance notation)

| Market      | Example                  |
|-------------|--------------------------|
| US stock    | `AAPL`, `TSLA`           |
| KOSPI       | `005930.KS` (Samsung)    |
| KOSDAQ      | `035720.KQ`              |
| Crypto      | `BTC-USD`               |
| Tokyo       | `7203.T`                |

Map company names to symbols, including Korean names the user may say:
Samsung Electronics / 삼성전자 → `005930.KS`, SK hynix / SK하이닉스 →
`000660.KS`, Apple / 애플 → `AAPL`, Tesla / 테슬라 → `TSLA`, NVIDIA / 엔비디아 →
`NVDA`. If unsure of the exact code, confirm with the user before adding.

## Command

`add` validates each symbol against the Yahoo Finance API before saving and
prints the resolved company name.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage.py" add AAPL 005930.KS
```

## Workflow

1. Resolve the Yahoo symbol(s) from what the user said (confirm if ambiguous).
2. Run `manage.py add ...`.
3. If it printed "Validation failed", the symbol was rejected — double-check the
   code with the user. The status line picks up the new quote within ~60s; no
   restart needed.
