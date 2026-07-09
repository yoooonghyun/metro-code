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
- `diagnose` — "is my harness working as intended?" / "하네스 진단" — see below
- `apply` — "apply proposed changes 1 and 3" / "진단 결과 반영해줘" — apply §6 proposals
- `stop` — "stop monitoring" / "모니터링 꺼줘" — telemetry off + stack down
- `update` — "update telemetro" — latest version

### Diagnose: intent vs. behavior

`/telemetro:diagnose` compares **what the telemetry says actually happened**
against **what your harness configuration says should happen**. `query.py`
digests the collected metrics and log events (token/cost by model, event
counts, `tool_decision` breakdown by decision *and source* —
`config`/`hook`/`user_*` — tool & skill usage, recent API errors); Claude then
reads your CLAUDE.md, permissions, hooks and skills and reports:

- ✅ guardrails that actually fired (`reject` by `config`/`hook`)
- ⚠️ divergences — actions you had to refuse by hand (`user_reject`) → missing
  rule/hook proposals; things you keep approving (`user_temporary`) → allowlist
  candidates; skills your CLAUDE.md mandates but that never ran
- 📉 API error clusters and token/cost outliers

Tool/skill names in events come from `OTEL_LOG_TOOL_DETAILS=1`, which telemetro
now installs (older installs: re-run `otel.py install`).

The report follows a fixed template (`templates/diagnose-report.md`: Verdict →
Working-as-intended → Divergences (rules/skills/subagents/memory) → Health &
cost → **Trend vs. previous diagnosis** → numbered Proposed changes), and every
report is archived under the data dir (`reports/<timestamp>.md`) so the next
diagnosis can tell you which divergences were fixed, persist, or are new.

`/telemetro:apply` then closes the loop: pick §6 proposals (all or by number)
and it applies them — settings/permission entries (with a backup), CLAUDE.md
additions, hook scripts (shown before saving), skill-description fixes — never
broader than proposed, and each applied item is annotated in the report so the
next diagnosis verifies the effect.

**Config epochs.** The harness itself changes over time — even mid-session —
so telemetro bundles hooks (SessionStart + every UserPromptSubmit) that
fingerprint the harness — CLAUDE.md tiers, permissions, the full hooks config,
env keys, and **content hashes** of every declared skill, subagent, and MCP
server spec (editing a skill's SKILL.md or a hook command opens a new epoch,
not just adding/removing one) — and append to `snapshots.jsonl` **only when the
fingerprint changes** (~25ms per prompt, deduplicated; full configs stored once
under `configs/<hash>.json`). Consecutive lines form epochs, and diagnose
attributes each event to the config active at its timestamp — a divergence
that only occurred under an older, since-fixed config is reported as resolved,
not as a current problem.

Or call the scripts directly:

```bash
P="$CLAUDE_PLUGIN_ROOT/scripts"
python3 $P/stack.py up                     # start stack (idempotent; respects existing OTLP listener)
python3 $P/stack.py status
python3 $P/stack.py down [--rm]
python3 $P/otel.py install [--project] [--endpoint http://host:4317] [--force]
python3 $P/otel.py status
python3 $P/otel.py remove
python3 $P/query.py summary [--hours 168] [--grafana http://localhost:3000]
```

## How it works

| File | Role |
|------|------|
| `scripts/common.py` | managed env keys, ports, settings/json helpers, port probe |
| `scripts/otel.py` | merge/remove/report the OTel env block in Claude Code settings |
| `scripts/stack.py` | run/stop the grafana/otel-lgtm container; skip when an OTLP listener exists |
| `scripts/query.py` | digest metrics (Prometheus) + log events (Loki) via Grafana proxies |
| `skills/init,status,diagnose,stop,update` | `/telemetro:*` |

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
