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
   line. `setup.py` writes an **absolute** script path, so it must be re-pointed
   after a plugin update (the cache path changes) — `setup.py --update` rewrites
   the path wherever our entry is installed (global and/or project), and the
   `update` skill chains marketplace-update → plugin-update → `--update`.

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
  `common.py`, gets quotes through the shared `get_quotes()`, and prints the
  ticker with a 🔔 next to any symbol whose target is touched. Claude Code does
  not cleanly wrap an over-wide status line, so it packs symbols across as many
  rows as needed to fit the terminal width (`$COLUMNS`, set by Claude Code
  v2.1.153+; falls back to the terminal size), measuring visible width with
  ANSI stripped and CJK/emoji counted as 2 columns. It labels each
  entry with the company name (`common.display_name`, suffix-trimmed) rather
  than the raw symbol — Korean tickers are numeric — and colors it red on a gain
  / blue on a loss (Korean convention). The name rides along in `get_quotes()`'s
  cached entry, so there is no extra request for it. Label priority is
  alias → company name → symbol; a user alias (`aliases.json`, e.g. a Korean
  name) is set via `manage.py alias`.
- `manage.py` also handles deletion: `remove` drops a ticker and its alias and
  warns if a price target lingers; `alias`/`unalias` edit `aliases.json`.
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

## Plugin: `echogram` (meeting notes)

Records a meeting locally and turns it into minutes. Flow: `start` → `end`.
- `record.py` spawns **ffmpeg detached** (`start_new_session=True`) so recording
  survives the `start` process exiting; the pid/paths live in `active.json`.
  `stop` finalizes the file with **SIGINT** (ffmpeg's clean shutdown, like `q`),
  escalating to SIGTERM, then writes `meetings/<id>/meta.json`.
- `transcribe.py` runs **whisper.cpp** (`whisper-cli`/`whisper-cpp`, or
  `$WHISPER_BIN`/`$WHISPER_MODEL`) on `audio.wav` → `transcript.txt`.
- **Live mode** (`start --live`) swaps ffmpeg for whisper.cpp's `whisper-stream`,
  which appends recognized text to `transcript.txt` as it goes. `monitor.py`
  (registered under `experimental.monitors`) tails that file and prints new lines
  so the transcript streams into Claude Code in near-real-time; it idles when no
  live meeting is active. `end` skips batch transcription when a live transcript
  already exists.
- The **minutes are written by Claude** (the `end` skill), not a script — same
  "scripts manage state, Claude does the intelligence; no API key" split as
  seekerizer. The local `minutes.md` is always kept.
- Upload destination is chosen once in `setup.py` (`config.json`
  `upload_target`): `local` | `notion` (via Notion MCP under a parent page) |
  `confluence` (REST, `$CONFLUENCE_TOKEN`/`$CONFLUENCE_USER`).
- Same data-dir rule as seekerizer: `$ECHOGRAM_DATA_DIR` → `$CLAUDE_PLUGIN_DATA` →
  `~/.claude/echogram`. Needs a **local mic** — useless in a remote/web session.
- `update` skill = marketplace-update → plugin-update. Simpler than seekerizer's
  (no status line, so no absolute path to re-point).

## Local development & testing

Scripts are Python **stdlib only** (no dependencies, no API key). There is an
offline `unittest` suite (network mocked) — run it before pushing:

```bash
python3 plugins/seekerizer/tests/test_seekerizer.py
```

You can also exercise a plugin by hand by simulating the Claude Code runtime
environment with the env vars it would set:

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
