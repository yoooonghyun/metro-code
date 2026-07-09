#!/usr/bin/env python3
"""Enumerate the intent side of the harness for /telemetro:diagnose.

Prints a markdown inventory of what the harness *declares*: installed skills,
subagents, MCP servers (flagging memory-type ones), and memory files
(CLAUDE.md tiers with size/staleness). The diagnose skill pairs this with
query.py's usage digest to find declared-but-never-used pieces and
used-but-undeclared behavior.

Usage:
    inventory.py [--project DIR]     # default: current directory
"""
import glob
import hashlib
import json
import os
import re
import sys
import time


def _name_from_skill_md(path):
    try:
        with open(path, encoding="utf-8") as f:
            head = f.read(2048)
        m = re.search(r"^name:\s*(\S+)", head, re.M)
        return m.group(1) if m else os.path.basename(os.path.dirname(path))
    except OSError:
        return os.path.basename(os.path.dirname(path))


def find_skills(project):
    """{skill name: {origin, path}} across project, user, and plugin scopes."""
    out = {}
    roots = [
        (os.path.join(project, ".claude", "skills"), "project"),
        (os.path.expanduser("~/.claude/skills"), "user"),
    ]
    for base, origin in roots:
        for p in glob.glob(os.path.join(base, "*", "SKILL.md")):
            out.setdefault(_name_from_skill_md(p), {"origin": origin, "path": p})
    for p in glob.glob(os.path.expanduser(
            "~/.claude/plugins/**/skills/*/SKILL.md"), recursive=True):
        plugin = "plugin"
        m = re.search(r"/plugins/(?:cache/)?(?:[^/]+/)?([^/@]+)[^/]*/skills/", p)
        if m:
            plugin = f"plugin:{m.group(1)}"
        out.setdefault(_name_from_skill_md(p), {"origin": plugin, "path": p})
    return out


def find_agents(project):
    """{agent name: {origin, path}} from project/user dirs and plugin caches."""
    out = {}
    roots = [
        (os.path.join(project, ".claude", "agents"), "project"),
        (os.path.expanduser("~/.claude/agents"), "user"),
    ]
    for base, origin in roots:
        for p in glob.glob(os.path.join(base, "*.md")):
            out.setdefault(os.path.splitext(os.path.basename(p))[0],
                           {"origin": origin, "path": p})
    for p in glob.glob(os.path.expanduser(
            "~/.claude/plugins/**/agents/*.md"), recursive=True):
        out.setdefault(os.path.splitext(os.path.basename(p))[0],
                       {"origin": "plugin", "path": p})
    return out


def _collect_mcp_servers(obj, found):
    """Recursively collect mcpServers maps from a parsed JSON structure."""
    if isinstance(obj, dict):
        servers = obj.get("mcpServers")
        if isinstance(servers, dict):
            for name, spec in servers.items():
                kind = "unknown"
                if isinstance(spec, dict):
                    kind = spec.get("type") or ("stdio" if spec.get("command")
                                                else "remote" if spec.get("url")
                                                else "unknown")
                sha = hashlib.sha256(json.dumps(
                    spec, sort_keys=True, default=str).encode()).hexdigest()[:16]
                found.setdefault(name, {"kind": kind, "sha": sha})
        for v in obj.values():
            _collect_mcp_servers(v, found)
    elif isinstance(obj, list):
        for v in obj:
            _collect_mcp_servers(v, found)


def find_mcp_servers(project):
    found = {}
    for path in (os.path.join(project, ".mcp.json"),
                 os.path.expanduser("~/.claude.json")):
        try:
            with open(path, encoding="utf-8") as f:
                _collect_mcp_servers(json.load(f), found)
        except (OSError, ValueError):
            continue
    return found


MEMORY_HINT = re.compile(r"memor|knowledge|recall|remember", re.I)


def memory_files(project):
    """CLAUDE.md tiers with size and staleness."""
    out = []
    for path, tier in (
        (os.path.join(project, "CLAUDE.md"), "project"),
        (os.path.join(project, "CLAUDE.local.md"), "project-local"),
        (os.path.join(project, ".claude", "CLAUDE.md"), "project(.claude)"),
        (os.path.expanduser("~/.claude/CLAUDE.md"), "user"),
    ):
        try:
            st = os.stat(path)
        except OSError:
            continue
        age_days = max(0, int((time.time() - st.st_mtime) / 86400))
        out.append((tier, path, st.st_size, age_days))
    return out


def main(argv):
    project = os.path.abspath(
        argv[argv.index("--project") + 1] if "--project" in argv else ".")
    print(f"# Harness inventory — {project}\n")

    skills = find_skills(project)
    print(f"## Skills declared ({len(skills)})")
    for name, info in sorted(skills.items()):
        print(f"- {name}  [{info['origin']}]")
    if not skills:
        print("(none found)")

    agents = find_agents(project)
    print(f"\n## Subagents declared ({len(agents)})")
    for name, info in sorted(agents.items()):
        print(f"- {name}  [{info['origin']}]")
    if not agents:
        print("(none found)")

    mcp = find_mcp_servers(project)
    print(f"\n## MCP servers configured ({len(mcp)})")
    for name, info in sorted(mcp.items()):
        tag = "  ← memory-type" if MEMORY_HINT.search(name) else ""
        print(f"- {name} ({info['kind']}){tag}")
    if not mcp:
        print("(none found)")

    mems = memory_files(project)
    print(f"\n## Memory files ({len(mems)})")
    for tier, path, size, age in mems:
        stale = "  ⚠ stale (>30d untouched)" if age > 30 else ""
        print(f"- [{tier}] {path} — {size:,}B, modified {age}d ago{stale}")
    if not mems:
        print("(no CLAUDE.md at any tier)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
