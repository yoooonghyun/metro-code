# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

`metro-code` is a **Claude Code plugin marketplace** and a playground for small
experiments built with Claude Code on the web (often from a phone). Each
experiment that proves useful becomes an installable plugin under `plugins/`.

Top-level structure:
- `.claude-plugin/marketplace.json` — the marketplace catalog. Every plugin must
  be listed here with a `name` and a `source` (relative path like
  `./plugins/<name>`).
- `plugins/<name>/` — one self-contained plugin per directory.

End users install via: `/plugin marketplace add yoooonghyun/metro-code` then
`/plugin install <name>@metro-code`. **Relative `source` paths only resolve when
the marketplace is added over Git** (GitHub), not via a direct URL to
`marketplace.json`.

## Plugin anatomy (see `plugins/seekerizer`)

A plugin is `.claude-plugin/plugin.json` (manifest) plus component dirs at the
plugin root: `skills/<skill>/SKILL.md`, `scripts/`, `README.md`. Skills invoke
bundled scripts through the `${CLAUDE_PLUGIN_ROOT}` env var (e.g.
`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage.py" add AAPL`).

### Two non-obvious constraints that shape the design

1. **A plugin cannot register the top-level `statusLine`.** A plugin's bundled
   `settings.json` only honors `agent` and `subagentStatusLine`. So enabling a
   custom status line requires writing into the *user's* settings. `seekerizer`
   does this through the `setup` skill → `scripts/setup.py`, which merges a
   `statusLine` entry into `~/.claude/settings.json` (or `.claude/settings.json`
   with `--project`). It refuses to overwrite a pre-existing different status
   line. `setup.py` writes an **absolute** script path, so setup must be re-run
   after a plugin update (the cache path changes).

2. **User state must not live in the plugin directory.** `${CLAUDE_PLUGIN_ROOT}`
   changes on every update, which would wipe data. `scripts/common.py` resolves
   the data dir in this order: `$SEEKERIZER_DATA_DIR` → `$CLAUDE_PLUGIN_DATA` →
   `~/.claude/seekerizer`. The watchlist (`tickers.json`) and quote cache
   (`cache.json`) live there and survive updates.

3. **There is exactly one quote fetcher.** All quotes go through
   `common.get_quotes()`, backed by a single per-symbol cache (`cache.json`,
   60s TTL). `statusline.py` and `monitor.py` both call it, so a symbol is
   fetched at most once per TTL across both — never add a separate API call /
   poll loop in either; extend `get_quotes()` instead.

`seekerizer` data flow:
- `statusline.py` (the status line command) reads the watchlist + targets via
  `common.py`, gets quotes through the shared `get_quotes()`, prints one line,
  and shows a 🔔 next to any symbol whose target is touched.
- `monitor.py` is the plugin's background **monitor** (registered under
  `experimental.monitors` in `plugin.json`; Claude Code runs it as a persistent
  per-session process). It polls the watchlist∪targets via the same
  `get_quotes()` (keeping the cache warm for the status line), and when a target
  is touched prints an alert line — each stdout line reaches Claude as a
  notification. A touched target is marked `fired` (one-shot) until re-set.
- `manage.py` edits the watchlist; `targets.py` edits price targets
  (`targets.json`), auto-detecting direction (above/below) from the current
  price. Both validate symbols against Yahoo before saving.

Symbols use Yahoo notation (`AAPL`, `005930.KS` for KOSPI, `BTC-USD`, etc.).
Monitors are **experimental** and only run while a session is open (no alerts
when Claude Code is closed).

## Local development & testing

There is no build/lint/test framework — scripts are Python **stdlib only**
(no dependencies, no API key). Test a plugin by simulating the Claude Code
runtime environment with the env vars it would set:

```bash
# Isolate state in a temp dir so you don't touch ~/.claude
export SEEKERIZER_DATA_DIR="$(mktemp -d)"
P=plugins/seekerizer/scripts

python3 $P/manage.py add AAPL 005930.KS   # add (validates via Yahoo)
python3 $P/manage.py list
python3 $P/statusline.py < /dev/null      # render the status line (stdin is drained)

# Exercise setup against an isolated HOME so real settings are untouched
HOME="$(mktemp -d)" python3 $P/setup.py --status-only
```

Validate manifests before pushing (invalid JSON means the plugin/marketplace
won't load):

```bash
python3 -c "import json; json.load(open('.claude-plugin/marketplace.json'))"
python3 -c "import json; json.load(open('plugins/seekerizer/.claude-plugin/plugin.json'))"
```

## Conventions

- **Renaming a plugin touches many places** — keep them in sync: the
  `plugins/<name>/` dir, `marketplace.json` (`name` + `source`), `plugin.json`
  (`name` + `displayName`), command namespaces in skills/docs
  (`/<name>:<skill>`), the data-dir fallback and `$<NAME>_DATA_DIR` env var in
  `common.py`, and the `is_ours` substring check in `setup.py`.
- **Docs, comments, and runtime messages are English.** Korean is kept *only*
  as functional skill trigger examples and company-name → symbol mappings, so
  skills still match Korean requests.
- Skills are named without redundant prefixes (the plugin name already
  namespaces them): `/seekerizer:add-symbol`, not `/seekerizer:seekerizer-*`.
