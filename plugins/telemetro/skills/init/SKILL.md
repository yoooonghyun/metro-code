---
name: init
description: >-
  Set up Claude Code monitoring: start a local Grafana/OTel stack if no
  monitoring tool is running, and enable OpenTelemetry export in settings. Use
  for "set up monitoring", "enable telemetry", "모니터링 설정", "클로드 코드
  모니터링 켜줘", "사용량 대시보드 만들어줘".
---

# Telemetro — init monitoring

One command sets up the whole loop: Claude Code's built-in OTel export → local
OTLP collector → Grafana dashboard.

## Steps

1. Ensure a monitoring stack is available. This checks for an existing OTLP
   listener first — if one is already running (any collector), **no container is
   started** and the existing setup is reused; otherwise it runs the
   `grafana/otel-lgtm` all-in-one container (OTLP collector + Prometheus + Loki +
   Tempo + Grafana):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stack.py" up
   ```

   If it reports no container runtime, help the user install/start Docker, then
   re-run. The first run pulls the image and can take a few minutes.

2. Enable Claude Code's OpenTelemetry export (writes the env block into
   `~/.claude/settings.json`; `--project` targets the repo's settings instead):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/otel.py" install
   ```

   If the user's collector is elsewhere, pass
   `--endpoint http://host:4317`. If it aborts on conflicting existing env
   values, show them to the user and only re-run with `--force` after they
   agree.

3. Tell the user:
   - **Restart Claude Code** (env vars are read at startup — telemetry starts
     flowing from the next session).
   - Open **http://localhost:3000** (Grafana, anonymous login) and explore the
     metrics: token usage, cost, session counts, lines of code, tool events.

## Notes

- Everything is local — telemetry goes to the user's own machine, nowhere else.
- Turn it back off anytime with /telemetro:stop.
