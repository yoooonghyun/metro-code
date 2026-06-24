---
name: set-target
description: >-
  Set, list, or remove a price-target alert for a stock — the user gets notified
  when the price touches the target. Use when the user names a target/goal price,
  e.g. "alert me when AAPL hits $300", "set a target of 300 for Apple",
  "remove the Tesla target", "list my alerts" (also matches Korean such as
  "AAPL 목표가 300달러로 알림", "테슬라 목표가 빼줘", "내 알림 목록").
---

# Seekerizer — price-target alerts

Set a target price for a symbol. A background monitor (the plugin's
`price-targets` monitor) polls prices and, when the target is **touched**,
prints an alert that Claude surfaces to the user; the status line also shows a
🔔 next to that symbol.

> The monitor only runs while a Claude Code session is open, and it is an
> experimental plugin feature. There are no alerts when Claude Code is closed.
> If the monitor isn't running, alerts won't fire — but the status line 🔔 still
> works whenever the status line refreshes.

## Commands

`set` fetches the current price and auto-detects the direction when you don't
pass one: a target **above** the current price alerts when the price rises to
it; **below** alerts when it falls to it. Setting a target re-arms it.

```bash
# Set a target (direction auto-detected from the current price)
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/targets.py" set AAPL 300

# Force a direction if needed
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/targets.py" set AAPL 300 above

# List targets (shows armed / fired)
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/targets.py" list

# Remove / clear
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/targets.py" remove TSLA
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/targets.py" clear
```

## Workflow

1. Resolve the Yahoo symbol from what the user said (e.g. 삼성전자 → `005930.KS`;
   confirm if ambiguous). The symbol does not need to be in the watchlist.
2. Run `targets.py set <SYMBOL> <PRICE>` (add a direction only if the user is
   explicit about "above"/"below").
3. Report the stored target and the current price from the command output. If it
   printed "Could not fetch a current price", the symbol was rejected — check it
   with the user.
4. A target fires once, then shows as `fired`. To re-arm, set it again.
