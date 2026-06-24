---
name: list-symbols
description: >-
  Show the current watchlist (with any aliases) and the price targets. Use for
  "show my watchlist", "list my stocks", "what am I tracking", "what alerts do I
  have" (also Korean: "추적 중인 종목 보여줘", "내 알림 목록 보여줘").
---

# Seekerizer — list watchlist & targets

Show what the user is tracking. Run both commands and summarize the output.

```bash
# Watchlist (shows aliases in parentheses)
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage.py" list

# Price targets (shows armed / fired)
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/targets.py" list
```

If the user only asked about one of them (just the watchlist, or just alerts),
run only that command.
