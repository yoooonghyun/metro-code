---
name: stop
description: >-
  Turn Claude Code monitoring off: remove the telemetry env vars and stop the
  local Grafana stack. Use for "stop monitoring", "disable telemetry",
  "모니터링 꺼줘", "텔레메트리 중지".
---

# Telemetro — stop monitoring

Undo what init set up. Ask the user whether they want to stop just the export,
just the stack, or both (default: both).

## Steps

1. Remove the telemetry env vars from settings (takes effect next session):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/otel.py" remove
   ```

2. Stop the local stack (add `--rm` only if the user wants the container gone —
   the collected metrics history lives inside it):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stack.py" down
   ```

Report what was stopped/removed. `/telemetro:init` turns it all back on.
