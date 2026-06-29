#!/usr/bin/env python3
"""Offline test suite for the echogram plugin (stdlib unittest only).

ffmpeg, whisper.cpp and all subprocess/signal calls are mocked, so these run
with no audio hardware and no external tools. Run from anywhere:

    python3 plugins/echogram/tests/test_echogram.py
"""
import io
import os
import sys
import tempfile
import contextlib
import unittest

SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
sys.path.insert(0, SCRIPTS)

import common      # noqa: E402
import record      # noqa: E402
import transcribe  # noqa: E402
import monitor     # noqa: E402
import setup as setup_mod  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["ECHOGRAM_DATA_DIR"] = self.tmp

    def tearDown(self):
        os.environ.pop("ECHOGRAM_DATA_DIR", None)
        for v in ("WHISPER_BIN", "WHISPER_MODEL"):
            os.environ.pop(v, None)

    @staticmethod
    def run_capture(fn, *a, **k):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rv = fn(*a, **k)
        return rv, buf.getvalue()


class TestCommon(Base):
    def test_config_defaults_and_merge(self):
        cfg = common.load_config()
        self.assertEqual(cfg["upload_target"], "local")
        cfg["upload_target"] = "notion"
        cfg["notion"]["parent_page_id"] = "abc"
        common.save_config(cfg)
        reloaded = common.load_config()
        self.assertEqual(reloaded["upload_target"], "notion")
        self.assertEqual(reloaded["notion"]["parent_page_id"], "abc")
        self.assertIn("confluence", reloaded)        # defaults still present

    def test_active_roundtrip(self):
        self.assertIsNone(common.load_active())
        common.save_active({"id": "x", "pid": 1})
        self.assertEqual(common.load_active()["id"], "x")
        common.clear_active()
        self.assertIsNone(common.load_active())

    def test_meetings_listed_newest_first(self):
        common.save_meta("20260101-090000", {"id": "20260101-090000", "started_at": "2026-01-01T09:00:00"})
        common.save_meta("20260102-090000", {"id": "20260102-090000", "started_at": "2026-01-02T09:00:00"})
        ids = [m["id"] for m in common.list_meetings()]
        self.assertEqual(ids[0], "20260102-090000")

    def test_input_args_platform(self):
        orig = common.sys.platform
        try:
            common.sys.platform = "darwin"
            self.assertEqual(common.ffmpeg_input_args(), ["-f", "avfoundation", "-i", ":default"])
            self.assertEqual(common.ffmpeg_input_args({"audio_input": ":1"})[-1], ":1")
            common.sys.platform = "linux"
            self.assertEqual(common.ffmpeg_input_args(), ["-f", "pulse", "-i", "default"])
        finally:
            common.sys.platform = orig


class FakePopen:
    instances = []

    def __init__(self, cmd, **kw):
        self.cmd = cmd
        self.pid = 4321
        FakePopen.instances.append(self)


