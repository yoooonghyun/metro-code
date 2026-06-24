---
name: remove-symbol
description: >-
  Remove a stock from the status-line watchlist, or clear the whole watchlist.
  Use for "remove TSLA", "delete Apple", "stop tracking 005930.KS", "clear my
  watchlist" (also Korean: "테슬라 빼줘", "삼성전자 삭제해줘", "워치리스트 비워줘").
---

# Seekerizer — remove a symbol

Remove one or more symbols from the watchlist, or clear it entirely. Removing a
symbol also drops its custom alias; if the symbol still has a price target, the
command prints a note (targets are managed by the set-target skill).

## Commands

```bash
# Remove one or more symbols
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage.py" remove TSLA 005930.KS

# Clear the entire watchlist
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage.py" clear
```

## Workflow

1. Resolve the symbol(s) from what the user said (a company/Korean name maps to
   a Yahoo symbol, e.g. 삼성전자 → `005930.KS`).
2. Run `manage.py remove ...` (or `clear` to remove everything).
3. Relay the result, including any "still has a price target" note so the user
   can decide whether to also remove the alert via the set-target skill.
