#!/usr/bin/env python3
"""Hook: record the harness configuration in force, whenever it changes.

The harness itself changes over time — including *within* a session (sessions
routinely run 100+ tasks) — so diagnosing "behavior vs. intent" is only sound
if we know which configuration was active when each event happened. This hook
runs at SessionStart and on every UserPromptSubmit: it fingerprints the harness
(CLAUDE.md tiers, permissions/hooks/env blocks, declared skills/agents/MCP
servers) and appends a line ONLY when the fingerprint differs from the last
recorded one. Consecutive lines therefore form config epochs [ts_i, ts_i+1);
diagnose joins telemetry events to epochs by timestamp (session ids recorded
too, as a secondary key).

Storage (in the telemetro data dir):
    snapshots.jsonl        one line per config CHANGE: ts, session_id, cwd, config_hash
    configs/<hash>.json    full snapshot, deduplicated by content hash

Reads the hook payload JSON from stdin (session_id, cwd, hook_event_name).
Never fails the session: any error exits 0 silently.
"""
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import data_dir, load_json, settings_path  # noqa: E402
from inventory import (  # noqa: E402
    find_skills, find_agents, find_mcp_servers, memory_files,
)


def _file_digest(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except OSError:
        return None


def build_snapshot(project):
    """A compact, deterministic picture of the harness as configured now."""
    snap = {"project": project}

    snap["memory"] = [
        {"tier": tier, "path": path, "size": size, "sha": _file_digest(path)}
        for tier, path, size, _age in memory_files(project)
    ]

    for scope, path in (("user", settings_path("global")),
                        ("project", os.path.join(project, ".claude", "settings.json"))):
        s = load_json(path, {})
        snap[f"settings_{scope}"] = {
            "permissions": s.get("permissions") or {},
            # Full hooks object: a changed hook command must open a new epoch,
            # not just an added/removed event key.
            "hooks": s.get("hooks") or {},
            "env_keys": sorted((s.get("env") or {}).keys()),
        }

    # Content hashes, not just names: editing a skill's SKILL.md, an agent
    # definition, or an MCP server spec changes the harness's behavior and must
    # start a new epoch even though the name list is identical.
    snap["skills"] = {name: _file_digest(info["path"])
                      for name, info in sorted(find_skills(project).items())}
    snap["agents"] = {name: _file_digest(info["path"])
                      for name, info in sorted(find_agents(project).items())}
    snap["mcp_servers"] = {name: info["sha"]
                           for name, info in sorted(find_mcp_servers(project).items())}
    return snap


def config_hash(snap):
    canon = json.dumps(snap, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]


def _last_hash(log_path):
    try:
        with open(log_path, "rb") as f:
            lines = f.read().splitlines()
        if not lines:
            return None
        return json.loads(lines[-1].decode("utf-8")).get("config_hash")
    except (OSError, ValueError):
        return None


def record(payload):
    project = payload.get("cwd") or os.getcwd()
    snap = build_snapshot(project)
    h = config_hash(snap)

    base = data_dir()
    log_path = os.path.join(base, "snapshots.jsonl")
    if _last_hash(log_path) == h:             # unchanged config -> no new epoch
        return None

    cfg_dir = os.path.join(base, "configs")
    os.makedirs(cfg_dir, exist_ok=True)
    cfg_path = os.path.join(cfg_dir, f"{h}.json")
    if not os.path.exists(cfg_path):          # dedupe: store each config once
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False, indent=2)

    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "session_id": payload.get("session_id") or "",
        "event": payload.get("hook_event_name") or "",
        "cwd": project,
        "config_hash": h,
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def main():
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        payload = {}
    try:
        record(payload)
    except Exception:
        pass                                   # never break session start
    return 0


if __name__ == "__main__":
    sys.exit(main())
