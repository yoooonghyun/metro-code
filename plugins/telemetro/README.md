# telemetro

Monitor your **Claude Code usage** on a local Grafana dashboard. telemetro wires
Claude Code's built-in **OpenTelemetry** export into your settings and, if no
monitoring tool is running, spins up the all-in-one **grafana/otel-lgtm**
container (OTLP collector + Prometheus + Loki + Tempo + Grafana) to receive it.

```text
/telemetro:init
→ starts Grafana stack (unless an OTLP listener already exists)
→ enables OTel export in ~/.claude/settings.json
→ restart Claude Code → http://localhost:3000
```

What you get on the dashboard: token usage, cost, session counts, lines of
code, commits/PRs, tool events, API errors — everything Claude Code emits over
OTLP. All local; nothing leaves your machine.

## Install

```text
/plugin marketplace add yoooonghyun/metro-code
/plugin install telemetro@metro-code
/telemetro:init
```

## Requirements

- `python3` (standard library only)
- **Docker** (or Podman) for the local stack — skipped entirely if you already
  run an OTLP collector on 4317/4318 (telemetro then just points Claude Code at
  it)

## Usage

- `init` — "set up monitoring" / "모니터링 설정" — stack up + telemetry on
- `status` — "is telemetry on?" / "모니터링 상태"
- `stop` — "stop monitoring" / "모니터링 꺼줘" — telemetry off + stack down
- `update` — "update telemetro" — latest version

Or call the scripts directly:

```bash
P="$CLAUDE_PLUGIN_ROOT/scripts"
python3 $P/stack.py up                     # start stack (idempotent; respects existing OTLP listener)
python3 $P/stack.py status
python3 $P/stack.py down [--rm]
python3 $P/otel.py install [--project] [--endpoint http://host:4317] [--force]
python3 $P/otel.py status
python3 $P/otel.py remove
```

## How it works

| File | Role |
|------|------|
| `scripts/common.py` | managed env keys, ports, settings/json helpers, port probe |
| `scripts/otel.py` | merge/remove/report the OTel env block in Claude Code settings |
| `scripts/stack.py` | run/stop the grafana/otel-lgtm container; skip when an OTLP listener exists |
| `skills/init,status,stop,update` | `/telemetro:*` |

- **Claude Code reads env at startup** — after `init` (or `stop`) a new session
  is needed for the change to take effect.
- The env block managed in settings:
  `CLAUDE_CODE_ENABLE_TELEMETRY=1`, `OTEL_METRICS_EXPORTER=otlp`,
  `OTEL_LOGS_EXPORTER=otlp`, `OTEL_EXPORTER_OTLP_PROTOCOL=grpc`,
  `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317`, plus 10s/5s export
  intervals. Only these keys are touched; conflicting pre-existing values abort
  unless `--force`.
- **Existing monitoring is respected**: `stack.py up` probes 4317/4318 first and
  starts nothing if a listener is already there.
- Container: `telemetro-grafana`, ports 3000 (Grafana UI), 4317 (OTLP gRPC),
  4318 (OTLP HTTP). `down` stops but keeps it (metrics history lives inside);
  `down --rm` deletes.

## Tests

Offline suite (docker and sockets mocked):

```bash
python3 plugins/telemetro/tests/test_telemetro.py
```
