#!/usr/bin/env python3
"""Pull a usage digest out of the telemetro stack for harness diagnosis.

Queries the Grafana datasource proxies (Prometheus for metrics, Loki for log
events) and prints a markdown digest of what Claude Code actually did: tokens
and cost, sessions, event counts, permission decisions (and who made them —
config, hook, or the user), tool/skill usage, and recent API errors. The
`diagnose` skill feeds this to Claude to compare against the project's harness
configuration (CLAUDE.md, hooks, permissions, skills).

Usage:
    query.py summary [--hours N] [--grafana http://localhost:3000] [--limit N]

Defaults: last 168h (7 days), Grafana at localhost:3000 (the telemetro stack),
up to 5000 log events scanned.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import GRAFANA_PORT  # noqa: E402

DEFAULT_GRAFANA = f"http://localhost:{GRAFANA_PORT}"


def _get(url, timeout=15):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def _arg(argv, flag, default):
    if flag in argv:
        i = argv.index(flag)
        if i + 1 < len(argv):
            return argv[i + 1]
    return default


# --- Prometheus (metrics) ----------------------------------------------------

def prom_query(grafana, promql):
    url = (f"{grafana}/api/datasources/proxy/uid/prometheus/api/v1/query?"
           + urllib.parse.urlencode({"query": promql}))
    data = _get(url)
    if data.get("status") != "success":
        return []
    return data["data"].get("result", [])


def claude_metric_names(grafana):
    url = f"{grafana}/api/datasources/proxy/uid/prometheus/api/v1/label/__name__/values"
    data = _get(url)
    names = data.get("data", []) if data.get("status") == "success" else []
    return sorted(n for n in names if n.startswith("claude_code"))


def metrics_digest(grafana, hours):
    lines = []
    names = claude_metric_names(grafana)
    if not names:
        return ["(no claude_code metrics found — has a session run with telemetry on?)"]
    for name in names:
        # Counters: total increase over the window, with a per-label breakdown
        # for the interesting ones.
        by = ""
        if "token" in name:
            by = " by (type, model)"
        elif "decision" in name:
            by = " by (decision, language)"
        results = prom_query(grafana, f"sum{by}(increase({name}[{hours}h]))")
        if not results:
            continue
        if len(results) == 1 and not results[0].get("metric"):
            lines.append(f"- {name}: {float(results[0]['value'][1]):,.2f}")
        else:
            lines.append(f"- {name}:")
            for r in sorted(results, key=lambda r: -float(r["value"][1]))[:12]:
                labels = ", ".join(f"{k}={v}" for k, v in sorted(r["metric"].items())
                                   if k != "__name__")
                lines.append(f"    - {labels}: {float(r['value'][1]):,.2f}")
    return lines or ["(claude_code metrics present but empty in this window)"]


# --- Loki (log events) -------------------------------------------------------

def loki_events(grafana, hours, limit):
    """Fetch raw Claude Code log lines and parse them into event dicts."""
    end = int(time.time() * 1e9)
    start = end - int(hours * 3600 * 1e9)
    url = (f"{grafana}/api/datasources/proxy/uid/loki/loki/api/v1/query_range?"
           + urllib.parse.urlencode({
               "query": '{service_name=~".*claude.*"}',
               "start": start, "end": end, "limit": limit,
               "direction": "backward",
           }))
    data = _get(url)
    events = []
    for stream in data.get("data", {}).get("result", []):
        stream_labels = stream.get("stream", {})
        for _, line in stream.get("values", []):
            ev = dict(stream_labels)
            try:
                body = json.loads(line)
                if isinstance(body, dict):
                    ev.update(body)
            except ValueError:
                ev["body"] = line
            events.append(ev)
    return events


def _field(ev, *keys):
    for k in keys:
        if k in ev:
            return str(ev[k])
    return None


def _count(counter, key):
    counter[key] = counter.get(key, 0) + 1


def events_digest(events):
    if not events:
        return ["(no claude_code log events found in this window)"]
    by_name, decisions, tools, errors = {}, {}, {}, []
    for ev in events:
        name = _field(ev, "event.name", "event_name", "name") or "(unknown)"
        _count(by_name, name)
        if "tool_decision" in name:
            decision = _field(ev, "decision") or "?"
            source = _field(ev, "source") or "?"
            _count(decisions, f"{decision} ({source})")
            tool = _field(ev, "tool_name", "tool")
            if tool and (decision != "accept" or source != "config"):
                _count(tools, f"{decision}:{tool}")
        elif "tool_result" in name:
            tool = _field(ev, "tool_name", "tool")
            if tool:
                _count(tools, f"used:{tool}")
        elif "api_error" in name and len(errors) < 5:
            errors.append(_field(ev, "error", "message", "body") or "(no detail)")

    def top(counter, n=15):
        return sorted(counter.items(), key=lambda kv: -kv[1])[:n]

    lines = [f"- events scanned: {len(events)}"]
    lines.append("- by event name:")
    lines += [f"    - {k}: {v}" for k, v in top(by_name)]
    if decisions:
        lines.append("- tool_decision breakdown (decision (source)):")
        lines += [f"    - {k}: {v}" for k, v in top(decisions)]
    if tools:
        lines.append("- tool usage / non-default decisions (top):")
        lines += [f"    - {k}: {v}" for k, v in top(tools)]
    if errors:
        lines.append("- recent api_error samples:")
        lines += [f"    - {e[:200]}" for e in errors]
    return lines


# --- entry -------------------------------------------------------------------

def cmd_summary(argv):
    grafana = _arg(argv, "--grafana", DEFAULT_GRAFANA).rstrip("/")
    hours = int(_arg(argv, "--hours", "168"))
    limit = int(_arg(argv, "--limit", "5000"))

    print(f"# Claude Code usage digest — last {hours}h")
    print(f"(source: {grafana}, Prometheus + Loki via Grafana proxies)\n")
    try:
        print("## Metrics")
        for line in metrics_digest(grafana, hours):
            print(line)
        print("\n## Log events")
        for line in events_digest(loki_events(grafana, hours, limit)):
            print(line)
    except OSError as e:
        print(f"\nCannot reach the monitoring stack at {grafana}: {e}")
        print("Start it with /telemetro:init (stack.py up), then retry.")
        return 1
    return 0


def main(argv):
    if not argv or argv[0] != "summary":
        print(__doc__)
        return 2
    return cmd_summary(argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
