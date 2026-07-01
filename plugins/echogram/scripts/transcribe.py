#!/usr/bin/env python3
"""Transcribe a recorded meeting to text with whisper.cpp.

Locates the whisper.cpp binary and a ggml model, runs it on the meeting's
audio.wav, and writes transcript.txt next to it. The `end` skill then hands that
transcript to Claude to write the minutes.

Resolution:
    binary  $WHISPER_BIN -> `whisper-cli` -> `whisper-cpp` on PATH
    model   $WHISPER_MODEL (file) -> first ggml-*.bin under $WHISPER_MODEL_DIR
            or common install dirs (prefer base/small over tiny/large)

Usage:
    transcribe.py <meeting_dir | audio.wav>
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import which, load_config  # noqa: E402

MODEL_DIRS = [
    os.environ.get("WHISPER_MODEL_DIR", ""),
    os.path.expanduser("~/.cache/whisper.cpp"),
    os.path.expanduser("~/.cache/whisper"),
    "/usr/local/share/whisper.cpp/models",
    "/opt/homebrew/share/whisper-cpp/models",
    "/usr/share/whisper.cpp/models",
]
# Preference order when several models are present (accuracy vs. speed balance).
# English-only (.en) models are faster but can't transcribe other languages, so
# they're only preferred when the language is explicitly English. large-v3-turbo
# is a distilled large-v3 — near-large quality but much faster, so it ranks above
# large among the multilingual options.
ENGLISH_PREF = ["base.en", "small.en", "base", "small", "medium",
                "large-v3-turbo", "large-v3", "large", "tiny"]
MULTILINGUAL_PREF = ["base", "small", "medium",
                     "large-v3-turbo", "large-v3", "large", "tiny"]

INSTALL_HINT = (
    "whisper.cpp not found. Install it and a model, e.g.:\n"
    "  brew install whisper-cpp                  # provides `whisper-cli`\n"
    "  # or build from https://github.com/ggml-org/whisper.cpp\n"
    "  # download a model (e.g. base.en) into ~/.cache/whisper.cpp/\n"
    "Then point echogram at them if needed:\n"
    "  export WHISPER_BIN=/path/to/whisper-cli\n"
    "  export WHISPER_MODEL=/path/to/ggml-base.en.bin\n"
    "Verify with /echogram:setup."
)


def find_binary():
    env = os.environ.get("WHISPER_BIN")
    if env and os.path.exists(env):
        return env
    return which("whisper-cli") or which("whisper-cpp")


def find_model(language="auto", prefer=""):
    """Pick a ggml model.

    A non-empty `prefer` (e.g. "large-v3-turbo") pins a specific model by name
    when it's installed. Otherwise fall back to the preference order; for
    non-English languages, prefer a multilingual model and never fall back to an
    English-only (.en) one (it can't do e.g. Korean)."""
    env = os.environ.get("WHISPER_MODEL")
    if env and os.path.exists(env):
        return env
    found = {}
    for d in MODEL_DIRS:
        if not d or not os.path.isdir(d):
            continue
        for name in os.listdir(d):
            if name.startswith("ggml-") and name.endswith(".bin"):
                key = name[len("ggml-"):-len(".bin")]
                found.setdefault(key, os.path.join(d, name))
    if not found:
        return None
    if prefer and prefer in found:      # explicit choice wins when present
        return found[prefer]
    english_only = language == "en"
    for pref in (ENGLISH_PREF if english_only else MULTILINGUAL_PREF):
        if pref in found:
            return found[pref]
    # Last resort: any model for English; for other languages skip .en models.
    pool = found if english_only else \
        {k: v for k, v in found.items() if not k.endswith(".en")}
    return sorted(pool.values())[0] if pool else None


def build_command(binary, model, wav, out_base, language="auto"):
    # -otxt + -of writes "<out_base>.txt"; -l sets/auto-detects language; -np quiet.
    return [binary, "-m", model, "-f", wav, "-otxt", "-of", out_base,
            "-l", language, "-np"]


def find_stream_binary():
    """Locate whisper.cpp's real-time `stream` example (for live mode)."""
    env = os.environ.get("WHISPER_STREAM_BIN")
    if env and os.path.exists(env):
        return env
    return which("whisper-stream")


_TS_RE = re.compile(r"^\[(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*[^\]]+\]\s*(.*)$")


def dedup_transcript(text):
    """Collapse whisper-stream's repeated output into clean, ordered lines.

    Sliding-window streaming re-transcribes the same audio span repeatedly, so
    the raw file accumulates duplicates. Lines tagged with a `[start --> end]`
    timestamp are keyed by their start time — a later emission for the same start
    OVERWRITES the earlier one (the latest pass is the most complete). Untimed
    lines drop exact repeats and growing partials (keep the longest).
    """
    timed = {}        # start_ts -> text (dict preserves first-seen order)
    untimed = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = _TS_RE.match(line)
        if m:
            timed[m.group(1)] = m.group(2).strip()      # same timestamp -> overwrite
        elif untimed and (line.startswith(untimed[-1]) or untimed[-1].startswith(line)):
            if len(line) >= len(untimed[-1]):           # keep the longer partial
                untimed[-1] = line
        else:
            untimed.append(line)
    lines = [t for t in timed.values() if t] + untimed
    return "\n".join(lines)


def build_stream_command(binary, model, transcript_path, language="auto"):
    """whisper.cpp `stream`: live mic transcription, appending to a text file.

    `-l` is set explicitly because stream defaults to English; pass "auto" or a
    code like "ko". Extra flags via $WHISPER_STREAM_ARGS (space-separated), e.g.
    "--step 500 --length 5000 -vth 0.6" to tune latency/VAD.
    """
    extra = (os.environ.get("WHISPER_STREAM_ARGS") or "").split()
    return [binary, "-m", model, "-f", transcript_path, "-l", language] + extra


def transcribe(meeting_dir):
    wav = meeting_dir if meeting_dir.endswith(".wav") else \
        os.path.join(meeting_dir, "audio.wav")
    if not os.path.exists(wav) or os.path.getsize(wav) == 0:
        print(f"No audio to transcribe at {wav}")
        return 1
    cfg = load_config()
    language = cfg.get("language", "auto")
    binary = find_binary()
    model = find_model(language, cfg.get("model", ""))
    if not binary or not model:
        print(INSTALL_HINT)
        return 1

    out_base = os.path.join(os.path.dirname(wav), "transcript")
    cmd = build_command(binary, model, wav, out_base, language)
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    txt = out_base + ".txt"
    if result.returncode != 0 or not os.path.exists(txt):
        print("Transcription failed.")
        err = (result.stderr or b"").decode("utf-8", "replace").strip()
        if err:
            print(err[-800:])
        return 1

    with open(txt, encoding="utf-8") as f:
        words = len(f.read().split())
    print(f"📝 Transcript: {txt} ({words} words)")
    print(f"TRANSCRIPT: {txt}")
    return 0


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    return transcribe(argv[0])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
