# metro-code

## Repository overview

`metro-code` is a personal playground for building software **on the go** —
specifically during subway commutes — using [Claude Code on the
web](https://code.claude.com/docs/en/claude-code-on-the-web) from a phone.
Everything here is meant to be developed, reviewed, and shipped without a
laptop: short, self-contained experiments that fit a commute. The name is a nod
to coding on the *metro*.

The repo doubles as a **Claude Code plugin marketplace**, so any experiment that
turns into something useful can be installed straight into Claude Code by anyone.

## Use it as a marketplace

In Claude Code:

```text
/plugin marketplace add yoooonghyun/metro-code
/plugin install seekerizer@metro-code
```

Then run the plugin's one-time setup:

```text
/seekerizer:setup
```

Start a new session and you'll see live stock quotes at the bottom of Claude
Code.

## Plugins

### `seekerizer` — inline stock price ticker

Shows your watchlist inline in the Claude Code status line, lets you manage it
in natural language, and alerts you when a stock touches a target price. Quotes
come from the Yahoo Finance public API — **no API key required**. Supports US,
Korean (KOSPI/KOSDAQ), Tokyo, and other markets, plus crypto.

```
📈 Apple $294.30 ▼0.91%  │  🔔 Tesla $381.61 ▼5.79%  │  Samsung Electronics ₩310,000 ▼12.31%
```

- **Manage by talking to Claude** (English or Korean): "add NVDA",
  "remove TSLA", "show my watchlist".
- **Price-target alerts**: "alert me when AAPL hits $300" — a background monitor
  notifies you (and shows 🔔) when the price is touched.
- Watchlist and targets persist across plugin updates.

See [`plugins/seekerizer/README.md`](plugins/seekerizer/README.md) for details.

## Repository layout

```
metro-code/
├── .claude-plugin/
│   └── marketplace.json            # marketplace catalog
└── plugins/
    └── seekerizer/                 # the plugin
        ├── .claude-plugin/plugin.json
        ├── scripts/                # python (stdlib only)
        ├── skills/                 # one skill per action
        │   ├── add-symbol/         # add a stock
        │   ├── remove-symbol/      # remove / clear stocks
        │   ├── alias-symbol/       # custom display label (e.g. Korean)
        │   ├── list-symbols/       # show watchlist & targets
        │   ├── set-target/         # price-target alerts
        │   └── setup/              # one-time status line install
        └── README.md
```

## Conventions

- Plugins live under `plugins/<name>/` and are listed in
  `.claude-plugin/marketplace.json`.
- Scripts use the Python standard library only, so experiments run anywhere
  without an install step.
- Docs and code comments are kept in English.
