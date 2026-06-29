#!/usr/bin/env python3
"""Check scribe's dependencies and choose where finished minutes are uploaded.

The upload destination is picked once here and stored in config.json; the `end`
skill reads it to decide what to do after saving the local minutes.

Usage:
    setup.py                      # show dependency status + current config
    setup.py --target local
    setup.py --target notion     parent_page_id=<id>
    setup.py --target confluence base_url=<url> space_key=<key> parent_page_id=<id>
    setup.py --audio-input :1     # override the ffmpeg input device (optional)

Destinations:
    local       save minutes.md only (always also saved locally)
    notion      Claude creates a page via the Notion MCP under parent_page_id
    confluence  uploaded via Confluence REST (token from $CONFLUENCE_TOKEN,
                user from $CONFLUENCE_USER) to base_url/space_key
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import which, load_config, save_config, UPLOAD_TARGETS  # noqa: E402
from transcribe import find_binary, find_model, find_stream_binary  # noqa: E402


def deps_status():
    ffmpeg = which("ffmpeg")
    binary = find_binary()
    model = find_model()
    stream = find_stream_binary()
    print("Dependencies:")
    print(f"  ffmpeg          {'✓ ' + ffmpeg if ffmpeg else '✗ missing (brew/apt install ffmpeg)'}")
    print(f"  whisper.cpp     {'✓ ' + binary if binary else '✗ missing (brew install whisper-cpp)'}")
    print(f"  whisper model   {'✓ ' + model if model else '✗ none (download a ggml-*.bin model)'}")
    print(f"  whisper-stream  {'✓ ' + stream if stream else '○ optional (live mode; needs SDL2 build)'}")
    return bool(ffmpeg and binary and model)


def print_config(cfg):
    target = cfg.get("upload_target", "local")
    print(f"Upload target: {target}")
    if target == "notion":
        print(f"  notion.parent_page_id = {cfg['notion'].get('parent_page_id') or '(unset)'}")
    elif target == "confluence":
        c = cfg["confluence"]
        print(f"  confluence.base_url       = {c.get('base_url') or '(unset)'}")
        print(f"  confluence.space_key      = {c.get('space_key') or '(unset)'}")
        print(f"  confluence.parent_page_id = {c.get('parent_page_id') or '(unset)'}")
    if cfg.get("audio_input"):
        print(f"  audio_input = {cfg['audio_input']}")


def apply_params(cfg, target, params):
    """Route key=value params into the right config section for `target`."""
    for p in params:
        if "=" not in p:
            continue
        key, val = p.split("=", 1)
        key = key.strip()
        if key in ("base_url", "space_key", "parent_page_id") and target == "confluence":
            cfg["confluence"][key] = val
        elif key == "parent_page_id" and target == "notion":
            cfg["notion"]["parent_page_id"] = val
        elif key == "audio_input":
            cfg["audio_input"] = val


def main(argv):
    cfg = load_config()

    if "--audio-input" in argv:
        i = argv.index("--audio-input")
        if i + 1 < len(argv):
            cfg["audio_input"] = argv[i + 1]
            save_config(cfg)
            print(f"audio_input set to {cfg['audio_input']}")

    if "--target" in argv:
        i = argv.index("--target")
        target = argv[i + 1] if i + 1 < len(argv) else ""
        if target not in UPLOAD_TARGETS:
            print(f"Unknown target '{target}'. Choose one of: {', '.join(UPLOAD_TARGETS)}")
            return 1
        cfg["upload_target"] = target
        apply_params(cfg, target, argv[i + 2:])
        save_config(cfg)
        print(f"Upload target set to: {target}")
        print_config(cfg)
        if target == "notion" and not cfg["notion"].get("parent_page_id"):
            print("Note: set a parent page — setup.py --target notion parent_page_id=<id>")
            print("      and connect the Notion MCP in your Claude Code.")
        if target == "confluence":
            print("Note: export CONFLUENCE_TOKEN and CONFLUENCE_USER for uploads.")
        return 0

    # No action flags: report status.
    ok = deps_status()
    print()
    print_config(cfg)
    if not ok:
        print("\nInstall the missing dependencies above, then re-run /scribe:setup.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
