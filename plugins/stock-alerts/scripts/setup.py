#!/usr/bin/env python3
"""Install (or remove) the stock-alerts status line in a Claude Code settings file.

The plugin already bundles a settings.json with a `statusLine` entry, but a
plugin cannot force the top-level status line — if a user already has their own
status line, or it isn't taking effect, this writes the entry directly into
their settings so it reliably shows up.

Usage:
    setup.py [--global | --project] [--remove] [--status-only]

    --global       Target ~/.claude/settings.json  (default)
    --project      Target ./.claude/settings.json  (current repo only)
    --remove       Remove the stock-alerts status line again
    --status-only  Don't install; just report current state

Existing settings are preserved (merged); only the `statusLine` key is touched.
"""
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATUSLINE_SCRIPT = os.path.join(SCRIPT_DIR, "stock_statusline.py")


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
        and "stock_statusline.py" in str(statusline.get("command", ""))
    )


def main(argv):
    scope = "project" if "--project" in argv else "global"
    path = target_path(scope)
    settings = load_settings(path)
    current = settings.get("statusLine")

    if "--status-only" in argv:
        print(f"설정 파일: {path}")
        if current is None:
            print("statusLine: (없음)")
        elif is_ours(current):
            print("statusLine: stock-alerts (설치됨)")
        else:
            print(f"statusLine: 다른 항목이 설정되어 있음 -> {json.dumps(current, ensure_ascii=False)}")
        return 0

    if "--remove" in argv:
        if is_ours(current):
            del settings["statusLine"]
            save_settings(path, settings)
            print(f"제거됨: {path} 의 stock-alerts status line")
        else:
            print("stock-alerts status line이 설정되어 있지 않습니다. 변경 없음.")
        return 0

    # Install.
    if current is not None and not is_ours(current):
        print(f"경고: {path} 에 이미 다른 statusLine이 있습니다:")
        print(f"  {json.dumps(current, ensure_ascii=False)}")
        print("덮어쓰려면 먼저 해당 설정을 확인하세요. (중단)")
        return 1

    settings["statusLine"] = {
        "type": "command",
        "command": f'python3 "{STATUSLINE_SCRIPT}"',
        "padding": 0,
    }
    save_settings(path, settings)
    print(f"설치 완료: {path}")
    print(f"  statusLine -> python3 \"{STATUSLINE_SCRIPT}\"")
    print("새 세션을 시작하면 하단에 시세가 표시됩니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
