---
name: update
description: >-
  Update the seekerizer plugin to the latest version from the metro-code
  marketplace, then re-point the status line. Use when the user wants to update
  / upgrade the plugin — e.g. "update seekerizer", "get the latest version",
  "플러그인 최신 버전으로 업데이트", "seekerizer 업데이트해줘".
---

# Seekerizer — update the plugin

Pull the newest seekerizer from the marketplace and fix up the status line.
A plugin's install path (`${CLAUDE_PLUGIN_ROOT}`) changes on update, so the
absolute path stored in the user's settings must be refreshed afterward. The
watchlist, price targets, and aliases live in the persistent data dir and
survive the update.

## Steps

1. Refresh the marketplace catalog (this git-pulls the latest from GitHub):

   ```bash
   claude plugin marketplace update metro-code
   ```

2. Update the installed plugin to the new version:

   ```bash
   claude plugin update seekerizer@metro-code
   ```

   If that subcommand isn't available in this Claude Code version, the same
   thing is done from the interactive menu: `/plugin` → **Installed** →
   seekerizer → update (or reinstall). Tell the user which to use based on the
   command's output.

3. Re-point the status line to the new plugin path:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" --update
   ```

4. Tell the user to **start a new Claude Code session** so the new version
   loads. After restarting, if the status line is missing or shows a stale path,
   run `/seekerizer:update` (or `/seekerizer:setup`) once more — step 3 then
   writes the new session's plugin path.

## Notes

- Report each command's output. If `claude plugin marketplace update` shows no
  change, the plugin is already at the latest version.
- Don't touch the user's data files; updates never clear the watchlist/targets.
