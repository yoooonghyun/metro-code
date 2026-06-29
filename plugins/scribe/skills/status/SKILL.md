---
name: status
description: >-
  Show whether a meeting is currently recording and list recent meetings. Use
  for "is scribe recording?", "meeting status", "회의 녹음 상태", "회의록 목록".
---

# Scribe — status

Show the current recording state and recent meetings.

## Steps

Run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/record.py" status
```

Relay the result: whether a recording is active (and since when), and the list
of recent meetings with their ids. Offer `/scribe:end` if one is active.
