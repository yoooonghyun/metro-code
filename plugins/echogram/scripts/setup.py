#!/usr/bin/env python3
"""Check echogram's dependencies and choose where finished minutes are uploaded.

The upload destination is picked once here and stored in config.json; the `end`
skill reads it to decide what to do after saving the local minutes.

Usage:
    setup.py                      # show dependency status + current config
    setup.py --target local
    setup.py --target notion     parent_page_id=<id>
    setup.py --target confluence base_url=<url> space_key=<key> parent_page_id=<id>
    setup.py --audio-input :1     # override the ffmpeg input device (optional)
    setup.py --language ko        # transcription language ("auto", "ko", "en", ...)
    setup.py --list-models        # show whisper models you can install
    setup.py --install-model large-v3-turbo  # download a ggml model from Hugging Face
    setup.py --model large-v3-turbo  # pin which installed model to use ("auto" to unset)

Destinations:
    local       save minutes.md only (always also saved locally)
    notion      Claude creates a page via the Notion MCP under parent_page_id
    confluence  uploaded via Confluence REST (token from $CONFLUENCE_TOKEN,
                user from $CONFLUENCE_USER) to base_url/space_key
"""
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import which, load_config, save_config, UPLOAD_TARGETS  # noqa: E402
from transcribe import find_binary, find_model, find_stream_binary  # noqa: E402

# whisper.cpp ggml models, hosted on Hugging Face. Append ".en" for an
# English-only variant of tiny/base/small/medium.
HF_BASE = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/"
MODELS = [
    ("tiny",           "75 MB",  "fastest, lowest quality — clean English only"),
    ("base",           "142 MB", "fast, basic quality"),
    ("small",          "466 MB", "balanced; good for Korean — CPU-friendly"),
    ("medium",         "1.5 GB", "high quality; slower on CPU"),
    ("large-v3-turbo", "1.6 GB", "near-large quality, faster"),
    ("large-v3",       "2.9 GB", "best quality; needs a strong CPU/GPU"),
]
MODEL_NAMES = {m[0] for m in MODELS}


def model_install_dir():
    d = os.environ.get("WHISPER_MODEL_DIR") or os.path.expanduser("~/.cache/whisper.cpp")
    os.makedirs(d, exist_ok=True)
    return d


def list_models():
    print("Whisper models (append .en for an English-only tiny/base/small/medium):")
    for name, size, note in MODELS:
        print(f"  {name:16} {size:>7}  {note}")
    print("\nInstall one:  setup.py --install-model small")
    print("For Korean or most real meetings, use small or larger (not tiny/base).")


def install_model(name):
    base = name[:-3] if name.endswith(".en") else name
    if base not in MODEL_NAMES:
        print(f"Unknown model '{name}'.")
        list_models()
        return 1
    fname = f"ggml-{name}.bin"
    dest = os.path.join(model_install_dir(), fname)
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        print(f"Already installed: {dest}")
        return 0
    url = HF_BASE + fname
    print(f"Downloading {fname} …")
    tmp = dest + ".part"
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:
            total = int(resp.headers.get("Content-Length", 0) or 0)
            done, last = 0, -10
            with open(tmp, "wb") as f:
                while True:
                    chunk = resp.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
                    if total:
                        pct = done * 100 // total
                        if pct >= last + 10:
                            last = pct - pct % 10
                            print(f"  {pct:3d}%  ({done >> 20} MB)", flush=True)
        if total and done != total:
            raise IOError(f"incomplete download: {done} of {total} bytes")
        os.replace(tmp, dest)
    except Exception as e:
        try:
            os.remove(tmp)
        except OSError:
            pass
        print(f"Download failed: {e}")
        print(f"Download it manually into {model_install_dir()}:\n  {url}")
        return 1
    print(f"Installed: {dest}")
    print("It will be picked up automatically next time you transcribe.")
    return 0


