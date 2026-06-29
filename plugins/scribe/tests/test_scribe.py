#!/usr/bin/env python3
"""Offline test suite for the scribe plugin (stdlib unittest only).

ffmpeg, whisper.cpp and all subprocess/signal calls are mocked, so these run
with no audio hardware and no external tools. Run from anywhere:

    python3 plugins/scribe/tests/test_scribe.py
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
import setup as setup_mod  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["SCRIBE_DATA_DIR"] = self.tmp

    def tearDown(self):
        os.environ.pop("SCRIBE_DATA_DIR", None)
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
        record.subprocess.Popen = FakePopen
        record.which = lambda n: "/usr/bin/ffmpeg"

    def tearDown(self):
        record.subprocess.Popen = self._popen
        record.which = self._which
        super().tearDown()

    def test_start_records_and_builds_cmd(self):
        rv, _ = self.run_capture(record.cmd_start, ["Sprint", "planning"])
        self.assertEqual(rv, 0)
        active = common.load_active()
        self.assertEqual(active["pid"], 4321)
        self.assertEqual(active["title"], "Sprint planning")
        cmd = FakePopen.instances[0].cmd
        self.assertIn("/usr/bin/ffmpeg", cmd)
        self.assertEqual(cmd[-3:], ["-ar", "16000", active["audio_path"]])

    def test_no_double_start(self):
        self.run_capture(record.cmd_start, ["one"])
        rv, out = self.run_capture(record.cmd_start, ["two"])
        self.assertEqual(rv, 1)
        self.assertIn("already being recorded", out)

    def test_start_without_ffmpeg(self):
        record.which = lambda n: None
        rv, out = self.run_capture(record.cmd_start, [])
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


class TestTranscribe(Base):
    def test_build_command(self):
        cmd = transcribe.build_command("/w/whisper-cli", "/m/ggml-base.en.bin",
                                       "/a/audio.wav", "/a/transcript")
        self.assertEqual(cmd[:3], ["/w/whisper-cli", "-m", "/m/ggml-base.en.bin"])
        self.assertIn("-otxt", cmd)
        self.assertIn("/a/transcript", cmd)

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
        transcribe.find_model = lambda: "/m/ggml-base.en.bin"

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
        transcribe.find_model = lambda: None
        rv, out = self.run_capture(transcribe.transcribe, mdir)
        self.assertEqual(rv, 1)
        self.assertIn("whisper.cpp not found", out)


class TestSetup(Base):
    def test_target_local(self):
        rv, _ = self.run_capture(setup_mod.main, ["--target", "local"])
        self.assertEqual(rv, 0)
        self.assertEqual(common.load_config()["upload_target"], "local")

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
