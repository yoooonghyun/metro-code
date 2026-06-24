---
name: setup
description: >-
  One-time setup for the stock-alerts plugin: install the stock price status
  line into the user's Claude Code settings. Use right after installing the
  plugin, or when the user says "주식 시세 status line 설정/설치해줘",
  "show stock prices in my status bar", "set up stock-alerts",
  "status line이 안 보여" (status line not showing).
---

# Stock Alerts — setup

Claude Code plugins can't register the top-level `statusLine` on their own, so
this skill writes it into the user's settings once. After this, the inline stock
ticker appears at the bottom of every new session.

## Install (default: global, all projects)

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" --global
```

This adds a `statusLine` entry to `~/.claude/settings.json` pointing at the
plugin's `statusline.py`. Existing settings are preserved (merged); only
the `statusLine` key is added. If the user already has a different status line,
the script stops and reports it instead of overwriting — relay that and ask how
they want to proceed.

To install for the current project only, use `--project` (writes to
`./.claude/settings.json`).

## Verify

```bash
# Show current state
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" --status-only

# Quick render test (prints exactly what the status line will show)
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/statusline.py" < /dev/null
```

## Seed an initial watchlist (optional)

If the watchlist is empty, offer to add a couple of starters:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage.py" add AAPL 005930.KS
```

## Uninstall the status line

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" --remove
```

## After setup

- Tell the user to **start a new session** (or reload) for the status line to
  appear — `statusLine` is read at session start.
- Note that if they later **update the plugin**, the script path changes, so
  they should re-run this setup once. (The watchlist itself persists across
  updates.)
- Day-to-day watchlist changes use the `stock-alerts` skill, not this one.
