---
name: start
description: >-
  Start recording a meeting (local audio via ffmpeg). Use when the user wants to
  begin capturing a meeting — "start the meeting", "record this meeting",
  "회의 시작", "회의록 시작해줘", "지금부터 녹음".
---

# Scribe — start a meeting

Begin a local audio recording. It keeps running in the background until
`/scribe:end`.

## Steps

1. Start recording (pass a short title if the user gave one):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/record.py" start "<title>"
   ```

2. Confirm to the user that recording has started and that `/scribe:end` will
   stop it and produce the minutes.

## Notes

- If the command reports ffmpeg is missing, point the user to `/scribe:setup`.
- Only one meeting records at a time; if one is already active the script says so
  — offer to `/scribe:end` the current one first.
- Recording needs a local mic (won't work in a remote/web session).
