---
name: update
description: >-
  Update the telemetro plugin to the latest version from the metro-code
  marketplace. Use for "update telemetro", "telemetro 업데이트",
  "모니터링 플러그인 업데이트".
---

# Telemetro — update the plugin

Pull the newest telemetro from the marketplace. Settings env vars and the
container are untouched by an update.

## Steps

1. ```bash
   claude plugin marketplace update metro-code
   ```
2. ```bash
   claude plugin update telemetro@metro-code
   ```
   If that subcommand isn't available, use the interactive menu: `/plugin` →
   **Installed** → telemetro → update.
3. Tell the user to start a new session so the new version loads.
