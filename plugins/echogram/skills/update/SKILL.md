---
name: update
description: >-
  Update the echogram plugin to the latest version from the metro-code
  marketplace. Use for "update echogram", "get the latest version",
  "회의록 플러그인 업데이트", "echogram 업데이트해줘", "최신 버전으로".
---

# Echogram — update the plugin

Pull the newest echogram from the marketplace. Your config and recorded meetings
live in the persistent data dir and survive the update (nothing to re-point —
echogram stores no absolute paths in your settings).

## Steps

1. Refresh the marketplace catalog (git-pulls the latest from GitHub):

   ```bash
   claude plugin marketplace update metro-code
   ```

2. Update the installed plugin to the new version:

   ```bash
   claude plugin update echogram@metro-code
   ```

   If that subcommand isn't available in this Claude Code version, use the
   interactive menu instead: `/plugin` → **Installed** → echogram → update.
   Tell the user which to use based on the command's output.

3. Tell the user to **start a new Claude Code session** so the new version loads.

## Notes

- Report each command's output. If `claude plugin marketplace update` shows no
  change, the plugin is already at the latest version.
- Updates never touch your data (`config.json`, `meetings/`) in the data dir.
