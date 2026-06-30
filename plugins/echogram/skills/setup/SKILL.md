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

2. If anything is missing, help the user install it (report the exact command
   for their OS), then re-run step 1:
   - **ffmpeg** — `brew install ffmpeg` (macOS) / `sudo apt-get install ffmpeg` (Linux)
   - **whisper.cpp** — `brew install whisper-cpp` (gives `whisper-cli`), or build
     from https://github.com/ggml-org/whisper.cpp
   - **a model** — download a `ggml-*.bin` into `~/.cache/whisper.cpp/`. For
     non-English meetings (e.g. **Korean**) use a **multilingual** model like
     `ggml-base.bin`/`ggml-small.bin` — an English-only `*.en` model can't
     transcribe other languages. If the binary/model are in nonstandard places,
     set `WHISPER_BIN` / `WHISPER_MODEL`.

3. Set the transcription **language** (default `auto`-detects). For a Korean
   meeting you can pin it:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" --language ko   # or auto / en / ja ...
   ```

4. Ask the user **where finished minutes should be uploaded**, then set it:

   ```bash
   # Local files only (default)
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" --target local

   # Notion — needs the Notion MCP connected in Claude Code
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" --target notion parent_page_id=<page_id>

   # Confluence — needs CONFLUENCE_TOKEN and CONFLUENCE_USER in the environment
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" --target confluence \
       base_url=https://yourorg.atlassian.net/wiki space_key=ENG parent_page_id=<id>
   ```

5. (Optional) If recording captures the wrong device, set an override:
   `setup.py --audio-input :1` (macOS index) and confirm with a short test
   recording via `/echogram:start` → `/echogram:end`.

## Notes

- Recording needs a real microphone, so this works on **local** Claude Code
  (desktop/CLI), not in a remote/web session (no audio device there).
- On macOS, grant the terminal app **Microphone** permission (System Settings →
  Privacy & Security → Microphone) — the first recording may prompt for it.
