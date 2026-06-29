---
name: start
description: >-
  Start recording a meeting locally. Live transcription by default (shown in real
  time); batch mode is opt-in. Use for "start the meeting", "record this meeting",
  "회의 시작", "회의록 시작해줘", "실시간 전사로 시작", "live transcription".
---

# Scribe — start a meeting

Begin a local recording that runs in the background until `/scribe:end`.

## Steps

1. Start recording (default is **live**):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/record.py" start "<title>"
   ```

   - **Live (default)** — the `live-transcript` monitor prints each line as it is
     recognized, so the transcript streams into the conversation as the meeting
     goes (many lines will arrive — that's expected). If `whisper-stream` isn't
     installed, it automatically falls back to batch and says so.
   - **Batch** — if the user prefers audio-only / higher-accuracy transcription
     at the end (no live stream), add `--batch`:
     ```bash
     python3 "${CLAUDE_PLUGIN_ROOT}/scripts/record.py" start --batch "<title>"
     ```

2. Confirm recording has started and that `/scribe:end` stops it and produces the
   minutes.

## Notes

- Live mode needs whisper.cpp's `whisper-stream`; batch needs `ffmpeg`. If a
  required tool is missing the script says so — point the user to `/scribe:setup`.
- Only one meeting records at a time; if one is active, offer `/scribe:end` first.
- Recording needs a local mic (won't work in a remote/web session).
