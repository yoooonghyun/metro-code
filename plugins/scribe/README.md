# scribe

Meeting recorder for Claude Code. **Start** a meeting, talk, **end** it — scribe
records the audio locally (ffmpeg), transcribes it with **whisper.cpp**, and then
Claude turns the transcript into structured minutes saved locally and optionally
uploaded to **Notion** or **Confluence**.

```text
/scribe:start  Quarterly planning
… meeting happens …
/scribe:end
→ minutes.md (Summary · Attendees · Discussion · Decisions · Action items)
→ uploaded to your configured destination
```

## Install

```text
/plugin marketplace add yoooonghyun/metro-code
/plugin install scribe@metro-code
/scribe:setup
```

> Recording needs a **local microphone**, so scribe works on local Claude Code
> (desktop/CLI), **not** in a remote/web session (no audio device there). On
> macOS, grant your terminal app **Microphone** permission.

## Requirements

- `python3` (standard library only)
- [`ffmpeg`](https://ffmpeg.org) — audio capture (`brew install ffmpeg` / `apt install ffmpeg`)
- [`whisper.cpp`](https://github.com/ggml-org/whisper.cpp) — transcription
  (`brew install whisper-cpp` gives `whisper-cli`) plus a `ggml-*.bin` model
  (e.g. `base.en`). Point at non-standard locations with `WHISPER_BIN` /
  `WHISPER_MODEL`.

`/scribe:setup` checks all of these and tells you what's missing.

## Usage

Talk to Claude (English or Korean) — one skill per action:

- `setup` — "set up scribe" / "회의록 설정" — check deps + choose upload target
- `start` — "start the meeting" / "회의 시작"
- `end` — "wrap up the meeting" / "회의 끝내고 정리해줘"
- `status` — "is scribe recording?" / "회의 녹음 상태"

Or call the scripts directly:

```bash
P="$CLAUDE_PLUGIN_ROOT/scripts"
python3 $P/setup.py                              # deps + config status
python3 $P/setup.py --target notion parent_page_id=<id>
python3 $P/record.py start "My meeting"
python3 $P/record.py status
python3 $P/record.py stop                        # prints MEETING_DIR
python3 $P/transcribe.py <MEETING_DIR>           # prints TRANSCRIPT
```

## Upload destinations (chosen at setup)

| Target | What happens | Needs |
|--------|--------------|-------|
| `local` | minutes.md saved under the data dir | — |
| `notion` | Claude creates a page via the Notion MCP under a parent page | Notion MCP connected; `parent_page_id` |
| `confluence` | page created via Confluence REST | `base_url`, `space_key`, `parent_page_id`; `CONFLUENCE_TOKEN` + `CONFLUENCE_USER` env |

A local `minutes.md` is **always** kept, even when uploading elsewhere.

## How it works

| File | Role |
|------|------|
| `scripts/common.py` | paths, config, the active-recording handle, per-OS audio input |
| `scripts/record.py` | `start`/`stop`/`status` — detached ffmpeg recording, clean stop via SIGINT |
| `scripts/transcribe.py` | locate whisper.cpp + model, transcribe `audio.wav` → `transcript.txt` |
| `scripts/setup.py` | check dependencies, choose upload target, store config |
| `skills/setup/` | `/scribe:setup` |
| `skills/start/` | `/scribe:start` |
| `skills/end/` | `/scribe:end` — stop → transcribe → Claude writes minutes → upload |
| `skills/status/` | `/scribe:status` |

- **Data location**: config (`config.json`) and recordings (`meetings/<id>/` with
  `audio.wav`, `transcript.txt`, `minutes.md`, `meta.json`) live in the plugin's
  persistent data dir (`$CLAUDE_PLUGIN_DATA`, falling back to `~/.claude/scribe`),
  so they survive plugin updates. Override with `$SCRIBE_DATA_DIR`.
- **No API key for the minutes**: transcription is local (whisper.cpp) and the
  summarization is done by Claude itself — scripts only manage state and files.

## Tests

Offline suite (ffmpeg/whisper/subprocess all mocked — no audio or tools needed):

```bash
python3 plugins/scribe/tests/test_scribe.py
```