def deps_status(language="auto", prefer=""):
    ffmpeg = which("ffmpeg")
    binary = find_binary()
    model = find_model(language, prefer)
    stream = find_stream_binary()
    print("Dependencies:")
    print(f"  ffmpeg          {'✓ ' + ffmpeg if ffmpeg else '✗ missing (brew/apt install ffmpeg)'}")
    print(f"  whisper.cpp     {'✓ ' + binary if binary else '✗ missing (brew install whisper-cpp)'}")
    note = "" if model else (" (need a multilingual ggml-*.bin, not an .en-only model)"
                             if language != "en" else "")
    print(f"  whisper model   {'✓ ' + model if model else '✗ none' + note}")
    print(f"  whisper-stream  {'✓ ' + stream if stream else '○ optional (live mode; needs SDL2 build)'}")
    return bool(ffmpeg and binary and model)


def print_config(cfg):
    target = cfg.get("upload_target", "local")
    print(f"Upload target: {target}")
    if target == "notion":
        print(f"  notion.parent_page_id = {cfg['notion'].get('parent_page_id') or '(unset)'}")
    elif target == "confluence":
        c = cfg["confluence"]
        print(f"  confluence.base_url       = {c.get('base_url') or '(unset)'}")
        print(f"  confluence.space_key      = {c.get('space_key') or '(unset)'}")
        print(f"  confluence.parent_page_id = {c.get('parent_page_id') or '(unset)'}")
    print(f"  language = {cfg.get('language', 'auto')}")
    print(f"  model    = {cfg.get('model') or 'auto'}")
    if cfg.get("audio_input"):
        print(f"  audio_input = {cfg['audio_input']}")


def apply_params(cfg, target, params):
    """Route key=value params into the right config section for `target`."""
    for p in params:
        if "=" not in p:
            continue
        key, val = p.split("=", 1)
        key = key.strip()
        if key in ("base_url", "space_key", "parent_page_id") and target == "confluence":
            cfg["confluence"][key] = val
        elif key == "parent_page_id" and target == "notion":
            cfg["notion"]["parent_page_id"] = val
        elif key == "audio_input":
            cfg["audio_input"] = val


def main(argv):
    cfg = load_config()

    if "--list-models" in argv:
        list_models()
        return 0

    if "--install-model" in argv:
        i = argv.index("--install-model")
        if i + 1 >= len(argv):
            list_models()
            return 1
        return install_model(argv[i + 1])

    if "--audio-input" in argv:
        i = argv.index("--audio-input")
        if i + 1 < len(argv):
            cfg["audio_input"] = argv[i + 1]
            save_config(cfg)
            print(f"audio_input set to {cfg['audio_input']}")

    if "--language" in argv:
        i = argv.index("--language")
        if i + 1 < len(argv):
            cfg["language"] = argv[i + 1]
            save_config(cfg)
            print(f"language set to {cfg['language']}")
            return 0

    if "--model" in argv:
        i = argv.index("--model")
        if i + 1 < len(argv):
            name = argv[i + 1]
            cfg["model"] = "" if name in ("auto", "") else name
            save_config(cfg)
            print(f"model set to {cfg['model'] or 'auto'}")
            if cfg["model"] and not find_model(cfg.get("language", "auto"), cfg["model"]):
                print(f"Note: ggml-{cfg['model']}.bin isn't installed yet — "
                      f"setup.py --install-model {cfg['model']}")
            return 0

    if "--target" in argv:
        i = argv.index("--target")
        target = argv[i + 1] if i + 1 < len(argv) else ""
        if target not in UPLOAD_TARGETS:
            print(f"Unknown target '{target}'. Choose one of: {', '.join(UPLOAD_TARGETS)}")
            return 1
        cfg["upload_target"] = target
        apply_params(cfg, target, argv[i + 2:])
        save_config(cfg)
        print(f"Upload target set to: {target}")
        print_config(cfg)
        if target == "notion" and not cfg["notion"].get("parent_page_id"):
            print("Note: set a parent page — setup.py --target notion parent_page_id=<id>")
            print("      and connect the Notion MCP in your Claude Code.")
        if target == "confluence":
            print("Note: export CONFLUENCE_TOKEN and CONFLUENCE_USER for uploads.")
        return 0

    # No action flags: report status.
    language = cfg.get("language", "auto")
    ok = deps_status(language, cfg.get("model", ""))
    print()
    print_config(cfg)
    if not find_model(language, cfg.get("model", "")):
        print("\nNo whisper model installed. Pick one with:  setup.py --list-models")
        print("then e.g.  setup.py --install-model small")
    if not ok:
        print("\nInstall the missing dependencies above, then re-run /echogram:setup.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
