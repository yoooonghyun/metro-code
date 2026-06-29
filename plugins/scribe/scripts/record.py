#!/usr/bin/env python3
"""Start / stop / inspect a local meeting audio recording (ffmpeg).

`start` spawns ffmpeg as a detached process that keeps recording after this
script exits, and remembers it in active.json. `stop` signals that process to
finalize the file cleanly (SIGINT, the same as pressing 'q' in ffmpeg) and
records the meeting's metadata. The transcription + minutes steps are driven by
the `end` skill after `stop` returns.

Usage:
    record.py start [title...]
    record.py stop
    record.py status
"""
import os
import signal
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (  # noqa: E402
    load_active, save_active, clear_active, load_config, load_meta, save_meta,
    meeting_dir, list_meetings, ffmpeg_input_args, which, now_iso,
    new_meeting_id,
)

INSTALL_HINT = (
    "ffmpeg not found. Install it:\n"
    "  macOS:  brew install ffmpeg\n"
    "  Linux:  sudo apt-get install ffmpeg   (and a working mic via PulseAudio/ALSA)\n"
    "Then run /scribe:setup to verify."
)


def _alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _terminate(pid, timeout=6.0):
    """Ask ffmpeg to finalize (SIGINT); escalate to SIGTERM if it lingers."""
    if not pid or not _alive(pid):
        return
    try:
        os.kill(pid, signal.SIGINT)
    except OSError:
        return
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not _alive(pid):
            return
        time.sleep(0.1)
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass


def cmd_start(args):
    if load_active():
        print("A meeting is already being recorded. Run /scribe:end to finish it first.")
        return 1
    ffmpeg = which("ffmpeg")
    if not ffmpeg:
        print(INSTALL_HINT)
        return 1

    config = load_config()
    title = " ".join(args).strip() or "Untitled meeting"
    mid = new_meeting_id()
    mdir = meeting_dir(mid)
    audio_path = os.path.join(mdir, "audio.wav")
    log_path = os.path.join(mdir, "ffmpeg.log")

    cmd = [ffmpeg, "-hide_banner", "-loglevel", "warning", "-y",
           *ffmpeg_input_args(config), "-ac", "1", "-ar", "16000", audio_path]

    log = open(log_path, "ab")
    proc = subprocess.Popen(
        cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=log, start_new_session=True,
    )
    log.close()   # the child holds its own dup of the fd

    active = {
        "id": mid, "title": title, "started_at": now_iso(), "dir": mdir,
        "audio_path": audio_path, "log_path": log_path, "pid": proc.pid,
    }
    save_active(active)
    save_meta(mid, {k: active[k] for k in ("id", "title", "started_at", "dir", "audio_path")})

    print(f"🎙️  Recording: {title}")
    print(f"   id {mid}  ·  {audio_path}")
    print("   Run /scribe:end when the meeting is over.")
    return 0


def cmd_stop(args):
    active = load_active()
    if not active:
        print("No meeting is being recorded.")
        return 1

    _terminate(active.get("pid"))
    ended = now_iso()
    meta = load_meta(active["id"]) or {}
    meta.update({
        "id": active["id"], "title": active.get("title"),
        "started_at": active.get("started_at"), "ended_at": ended,
        "dir": active.get("dir"), "audio_path": active.get("audio_path"),
    })
    save_meta(active["id"], meta)
    clear_active()

    have_audio = os.path.exists(active.get("audio_path", "")) and \
        os.path.getsize(active["audio_path"]) > 0
    print(f"⏹️  Stopped: {active.get('title')}")
    print(f"   started {active.get('started_at')}  ended {ended}")
    if not have_audio:
        print("   WARNING: no audio captured — check mic permission and ffmpeg.log.")
    # Machine-readable line so the end skill knows where to transcribe.
    print(f"MEETING_DIR: {active.get('dir')}")
    return 0


def cmd_status(args):
    active = load_active()
    if active:
        print(f"🎙️  Recording now: {active.get('title')} (id {active.get('id')}, "
              f"since {active.get('started_at')})")
    else:
        print("No active recording.")
    recent = list_meetings()[:5]
    if recent:
        print("Recent meetings:")
        for m in recent:
            done = "✓" if m.get("ended_at") else "…"
            print(f"  {done} {m.get('id')}  {m.get('title')}")
    return 0


COMMANDS = {"start": cmd_start, "stop": cmd_stop, "status": cmd_status}


def main(argv):
    if not argv or argv[0] not in COMMANDS:
        print(__doc__)
        return 2
    return COMMANDS[argv[0]](argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