class TestRecord(Base):
    def setUp(self):
        super().setUp()
        FakePopen.instances = []
        self._popen = record.subprocess.Popen
        self._which = record.which
        self._fsb = record.find_stream_binary
        self._fm = record.find_model
        record.subprocess.Popen = FakePopen
        record.which = lambda n: "/usr/bin/ffmpeg"
        # Default: live tooling absent, so the default mode falls back to batch.
        record.find_stream_binary = lambda *a, **k: None
        record.find_model = lambda *a, **k: None

    def tearDown(self):
        record.subprocess.Popen = self._popen
        record.which = self._which
        record.find_stream_binary = self._fsb
        record.find_model = self._fm
        super().tearDown()

    def test_batch_flag_builds_ffmpeg_cmd(self):
        rv, _ = self.run_capture(record.cmd_start, ["--batch", "Sprint", "planning"])
        self.assertEqual(rv, 0)
        active = common.load_active()
        self.assertEqual(active["mode"], "batch")
        self.assertEqual(active["title"], "Sprint planning")
        cmd = FakePopen.instances[0].cmd
        self.assertIn("/usr/bin/ffmpeg", cmd)
        self.assertEqual(cmd[-3:], ["-ar", "16000", active["audio_path"]])

    def test_default_is_live_when_available(self):
        record.find_stream_binary = lambda *a, **k: "/usr/bin/whisper-stream"
        record.find_model = lambda *a, **k: "/m/ggml-base.en.bin"
        rv, _ = self.run_capture(record.cmd_start, ["Standup"])   # no flags
        self.assertEqual(rv, 0)
        self.assertEqual(common.load_active()["mode"], "live")

    def test_default_falls_back_to_batch(self):
        # stream tooling missing (setUp default) -> default start uses batch
        rv, out = self.run_capture(record.cmd_start, ["Standup"])
        self.assertEqual(rv, 0)
        self.assertEqual(common.load_active()["mode"], "batch")
        self.assertIn("Live mode unavailable", out)

    def test_no_double_start(self):
        self.run_capture(record.cmd_start, ["--batch", "one"])
        rv, out = self.run_capture(record.cmd_start, ["--batch", "two"])
        self.assertEqual(rv, 1)
        self.assertIn("already being recorded", out)

    def test_start_without_ffmpeg(self):
        record.which = lambda n: None
        rv, out = self.run_capture(record.cmd_start, ["--batch"])
        self.assertEqual(rv, 1)
        self.assertIsNone(common.load_active())
        self.assertIn("ffmpeg not found", out)

    def test_stop_finalizes_and_clears(self):
        self.run_capture(record.cmd_start, ["demo"])
        active = common.load_active()
        # pretend audio was captured
        with open(active["audio_path"], "wb") as f:
            f.write(b"RIFFfake")
        record._terminate = lambda pid, timeout=6.0: None   # don't signal real pids
        rv, out = self.run_capture(record.cmd_stop, [])
        self.assertEqual(rv, 0)
        self.assertIsNone(common.load_active())
        self.assertIn("MEETING_DIR:", out)
        meta = common.load_meta(active["id"])
        self.assertTrue(meta.get("ended_at"))

    def test_stop_without_active(self):
        rv, out = self.run_capture(record.cmd_stop, [])
        self.assertEqual(rv, 1)
        self.assertIn("No meeting", out)

    def test_start_live_builds_stream_cmd(self):
        record.find_stream_binary = lambda *a, **k: "/usr/bin/whisper-stream"
        record.find_model = lambda *a, **k: "/m/ggml-base.en.bin"
        rv, _ = self.run_capture(record.cmd_start, ["--live", "Daily", "standup"])
        self.assertEqual(rv, 0)
        active = common.load_active()
        self.assertEqual(active["mode"], "live")
        self.assertTrue(os.path.exists(active["transcript_path"]))
        cmd = FakePopen.instances[0].cmd
        self.assertIn("/usr/bin/whisper-stream", cmd)
        self.assertEqual(cmd[cmd.index("-f") + 1], active["transcript_path"])
        # the title must not keep the --live flag
        self.assertEqual(active["title"], "Daily standup")

    def test_start_live_missing_stream(self):
        record.find_stream_binary = lambda *a, **k: None
        record.find_model = lambda *a, **k: "/m/x.bin"
        rv, out = self.run_capture(record.cmd_start, ["--live"])
        self.assertEqual(rv, 1)
        self.assertIsNone(common.load_active())
        self.assertIn("whisper-stream", out)

    def test_stop_live_uses_transcript(self):
        record.find_stream_binary = lambda *a, **k: "/usr/bin/whisper-stream"
        record.find_model = lambda *a, **k: "/m/x.bin"
        self.run_capture(record.cmd_start, ["--live", "demo"])
        active = common.load_active()
        with open(active["transcript_path"], "w", encoding="utf-8") as f:
            f.write("live recognized text")
        record._terminate = lambda pid, timeout=6.0: None
        rv, out = self.run_capture(record.cmd_stop, [])
        self.assertEqual(rv, 0)
        self.assertIn("TRANSCRIPT:", out)
        self.assertEqual(common.load_meta(active["id"])["mode"], "live")


class TestMonitor(Base):
    def test_emits_only_new_text_for_live(self):
        mdir = common.meeting_dir("live1")
        tpath = os.path.join(mdir, "transcript.txt")
        open(tpath, "w").close()
        common.save_active({"id": "live1", "title": "T", "mode": "live",
                            "dir": mdir, "transcript_path": tpath})
        state = {"id": None, "emitted": 0}

        with open(tpath, "w", encoding="utf-8") as f:
            f.write("hello\n")
        _, out1 = self.run_capture(monitor.check_once, state)
        self.assertIn("started", out1)
        self.assertIn("📝 hello", out1)

        _, out2 = self.run_capture(monitor.check_once, state)   # nothing new
        self.assertNotIn("hello", out2)

        with open(tpath, "a", encoding="utf-8") as f:
            f.write("world\n")
        _, out3 = self.run_capture(monitor.check_once, state)
        self.assertIn("📝 world", out3)
        self.assertNotIn("hello", out3)

    def test_idle_when_no_live_meeting(self):
        state = {"id": "x", "emitted": 5}
        _, out = self.run_capture(monitor.check_once, state)
        self.assertEqual(out.strip(), "")
        self.assertIsNone(state["id"])

    def test_ignores_batch_meeting(self):
        common.save_active({"id": "b1", "mode": "batch", "dir": common.meeting_dir("b1")})
        state = {"id": None, "emitted": 0}
        _, out = self.run_capture(monitor.check_once, state)
        self.assertEqual(out.strip(), "")


