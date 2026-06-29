"""Shared helpers for the echogram (meeting-notes) plugin scripts.

echogram records a meeting's audio locally (ffmpeg), transcribes it with
whisper.cpp, and then lets Claude turn the transcript into structured minutes
that are saved locally and optionally uploaded to Notion or Confluence.

This module is the single source of truth for:
  - where user state lives (config + recorded meetings),
  - the "active recording" handle (so `end` can find what `start` began),
  - per-platform audio capture settings.

State location resolution (so data survives plugin updates, which change
${CLAUDE_PLUGIN_ROOT}):
    1. $ECHOGRAM_DATA_DIR     (explicit override, e.g. for testing)
    2. $CLAUDE_PLUGIN_DATA  (per-plugin persistent dir, set by Claude Code)
    3. ~/.claude/echogram     (fallback when run outside a plugin context)
"""
import json
import os
import shutil
import sys
import time

# Upload destinations chosen at setup time.
UPLOAD_TARGETS = ("local", "notion", "confluence")

DEFAULT_CONFIG = {
    "upload_target": "local",          # one of UPLOAD_TARGETS
    "notion": {"parent_page_id": ""},  # where new meeting pages are created
    "confluence": {"base_url": "", "space_key": "", "parent_page_id": ""},
    # audio_input overrides the auto-detected ffmpeg input (e.g. ":1" on macOS).
    "audio_input": "",
    # whisper language: "auto" detects, or a code like "ko"/"en"/"ja". Drives
    # both transcription and model choice (non-English avoids .en-only models).
    "language": "auto",
}


# --- paths -----------------------------------------------------------------

def data_dir():
    base = (
        os.environ.get("ECHOGRAM_DATA_DIR")
        or os.environ.get("CLAUDE_PLUGIN_DATA")
        or os.path.expanduser("~/.claude/echogram")
    )
    os.makedirs(base, exist_ok=True)
    return base


def config_path():
    return os.path.join(data_dir(), "config.json")


def active_path():
    return os.path.join(data_dir(), "active.json")


def meetings_dir():
    d = os.path.join(data_dir(), "meetings")
    os.makedirs(d, exist_ok=True)
    return d


def meeting_dir(meeting_id):
    d = os.path.join(meetings_dir(), meeting_id)
    os.makedirs(d, exist_ok=True)
    return d


def _read_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _atomic_write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


# --- config ----------------------------------------------------------------

def load_config():
    cfg = _read_json(config_path(), {})
    if not isinstance(cfg, dict):
        cfg = {}
    # Merge over defaults so missing keys are always present.
    merged = json.loads(json.dumps(DEFAULT_CONFIG))
    for k, v in cfg.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            merged[k].update(v)
        else:
            merged[k] = v
    return merged


def save_config(cfg):
    _atomic_write(config_path(), cfg)


# --- active recording ------------------------------------------------------
# active.json: {id, title, started_at, dir, audio_path, log_path, pid}

def load_active():
    data = _read_json(active_path(), None)
    return data if isinstance(data, dict) else None


def save_active(active):
    _atomic_write(active_path(), active)


def clear_active():
    try:
        os.remove(active_path())
    except OSError:
        pass


# --- meeting metadata ------------------------------------------------------

def meta_path(meeting_id):
    return os.path.join(meeting_dir(meeting_id), "meta.json")


def load_meta(meeting_id):
    return _read_json(meta_path(meeting_id), {}) or {}


def save_meta(meeting_id, meta):
    _atomic_write(meta_path(meeting_id), meta)


def list_meetings():
    """Return meeting metadata dicts, newest first."""
    out = []
    for name in os.listdir(meetings_dir()):
        meta = load_meta(name)
        if meta:
            out.append(meta)
    out.sort(key=lambda m: m.get("started_at", ""), reverse=True)
    return out


# --- audio capture ---------------------------------------------------------

def ffmpeg_input_args(config=None):
    """ffmpeg input flags for the current platform's default microphone.

    A non-empty config['audio_input'] overrides the device spec only (the
    container flag stays platform-correct). Examples of an override: ':1'
    (macOS avfoundation device index 1), 'hw:1' (ALSA).
    """
    config = config or {}
    override = (config.get("audio_input") or "").strip()
    if sys.platform == "darwin":
        return ["-f", "avfoundation", "-i", override or ":default"]
    if sys.platform.startswith("linux"):
        # PulseAudio/PipeWire expose a "default" source; ALSA users can override.
        if override and not override.startswith(":"):
            return ["-f", "alsa", "-i", override]
        return ["-f", "pulse", "-i", "default"]
    # Other platforms: best-effort, let the override carry the whole input.
    return ["-i", override] if override else ["-i", "default"]


def which(name):
    return shutil.which(name)


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


def new_meeting_id():
    return time.strftime("%Y%m%d-%H%M%S", time.localtime())
