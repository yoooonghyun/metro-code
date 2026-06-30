#!/usr/bin/env python3
"""Background monitor: surface live meeting transcription in Claude Code.

Registered under experimental.monitors, so Claude Code runs this as a persistent
per-session process. While a *live* meeting is recording (`record.py start
--live`), whisper.cpp's stream example appends recognized text — with sliding
windows that repeat the same span — to the meeting's transcript.raw.txt. This
monitor reads that raw file, de-duplicates it (same-timestamp segments overwrite,
so nothing is shown twice), and prints only newly finalized lines to stdout.
Claude Code delivers every stdout line as a notification, so the transcript shows
up in near-real-time. When no live meeting is running it just idles cheaply.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_active  # noqa: E402
from transcribe import dedup_transcript  # noqa: E402

POLL_SECONDS = 1.0


def check_once(state):
    """Emit any de-duplicated transcript lines not yet shown. `state` persists."""
    active = load_active()
    if not active or active.get("mode") != "live":
        state["id"] = None
        state["emitted"] = 0
        return

    if state.get("id") != active.get("id"):
        state["id"] = active.get("id")
        state["emitted"] = 0
        print(f"📝 live transcription started: {active.get('title')}", flush=True)

    path = (active.get("raw_path") or active.get("transcript_path")
            or os.path.join(active.get("dir", ""), "transcript.raw.txt"))
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
    except OSError:
        return

    # De-dup first, then emit only lines beyond what we've already shown. Because
    # same-timestamp segments overwrite in place, the clean list grows only when a
    # genuinely new segment is finalized — so repeats never reach the chat.
    lines = [ln for ln in dedup_transcript(raw).splitlines() if ln.strip()]
    if len(lines) > state.get("emitted", 0):
        for line in lines[state["emitted"]:]:
            print(f"📝 {line}", flush=True)
        state["emitted"] = len(lines)


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
