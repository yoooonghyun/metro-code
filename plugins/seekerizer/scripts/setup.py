#!/usr/bin/env python3
"""Install (or remove) the seekerizer status line in a Claude Code settings file.

A Claude Code plugin cannot register the top-level `statusLine` itself: a
plugin's bundled settings.json only supports the `agent` and
`subagentStatusLine` keys. So this script writes the `statusLine` entry directly
into the user's settings to enable the inline ticker.

Usage:
    setup.py [--global | --project] [--remove] [--status-only]

    --global       Target ~/.claude/settings.json  (default)
    --project      Target ./.claude/settings.json  (current repo only)
    --remove       Remove the seekerizer status line again
    --status-only  Don't install; just report current state

Existing settings are preserved (merged); only the `statusLine` key is touched.
"""
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATUSLINE_SCRIPT = os.path.join(SCRIPT_DIR, "statusline.py")


def target_path(scope):
    if scope == "project":
        return os.path.join(os.getcwd(), ".claude", "settings.json")
    return os.path.expanduser("~/.claude/settings.json")


def load_settings(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_settings(path, settings):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
        f.write("\n")


def is_ours(statusline):
    return (
        isinstance(statusline, dict)
        and "statusline.py" in str(statusline.get("command", ""))
    )


def main(argv):
    scope = "project" if "--project" in argv else "global"
    path = target_path(scope)
    settings = load_settings(path)
    current = settings.get("statusLine")

    if "--status-only" in argv:
        print(f"Settings file: {path}")
        if current is None:
            print("statusLine: (none)")
        elif is_ours(current):
            print("statusLine: seekerizer (installed)")
        else:
            print(f"statusLine: a different entry is set -> {json.dumps(current, ensure_ascii=False)}")
        return 0

    if "--remove" in argv:
        if is_ours(current):
            del settings["statusLine"]
            save_settings(path, settings)
            print(f"Removed: seekerizer status line from {path}")
        else:
            print("No seekerizer status line is configured. No change.")
        return 0

    # Install.
    if current is not None and not is_ours(current):
        print(f"Warning: {path} already has a different statusLine:")
        print(f"  {json.dumps(current, ensure_ascii=False)}")
        print("Review that setting before overwriting. (aborted)")
        return 1

    settings["statusLine"] = {
        "type": "command",
        "command": f'python3 "{STATUSLINE_SCRIPT}"',
        "padding": 0,
    }
    save_settings(path, settings)
    print(f"Installed: {path}")
    print(f"  statusLine -> python3 \"{STATUSLINE_SCRIPT}\"")
    print("Start a new session to see quotes at the bottom of Claude Code.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
