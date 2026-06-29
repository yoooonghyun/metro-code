---
name: end
description: >-
  End the meeting: stop recording, transcribe with whisper.cpp, write structured
  minutes, and upload them to the configured destination. Use for "end the
  meeting", "wrap up", "finish recording", "회의 끝", "회의록 마무리해줘",
  "녹음 끝내고 정리해줘".
---

# Echogram — end a meeting

Stop the recording and turn it into minutes. You (Claude) write the minutes from
the transcript — no transcription model is needed for that step.

## Steps

1. Stop the recording. Note the `MEETING_DIR:` line in the output:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/record.py" stop
   ```

   If it warns that no audio was captured, tell the user (likely a mic-permission
   issue) and stop here.

2. Get the transcript:
   - If `stop` already printed a `TRANSCRIPT:` line, the meeting was recorded in
     **live** mode and is already transcribed — use that file, skip this step.
   - Otherwise (batch mode) transcribe now; note the `TRANSCRIPT:` path:
     ```bash
     python3 "${CLAUDE_PLUGIN_ROOT}/scripts/transcribe.py" "<MEETING_DIR>"
     ```
     If it reports whisper.cpp/model missing, point the user to `/echogram:setup`.

3. Read the transcript file and write **minutes** to `<MEETING_DIR>/minutes.md`
   using this structure (keep the user's language; omit empty sections):

   ```markdown
   # <title> — <date>

   ## Summary
   2–4 sentences.

   ## Attendees
   - …

   ## Discussion
   - key points by topic

   ## Decisions
   - …

   ## Action items
   - [ ] <owner> — <task> (due <date>)

   ## Open questions / Next steps
   - …
   ```

4. Read the upload target and act on it:

   ```bash
   cat "$(python3 -c "import sys;sys.path.insert(0,'${CLAUDE_PLUGIN_ROOT}/scripts');import common;print(common.config_path())")"
   ```

   - **local** — nothing more to do; report the saved `minutes.md` path.
   - **notion** — create a page with the minutes via the Notion MCP
     (`notion-create-pages`, load it with ToolSearch first) under the configured
     `notion.parent_page_id`. Report the new page URL.
   - **confluence** — create a page via REST (convert the minutes to simple HTML
     for the storage body):

     ```bash
     curl -sS -u "$CONFLUENCE_USER:$CONFLUENCE_TOKEN" \
       -X POST "<base_url>/rest/api/content" \
       -H "Content-Type: application/json" \
       -d '{"type":"page","title":"<title> — <date>","space":{"key":"<space_key>"},
            "ancestors":[{"id":"<parent_page_id>"}],
            "body":{"storage":{"value":"<html>","representation":"storage"}}}'
     ```

     Report the resulting page link.

5. Summarize for the user: the title, where the minutes were saved, the upload
   result, and the action items.

## Notes

- Always keep the local `minutes.md`, even when uploading elsewhere.
- If the upload destination isn't configured (e.g. Notion parent unset), save
  locally and tell the user to run `/echogram:setup`.
