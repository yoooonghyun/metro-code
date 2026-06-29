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
# they're only preferred when the language is explicitly English.
ENGLISH_PREF = ["base.en", "small.en", "base", "small", "medium", "large", "tiny"]
MULTILINGUAL_PREF = ["base", "small", "medium", "large-v3", "large", "tiny"]

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


def find_model(language="auto"):
    """Pick a ggml model. For non-English languages, prefer a multilingual model
    and never fall back to an English-only (.en) one (it can't do e.g. Korean)."""
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
    language = load_config().get("language", "auto")
    binary = find_binary()
    model = find_model(language)
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
