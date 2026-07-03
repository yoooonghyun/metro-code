"""Shared helpers for the telemetro plugin scripts.

telemetro wires Claude Code's built-in OpenTelemetry support to a local
monitoring stack: `otel.py` writes the OTel env vars into the user's Claude Code
settings, and `stack.py` runs the all-in-one Grafana OTel stack
(grafana/otel-lgtm: OTLP collector + Prometheus + Loki + Tempo + Grafana) in a
container when nothing is already listening for OTLP.

State location resolution (survives plugin updates):
    1. $TELEMETRO_DATA_DIR   (explicit override, e.g. for testing)
    2. $CLAUDE_PLUGIN_DATA   (per-plugin persistent dir, set by Claude Code)
    3. ~/.claude/telemetro   (fallback when run outside a plugin context)
"""
import json
import os
import socket

# The all-in-one Grafana OTel image and the container we manage.
STACK_IMAGE = "grafana/otel-lgtm"
CONTAINER_NAME = "telemetro-grafana"
GRAFANA_PORT = 3000
OTLP_GRPC_PORT = 4317
OTLP_HTTP_PORT = 4318

# The env block telemetro manages inside the user's Claude Code settings.
# CLAUDE_CODE_ENABLE_TELEMETRY turns the built-in OTel support on; the rest
# points it at the local OTLP endpoint with snappy export intervals.
def otel_env(endpoint=None):
    endpoint = endpoint or f"http://localhost:{OTLP_GRPC_PORT}"
    return {
        "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
        "OTEL_METRICS_EXPORTER": "otlp",
        "OTEL_LOGS_EXPORTER": "otlp",
        "OTEL_EXPORTER_OTLP_PROTOCOL": "grpc",
        "OTEL_EXPORTER_OTLP_ENDPOINT": endpoint,
        "OTEL_METRIC_EXPORT_INTERVAL": "10000",
        "OTEL_LOGS_EXPORT_INTERVAL": "5000",
    }


MANAGED_KEYS = tuple(otel_env().keys())


def data_dir():
    base = (
        os.environ.get("TELEMETRO_DATA_DIR")
        or os.environ.get("CLAUDE_PLUGIN_DATA")
        or os.path.expanduser("~/.claude/telemetro")
    )
    os.makedirs(base, exist_ok=True)
    return base


def settings_path(scope="global"):
    if scope == "project":
        return os.path.join(os.getcwd(), ".claude", "settings.json")
    return os.path.expanduser("~/.claude/settings.json")


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else default
    except (OSError, ValueError):
        return default


def save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def port_in_use(port, host="127.0.0.1", timeout=0.5):
    """True if something is listening on host:port (e.g. an OTLP collector)."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False
