#!/usr/bin/env python3
"""Enable (or disable) Claude Code's OpenTelemetry export in settings.json.

Claude Code has OTel support built in; it just needs env vars. Claude Code reads
the `env` block of settings.json at startup, so this script merges telemetro's
OTel keys there (a new session picks them up — restart required).

Usage:
    otel.py install [--project] [--endpoint http://host:4317] [--force]
    otel.py remove  [--project]
    otel.py status  [--project]

    --project   Target ./.claude/settings.json instead of ~/.claude/settings.json
    --endpoint  OTLP endpoint (default http://localhost:4317, gRPC)
    --force     Overwrite managed keys that already exist with different values

Only telemetro's keys are touched; the rest of the settings are preserved.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (  # noqa: E402
    otel_env, MANAGED_KEYS, settings_path, load_json, save_json,
)


def _arg(argv, flag, default=None):
    if flag in argv:
        i = argv.index(flag)
        if i + 1 < len(argv):
            return argv[i + 1]
    return default


def cmd_install(argv):
    scope = "project" if "--project" in argv else "global"
    path = settings_path(scope)
    settings = load_json(path, {})
    env = settings.get("env")
    if not isinstance(env, dict):
        env = {}
    desired = otel_env(_arg(argv, "--endpoint"))

    conflicts = {k: env[k] for k in desired
                 if k in env and env[k] != desired[k]}
    if conflicts and "--force" not in argv:
        print(f"Warning: {path} already sets different values for:")
        for k, v in conflicts.items():
            print(f"  {k} = {v}   (telemetro wants: {desired[k]})")
        print("Re-run with --force to overwrite, or remove them manually. (aborted)")
        return 1

    env.update(desired)
    settings["env"] = env
    save_json(path, settings)
    print(f"Installed: OTel telemetry env in {path}")
    print(f"  endpoint: {desired['OTEL_EXPORTER_OTLP_ENDPOINT']} (gRPC)")
    print("Start a new Claude Code session for telemetry to begin flowing.")
    return 0


def cmd_remove(argv):
    scope = "project" if "--project" in argv else "global"
    path = settings_path(scope)
    settings = load_json(path, {})
    env = settings.get("env")
    if not isinstance(env, dict):
        print("No telemetro telemetry env is configured. No change.")
        return 0
    removed = [k for k in MANAGED_KEYS if env.pop(k, None) is not None]
    if not removed:
        print("No telemetro telemetry env is configured. No change.")
        return 0
    if env:
        settings["env"] = env
    else:
        settings.pop("env", None)
    save_json(path, settings)
    print(f"Removed {len(removed)} telemetry env vars from {path}")
    return 0


def cmd_status(argv):
    scope = "project" if "--project" in argv else "global"
    path = settings_path(scope)
    env = load_json(path, {}).get("env") or {}
    print(f"Settings file: {path}")
    missing = [k for k in MANAGED_KEYS if k not in env]
    if not missing:
        print("Telemetry: ENABLED")
        print(f"  endpoint = {env.get('OTEL_EXPORTER_OTLP_ENDPOINT')}")
    elif len(missing) == len(MANAGED_KEYS):
        print("Telemetry: not configured")
    else:
        print(f"Telemetry: PARTIAL — missing {', '.join(missing)}")
        print("  Re-run otel.py install to fix.")
    return 0


COMMANDS = {"install": cmd_install, "remove": cmd_remove, "status": cmd_status}


def main(argv):
    if not argv or argv[0] not in COMMANDS:
        print(__doc__)
        return 2
    return COMMANDS[argv[0]](argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
