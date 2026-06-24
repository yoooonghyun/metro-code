---
name: add-symbol
description: >-
  Add, remove, list, or clear the stocks in the Claude Code status line, or set a
  custom display label (alias) for one. Use when the user mentions
  stocks/quotes/watchlist — e.g. "add AAPL", "remove/delete TSLA", "show my
  watchlist", "label 005930.KS as 삼성전자" (also matches Korean such as
  "삼성전자 추가", "테슬라 삭제해줘", "005930.KS를 삼성전자로 표시").
---

# Seekerizer — watchlist management

Manage the watchlist that the status line renders inline at the bottom of Claude
Code. The watchlist is stored in the plugin's persistent data dir and edited
through `manage.py`.

> If the status line isn't showing yet, the user needs to run the setup skill
> once: `/seekerizer:setup`. Mention this if they ask "why don't
> I see any prices".

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
`NVDA`. If unsure of the exact code, ask the user to confirm before adding.

## Commands

Run with the plugin's bundled script. `add` validates each symbol against the
Yahoo Finance API before saving and prints the resolved company name.

```bash
# Add one or more tickers
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage.py" add AAPL 005930.KS

# Remove tickers
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage.py" remove TSLA

# List the current watchlist (shows any aliases)
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage.py" list

# Clear everything
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage.py" clear

# Set a custom display label (e.g. a Korean name Yahoo doesn't provide)
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage.py" alias 005930.KS 삼성전자

# Drop the custom label (revert to the auto company name)
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage.py" unalias 005930.KS
```

By default the status line shows the **company name** (e.g. `Samsung Electronics`
for `005930.KS`). An `alias` overrides that label — use it when the user wants a
Korean name. `remove` deletes the ticker and also drops its alias; if the symbol
still has a price target it prints a note (targets are managed by `set-target`).

## Workflow

1. Resolve the Yahoo symbol(s) from what the user said (confirm if ambiguous).
2. Run the appropriate `manage.py` command (`add` / `remove` / `alias` / …).
3. Report the result. If `add` printed "Validation failed", the symbol was
   rejected — double-check the code with the user.
4. The status line refreshes on its own; a new quote appears within ~60s (the
   quote cache window). No restart needed.
