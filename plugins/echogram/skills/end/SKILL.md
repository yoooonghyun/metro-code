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

3. **Attendees (if Google Calendar is connected).** If a Google Calendar MCP /
   tool is available (find it with ToolSearch, e.g. a `*calendar*` list-events
   tool), look up the meeting event and use its invitee list as the attendees:
   - Match by the meeting's start time — read `started_at` (and `title`) from
     `<MEETING_DIR>/meta.json` — and pick the event overlapping that time.
   - Collect each attendee's **display name and email** (keep the email; it's the
     key for tagging on Notion/Confluence later).
   - If no calendar tool is connected or no event matches, fall back to names
     mentioned in the transcript, and otherwise omit 참석자. Never invent people.

4. Read the transcript file and write **minutes** to `<MEETING_DIR>/minutes.md`.

   Render the section **headings in the meeting's language** (Korean transcript →
   Korean headings, shown below; English transcript → the English equivalents in
   parentheses). These **four sections are required and must appear in this
   order**, even if a section is brief; the metadata header and 참석자 are
   optional (include when known — prefer the calendar attendees from step 3):

   ```markdown
   # <제목> — <날짜>
   참석자: <names>            ← from the calendar event when available

   ## 아젠다 (Agenda)
   - the topics the meeting set out to cover (as a list)

   ## 회의 요약 (Summary)
   - a concise narrative of what was actually discussed (bullets or 3–6 sentences)

   ## 결론 (Conclusion)
   - the decisions reached and the agreed outcome

   ## 액션 아이템 (Action items)
   - [ ] <담당자> — <할 일> (기한: <날짜>)
   ```

   Rules:
   - Base everything strictly on the transcript; don't invent decisions or
     owners. If something is unknown, write "미정"/"TBD" rather than guessing.
     (Attendees may come from the calendar even if not heard in the transcript.)
   - Each action item is a checkbox with an owner and, when stated, a due date.
   - If the meeting had no clear agenda, infer it from the topics discussed and
     note that it was inferred.

5. Read the upload target and act on it. When uploading, **tag the attendees**
   (from step 3) as real users where possible — mentions notify them:

   ```bash
   cat "$(python3 -c "import sys;sys.path.insert(0,'${CLAUDE_PLUGIN_ROOT}/scripts');import common;print(common.config_path())")"
   ```

   - **local** — nothing more to do; report the saved `minutes.md` path.
   - **notion** — create a page with the minutes via the Notion MCP
     (`notion-create-pages`, load it with ToolSearch first) under the configured
     `notion.parent_page_id`. Resolve each attendee to a Notion user with
     `notion-get-users` (match by email) and **@-mention** them on the 참석자 line;
     for anyone not found, leave their plain name. Report the new page URL.
   - **confluence** — create a page via REST (convert the minutes to simple HTML
     for the storage body). Tag attendees with Confluence user mentions: resolve
     each email to an `accountId` (`GET <base_url>/rest/api/search?cql=...` or the
     user API) and put `<ac:link><ri:user ri:account-id="ID"/></ac:link>` on the
     참석자 line; fall back to plain names when not found.

     ```bash
     curl -sS -u "$CONFLUENCE_USER:$CONFLUENCE_TOKEN" \
       -X POST "<base_url>/rest/api/content" \
       -H "Content-Type: application/json" \
       -d '{"type":"page","title":"<title> — <date>","space":{"key":"<space_key>"},
            "ancestors":[{"id":"<parent_page_id>"}],
            "body":{"storage":{"value":"<html>","representation":"storage"}}}'
     ```

     Report the resulting page link.

6. Summarize for the user: the title, attendees, where the minutes were saved,
   the upload result, and the action items.

## Notes

- Always keep the local `minutes.md`, even when uploading elsewhere.
- If the upload destination isn't configured (e.g. Notion parent unset), save
  locally and tell the user to run `/echogram:setup`.
