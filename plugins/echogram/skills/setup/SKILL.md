---
name: setup
description: >-
  Set up echogram: check dependencies (ffmpeg, whisper.cpp + model) and choose
  where finished meeting minutes are uploaded (local, Notion, or Confluence).
  Use for "set up echogram", "configure meeting notes", "회의록 설정",
  "회의록 업로드 위치 설정".
---

# Echogram — setup

One-time setup: verify the recording/transcription tools and pick an upload
destination. The choice is stored in config.json and reused by `/echogram:end`.

## Steps

1. Check dependencies and show the current config:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py"
   ```

2. If `ffmpeg`/`whisper.cpp` are missing, help the user install them (report the
   exact command for their OS), then re-run step 1:
   - **ffmpeg** — `brew install ffmpeg` (macOS) / `sudo apt-get install ffmpeg` (Linux)
   - **whisper.cpp** — `brew install whisper-cpp` (gives `whisper-cli`), or build
     from https://github.com/ggml-org/whisper.cpp. If they're in nonstandard
     places, set `WHISPER_BIN` / `WHISPER_STREAM_BIN`.

3. If no model is installed, **show the options and let the user choose**, then
   download it:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" --list-models
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" --install-model large-v3-turbo
   ```

   Present the list and recommend by need: **small** is the CPU-friendly default
   and works for Korean; **large-v3-turbo** is near-large accuracy but much
   faster (a great high-quality pick); **medium**/**large-v3** for max accuracy;
   **tiny/base** only for quick/clean English. For an English-only meeting an
   `.en` variant (e.g. `small.en`) is fine; for Korean or mixed audio use a plain
   (multilingual) model. The download lands in `~/.cache/whisper.cpp/` and is
   picked up automatically (override location with `WHISPER_MODEL`).

   If several models are installed, auto-selection prefers higher quality
   (large-v3-turbo → large-v3 → …). To pin a specific one:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" --model large-v3-turbo   # "auto" to unset
   ```

4. Set the transcription **language** (default `auto`-detects). For a Korean
   meeting you can pin it:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" --language ko   # or auto / en / ja ...
   ```

5. Ask the user **where finished minutes should be uploaded**, then set it:

   ```bash
   # Local files only (default)
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" --target local

   # Notion — needs the Notion MCP connected in Claude Code
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" --target notion parent_page_id=<page_id>

   # Confluence — needs CONFLUENCE_TOKEN and CONFLUENCE_USER in the environment
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" --target confluence \
       base_url=https://yourorg.atlassian.net/wiki space_key=ENG parent_page_id=<id>
   ```

6. (Optional) **Connect Google Calendar** so `/echogram:end` can fill the
   attendees from the meeting invite. Ask the user if they want it; if yes, add
   Google's official remote MCP and have them authenticate:

   ```bash
   claude mcp add --transport http google-calendar https://calendarmcp.googleapis.com/mcp/v1
   ```

   Then they finish the OAuth in `/mcp` (Authenticate). Requires a paid Claude
   plan and Claude Code v2.1.46+ (which lets claude.ai connectors work in Claude
   Code); alternatively they can enable the **Google Calendar** connector in
   claude.ai → Settings → Connectors. If any other Google Calendar MCP is already
   connected, keep it — `/echogram:end` uses whatever calendar tool is available.

7. (Optional) If recording captures the wrong device, set an override:
   `setup.py --audio-input :1` (macOS index) and confirm with a short test
   recording via `/echogram:start` → `/echogram:end`.

## Notes

- Recording needs a real microphone, so this works on **local** Claude Code
  (desktop/CLI), not in a remote/web session (no audio device there).
- On macOS, grant the terminal app **Microphone** permission (System Settings →
  Privacy & Security → Microphone) — the first recording may prompt for it.
