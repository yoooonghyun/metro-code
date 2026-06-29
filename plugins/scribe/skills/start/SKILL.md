---
name: start
description: >-
  Start recording a meeting locally. Default batch mode (ffmpeg, transcribed at
  the end); optional live mode shows the transcript in real time. Use for
  "start the meeting", "record this meeting", "회의 시작", "회의록 시작해줘",
  "실시간 전사로 시작", "live transcription".
---

# Scribe — start a meeting

Begin a local recording that runs in the background until `/scribe:end`.

## Steps

1. Choose the mode from what the user asked:
   - **Batch (default)** — records audio, transcribes at the end:
     ```bash
     python3 "${CLAUDE_PLUGIN_ROOT}/scripts/record.py" start "<title>"
     ```
   - **Live** — if the user wants to *see the transcript in real time*
     ("실시간", "live", "show as it goes"), add `--live`:
     ```bash
     python3 "${CLAUDE_PLUGIN_ROOT}/scripts/record.py" start --live "<title>"
     ```
     In live mode the `live-transcript` monitor prints each new line as it is
     recognized, so the transcript appears in the conversation as the meeting
     goes. (Many lines will stream in — that's expected.)

2. Confirm recording has started and that `/scribe:end` stops it and produces the
   minutes.

## Notes

- Batch mode needs `ffmpeg`; live mode needs whisper.cpp's `whisper-stream`. If
  either is missing the script says so — point the user to `/scribe:setup`.
- Only one meeting records at a time; if one is active, offer `/scribe:end` first.
- Recording needs a local mic (won't work in a remote/web session).
