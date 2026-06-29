#!/usr/bin/env python3
"""Background monitor: surface live meeting transcription in Claude Code.

Registered under experimental.monitors, so Claude Code runs this as a persistent
per-session process. While a *live* meeting is recording (`record.py start
--live`), whisper.cpp's stream example appends recognized text to the meeting's
transcript.txt; this monitor tails that file and prints each new chunk to stdout.
Claude Code delivers every stdout line as a notification, so the transcript shows
up in near-real-time. When no live meeting is running it just idles cheaply.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_active  # noqa: E402

POLL_SECONDS = 1.0


def check_once(state):
    """Emit any transcript text not yet shown. `state` persists across calls."""
    active = load_active()
    if not active or active.get("mode") != "live":
        state["id"] = None
        state["emitted"] = 0
        return

    if state.get("id") != active.get("id"):
        state["id"] = active.get("id")
        state["emitted"] = 0
        print(f"📝 live transcription started: {active.get('title')}", flush=True)

    path = active.get("transcript_path") or os.path.join(active.get("dir", ""), "transcript.txt")
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return

    # Emit only the suffix beyond what we've already shown. Using a character
    # count (not a file offset) is robust whether stream appends or rewrites the
    # cumulative transcript each pass.
    if len(text) > state.get("emitted", 0):
        fresh = text[state["emitted"]:]
        state["emitted"] = len(text)
        for line in fresh.splitlines():
            line = line.strip()
            if line:
                print(f"📝 {line}", flush=True)


def main():
    state = {"id": None, "emitted": 0}
    while True:
        try:
            check_once(state)
        except Exception:
            pass
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
