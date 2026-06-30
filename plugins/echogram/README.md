# echogram

Meeting recorder for Claude Code. **Start** a meeting, talk, **end** it — echogram
records the audio locally (ffmpeg), transcribes it with **whisper.cpp**, and then
Claude turns the transcript into structured minutes saved locally and optionally
uploaded to **Notion** or **Confluence**.

```text
/echogram:start  Quarterly planning
… meeting happens …
/echogram:end
→ minutes.md (Summary · Attendees · Discussion · Decisions · Action items)
→ uploaded to your configured destination
```

## Install

```text
/plugin marketplace add yoooonghyun/metro-code
/plugin install echogram@metro-code
/echogram:setup
```

> Recording needs a **local microphone**, so echogram works on local Claude Code
> (desktop/CLI), **not** in a remote/web session (no audio device there). On
> macOS, grant your terminal app **Microphone** permission.

## Requirements

- `python3` (standard library only)
- [`ffmpeg`](https://ffmpeg.org) — audio capture (`brew install ffmpeg` / `apt install ffmpeg`)
- [`whisper.cpp`](https://github.com/ggml-org/whisper.cpp) — transcription
  (`brew install whisper-cpp` gives `whisper-cli`) plus a `ggml-*.bin` model
  (e.g. `base.en`). Point at non-standard locations with `WHISPER_BIN` /
  `WHISPER_MODEL`.
- *(optional, for live mode)* `whisper-stream` — whisper.cpp's real-time `stream`
  example (needs an SDL2 build). Set `WHISPER_STREAM_BIN` if it's elsewhere; tune
  with `WHISPER_STREAM_ARGS` (e.g. `"--step 500 --length 5000 -vth 0.6"`).

`/echogram:setup` checks all of these and tells you what's missing.

## Usage

Talk to Claude (English or Korean) — one skill per action:

- `setup` — "set up echogram" / "회의록 설정" — check deps + choose upload target
- `start` — "start the meeting" / "회의 시작" (live by default; "batch" for audio-only)
- `end` — "wrap up the meeting" / "회의 끝내고 정리해줘"
- `status` — "is echogram recording?" / "회의 녹음 상태"
- `update` — "update echogram" / "회의록 플러그인 업데이트" — pull the latest version

### Live transcription (default)

`start` records in **live** mode by default — the transcript streams into the
conversation as the meeting happens:

```bash
python3 "$CLAUDE_PLUGIN_ROOT/scripts/record.py" start "My meeting"
```

The `live-transcript` background **monitor** tails the recognized text and prints
each new line, which Claude Code surfaces as it arrives. Live mode uses
`whisper-stream` (lower latency, lower accuracy) and writes straight to
`transcript.txt`, so `/echogram:end` skips batch transcription and goes straight to
the minutes. Expect many lines to stream in. Monitors are **experimental** and
only run while a Claude Code session is open.

If `whisper-stream` isn't installed, `start` automatically falls back to **batch**
mode (audio recorded via ffmpeg, transcribed at the end). Force batch with
`start --batch` when you want audio-only / higher-accuracy transcription.

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
| `scripts/record.py` | `start`/`stop`/`status` — detached recording (ffmpeg, or whisper-stream for `--live`), clean stop via SIGINT |
| `scripts/transcribe.py` | locate whisper.cpp + model, transcribe `audio.wav` → `transcript.txt` |
| `scripts/monitor.py` | live-transcript monitor: tails `transcript.txt` and surfaces new lines |
| `scripts/setup.py` | check dependencies, choose upload target, store config |
| `skills/setup/` | `/echogram:setup` |
| `skills/start/` | `/echogram:start` |
| `skills/end/` | `/echogram:end` — stop → transcribe → Claude writes minutes → upload |
| `skills/status/` | `/echogram:status` |
| `skills/update/` | `/echogram:update` — update the plugin to the latest version |

- **Data location**: config (`config.json`) and recordings (`meetings/<id>/` with
  `audio.wav`, `transcript.txt`, `minutes.md`, `meta.json`) live in the plugin's
  persistent data dir (`$CLAUDE_PLUGIN_DATA`, falling back to `~/.claude/echogram`),
  so they survive plugin updates. Override with `$ECHOGRAM_DATA_DIR`.
- **No API key for the minutes**: transcription is local (whisper.cpp) and the
  summarization is done by Claude itself — scripts only manage state and files.

## Updating

```text
/echogram:update
```

Refreshes the marketplace (`claude plugin marketplace update metro-code`) and
updates the plugin. No re-pointing needed (echogram stores no absolute paths),
and your config and recorded meetings persist across updates. Start a new session
afterward.

## Tests

Offline suite (ffmpeg/whisper/subprocess all mocked — no audio or tools needed):

```bash
python3 plugins/echogram/tests/test_echogram.py
```
