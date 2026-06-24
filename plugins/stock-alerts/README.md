# stock-alerts

Inline stock price ticker for the Claude Code **status line**, with skill-based
watchlist management. Quotes from the Yahoo Finance public API — **no API key**.

```
📈 AAPL $294.30 ▼0.91%  │  TSLA $381.61 ▼5.79%  │  005930.KS ₩310,000 ▼12.31%
```

## Install

```text
/plugin marketplace add yoooonghyun/metro-code
/plugin install stock-alerts@metro-code
/stock-alerts:setup
```

The setup step is required once: a plugin cannot register the top-level
`statusLine` on its own, so the setup skill writes it into your
`~/.claude/settings.json` (existing settings are preserved). Start a new session
afterward.

## Usage

Talk to Claude — the `stock-alerts` skill handles it:

- "삼성전자 종목 추가해줘" / "add NVDA to my watchlist"
- "테슬라 빼줘" / "remove TSLA"
- "추적 중인 종목 보여줘" / "show my watchlist"

Or call the scripts directly:

```bash
python3 "$CLAUDE_PLUGIN_ROOT/scripts/stock_manage.py" add AAPL 005930.KS
python3 "$CLAUDE_PLUGIN_ROOT/scripts/stock_manage.py" remove TSLA
python3 "$CLAUDE_PLUGIN_ROOT/scripts/stock_manage.py" list
python3 "$CLAUDE_PLUGIN_ROOT/scripts/stock_manage.py" clear
```

### Symbol format (Yahoo Finance notation)

| Market    | Example                |
|-----------|------------------------|
| 미국 주식 | `AAPL`, `TSLA`, `NVDA` |
| 코스피    | `005930.KS` (삼성전자) |
| 코스닥    | `035720.KQ`            |
| 암호화폐  | `BTC-USD`              |
| 도쿄      | `7203.T`               |

## How it works

| File | Role |
|------|------|
| `scripts/stock_statusline.py` | status line command: fetch + render (60s cache) |
| `scripts/stock_manage.py` | add/remove/list/clear, validates symbols |
| `scripts/setup.py` | install/remove the status line in your settings |
| `scripts/_common.py` | shared paths/helpers |
| `skills/add-stock/` | natural-language watchlist management (`/stock-alerts:add-stock`) |
| `skills/setup/` | one-time status line setup (`/stock-alerts:setup`) |

- **Data location**: the watchlist (`tickers.json`) and quote cache
  (`cache.json`) live in the plugin's persistent data dir
  (`$CLAUDE_PLUGIN_DATA`, falling back to `~/.claude/stock-alerts`), so they
  **survive plugin updates**. Override with `$STOCK_ALERTS_DATA_DIR`.
- **Quotes**: Yahoo Finance chart API, cached 60s to keep the status line fast.
- **Currency**: `.KS`/`.KQ` → ₩, `.T` → ¥, `.L` → £, `.HK` → HK$, else $.

## After a plugin update

The watchlist persists, but the plugin's script path changes, so re-run setup
once:

```text
/stock-alerts:setup
```

## Requirements

- `python3` (standard library only — nothing to install)
- Internet access for quote lookups
