# metro-code — Claude Code plugin marketplace

A [Claude Code plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces).
Anyone can add this repo as a marketplace and install the plugins below into
their own Claude Code.

## Install

In Claude Code:

```text
/plugin marketplace add yoooonghyun/metro-code
/plugin install stock-alerts@metro-code
```

Then run the one-time setup so the status line shows up:

```text
/stock-alerts:setup
```

Start a new session and you'll see live quotes at the bottom of Claude Code.

## Plugins

### `stock-alerts` — inline stock price ticker

Shows your watchlist inline in the Claude Code status line, and lets you manage
it in natural language. Quotes come from the Yahoo Finance public API — **no API
key required**. Supports US, Korean (KOSPI/KOSDAQ), and other markets, plus
crypto.

```
📈 AAPL $294.30 ▼0.91%  │  TSLA $381.61 ▼5.79%  │  005930.KS ₩310,000 ▼12.31%
```

- **Add/remove stocks by talking to Claude**: "삼성전자 추가해줘",
  "테슬라 빼줘", "추적 중인 종목 보여줘", "add NVDA".
- Watchlist persists across plugin updates.

See [`plugins/stock-alerts/README.md`](plugins/stock-alerts/README.md) for
details.

## Repository layout

```
metro-code/
├── .claude-plugin/
│   └── marketplace.json          # marketplace catalog
└── plugins/
    └── stock-alerts/             # the plugin
        ├── .claude-plugin/plugin.json
        ├── scripts/              # python (stdlib only)
        ├── skills/
        │   ├── add-symbol/   # manage watchlist (/stock-alerts:add-symbol)
        │   └── setup/    # one-time status line install (/stock-alerts:setup)
        └── README.md
```
