---
name: status
description: >-
  Show Claude Code monitoring status: whether telemetry env is configured and
  whether the Grafana/OTel stack is running. Use for "monitoring status",
  "is telemetry on?", "모니터링 상태", "텔레메트리 켜져있어?".
---

# Telemetro — status

Report both halves of the loop.

## Steps

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/otel.py" status
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stack.py" status
```

Relay the combined picture: telemetry env configured? OTLP listener present?
Container running? Remind that Grafana lives at http://localhost:3000 when the
stack is up, and that /telemetro:init fixes anything missing.