class TestTranscribe(Base):
    def test_build_command(self):
        cmd = transcribe.build_command("/w/whisper-cli", "/m/ggml-base.en.bin",
                                       "/a/audio.wav", "/a/transcript")
        self.assertEqual(cmd[:3], ["/w/whisper-cli", "-m", "/m/ggml-base.en.bin"])
        self.assertIn("-otxt", cmd)
        self.assertIn("/a/transcript", cmd)

    def test_commands_pass_language(self):
        c = transcribe.build_command("b", "m", "w", "o", "ko")
        self.assertEqual(c[c.index("-l") + 1], "ko")
        s = transcribe.build_stream_command("b", "m", "t", "ko")
        self.assertEqual(s[s.index("-l") + 1], "ko")
        # default is auto, not English
        self.assertEqual(transcribe.build_command("b", "m", "w", "o")[
            transcribe.build_command("b", "m", "w", "o").index("-l") + 1], "auto")

    def test_model_selection_language_aware(self):
        md = tempfile.mkdtemp()
        for n in ("ggml-base.en.bin", "ggml-base.bin"):
            open(os.path.join(md, n), "w").close()
        orig = transcribe.MODEL_DIRS
        transcribe.MODEL_DIRS = [md]
        try:
            self.assertTrue(transcribe.find_model("en").endswith("ggml-base.en.bin"))
            self.assertTrue(transcribe.find_model("ko").endswith("ggml-base.bin"))
            self.assertTrue(transcribe.find_model("auto").endswith("ggml-base.bin"))
        finally:
            transcribe.MODEL_DIRS = orig

    def test_english_only_model_rejected_for_korean(self):
        md = tempfile.mkdtemp()
        open(os.path.join(md, "ggml-base.en.bin"), "w").close()
        orig = transcribe.MODEL_DIRS
        transcribe.MODEL_DIRS = [md]
        try:
            self.assertIsNone(transcribe.find_model("ko"))   # .en can't do Korean
            self.assertTrue(transcribe.find_model("en"))
        finally:
            transcribe.MODEL_DIRS = orig

    def test_find_binary_and_model_from_env(self):
        b = os.path.join(self.tmp, "whisper-cli"); open(b, "w").close()
        m = os.path.join(self.tmp, "ggml-base.en.bin"); open(m, "w").close()
        os.environ["WHISPER_BIN"] = b
        os.environ["WHISPER_MODEL"] = m
        self.assertEqual(transcribe.find_binary(), b)
        self.assertEqual(transcribe.find_model(), m)

    def test_transcribe_success(self):
        mdir = common.meeting_dir("m1")
        wav = os.path.join(mdir, "audio.wav")
        with open(wav, "wb") as f:
            f.write(b"RIFFfake")
        transcribe.find_binary = lambda: "/w/whisper-cli"
        transcribe.find_model = lambda *a, **k: "/m/ggml-base.en.bin"

        def fake_run(cmd, **kw):
            out_base = cmd[cmd.index("-of") + 1]
            with open(out_base + ".txt", "w", encoding="utf-8") as f:
                f.write("hello world from the meeting")
            return type("R", (), {"returncode": 0, "stderr": b""})()

        orig = transcribe.subprocess.run
        transcribe.subprocess.run = fake_run
        try:
            rv, out = self.run_capture(transcribe.transcribe, mdir)
        finally:
            transcribe.subprocess.run = orig
        self.assertEqual(rv, 0)
        self.assertIn("TRANSCRIPT:", out)
        self.assertTrue(os.path.exists(os.path.join(mdir, "transcript.txt")))

    def test_transcribe_missing_tools(self):
        mdir = common.meeting_dir("m2")
        with open(os.path.join(mdir, "audio.wav"), "wb") as f:
            f.write(b"x")
        transcribe.find_binary = lambda: None
        transcribe.find_model = lambda *a, **k: None
        rv, out = self.run_capture(transcribe.transcribe, mdir)
        self.assertEqual(rv, 1)
        self.assertIn("whisper.cpp not found", out)


class TestSetup(Base):
    def test_target_local(self):
        rv, _ = self.run_capture(setup_mod.main, ["--target", "local"])
        self.assertEqual(rv, 0)
        self.assertEqual(common.load_config()["upload_target"], "local")

    def test_language_setting(self):
        rv, _ = self.run_capture(setup_mod.main, ["--language", "ko"])
        self.assertEqual(rv, 0)
        self.assertEqual(common.load_config()["language"], "ko")

    def test_target_notion_with_param(self):
        self.run_capture(setup_mod.main, ["--target", "notion", "parent_page_id=PAGE1"])
        cfg = common.load_config()
        self.assertEqual(cfg["upload_target"], "notion")
        self.assertEqual(cfg["notion"]["parent_page_id"], "PAGE1")

    def test_target_confluence_params(self):
        self.run_capture(setup_mod.main, [
            "--target", "confluence", "base_url=https://x/wiki",
            "space_key=ENG", "parent_page_id=42"])
        c = common.load_config()["confluence"]
        self.assertEqual((c["base_url"], c["space_key"], c["parent_page_id"]),
                         ("https://x/wiki", "ENG", "42"))

    def test_unknown_target(self):
        rv, out = self.run_capture(setup_mod.main, ["--target", "bogus"])
        self.assertEqual(rv, 1)
        self.assertIn("Unknown target", out)

    def test_audio_input_override(self):
        self.run_capture(setup_mod.main, ["--audio-input", ":2"])
        self.assertEqual(common.load_config()["audio_input"], ":2")


if __name__ == "__main__":
    unittest.main(verbosity=2)
