# seekerizer

Inline stock price ticker for the Claude Code **status line**, with skill-based
watchlist management and **price-target alerts**. Quotes from the Yahoo Finance
public API — **no API key**.

```
📈 Apple $294.30 ▼0.91%  │  Tesla $381.61 ▼5.79%  │  Samsung Electronics ₩310,000 ▼12.31%
```

## Install

```text
/plugin marketplace add yoooonghyun/metro-code
/plugin install seekerizer@metro-code
/seekerizer:setup
```

The setup step is required once: a plugin cannot register the top-level
`statusLine` on its own, so the setup skill writes it into your
`~/.claude/settings.json` (existing settings are preserved). Start a new session
afterward.

## Usage

Talk to Claude (English or Korean):

- `add-symbol` skill — "add NVDA to my watchlist" / "삼성전자 종목 추가해줘",
  "remove TSLA" / "테슬라 빼줘", "show my watchlist" / "추적 중인 종목 보여줘"
- `set-target` skill — "alert me when AAPL hits $300" /
  "AAPL 목표가 300달러로 알림", "list my alerts", "remove the Tesla target"

Or call the scripts directly:

```bash
python3 "$CLAUDE_PLUGIN_ROOT/scripts/manage.py" add AAPL 005930.KS
python3 "$CLAUDE_PLUGIN_ROOT/scripts/manage.py" remove TSLA
python3 "$CLAUDE_PLUGIN_ROOT/scripts/manage.py" list
python3 "$CLAUDE_PLUGIN_ROOT/scripts/manage.py" clear
```

### Symbol format (Yahoo Finance notation)

| Market    | Example                |
|-----------|------------------------|
| US stock  | `AAPL`, `TSLA`, `NVDA` |
| KOSPI     | `005930.KS` (Samsung)  |
| KOSDAQ    | `035720.KQ`            |
| Crypto    | `BTC-USD`              |
| Tokyo     | `7203.T`               |

## How it works

| File | Role |
|------|------|
| `scripts/common.py` | paths, watchlist/targets state, and the single quote fetch + shared cache |
| `scripts/statusline.py` | status line command: render quotes, 🔔 on touched targets |
| `scripts/monitor.py` | background monitor: poll targets, alert when touched |
| `scripts/manage.py` | watchlist add/remove/list/clear, validates symbols |
| `scripts/targets.py` | price targets set/list/remove/clear |
| `scripts/setup.py` | install/remove the status line in your settings |
| `skills/add-symbol/` | watchlist management (`/seekerizer:add-symbol`) |
| `skills/set-target/` | price-target alerts (`/seekerizer:set-target`) |
| `skills/setup/` | one-time status line setup (`/seekerizer:setup`) |

- **Data location**: the watchlist (`tickers.json`), price targets
  (`targets.json`), and quote cache (`cache.json`) live in the plugin's
  persistent data dir (`$CLAUDE_PLUGIN_DATA`, falling back to
  `~/.claude/seekerizer`), so they **survive plugin updates**. Override with
  `$SEEKERIZER_DATA_DIR`.
- **One quote fetcher, no duplicate calls**: all quotes go through
  `common.get_quotes()`, backed by a single per-symbol cache (60s TTL). The
  background monitor keeps the cache warm and the status line reuses it — a
  symbol is fetched at most once per TTL across both.
- **Currency**: `.KS`/`.KQ` → ₩, `.T` → ¥, `.L` → £, `.HK` → HK$, else $.
- **Colors**: gains are shown red and losses blue (Korean market convention).
- **Labels**: the status line shows the company name (e.g. `Samsung Electronics`
  for `005930.KS`) instead of the raw symbol, since Korean tickers are numeric.
  The name comes from the same quote fetch (no extra API call) and corporate
  suffixes like "Co., Ltd."/"Inc." are trimmed.

## Price-target alerts

Set a target with the `set-target` skill (or `targets.py set AAPL 300`).
Direction is auto-detected from the current price: a target **above** alerts
when the price rises to touch it, **below** when it falls to it. When touched,
the `price-targets` background monitor prints an alert that Claude surfaces in
the conversation, and the status line shows a 🔔 next to the symbol. A target
fires once, then re-arms when you set it again.

> Alerts are an **experimental** plugin monitor and only run while a Claude Code
> session is open — there are no alerts when Claude Code is closed.

## After a plugin update

The watchlist persists, but the plugin's script path changes, so re-run setup
once:

```text
/seekerizer:setup
```

## Requirements

- `python3` (standard library only — nothing to install)
- Internet access for quote lookups
