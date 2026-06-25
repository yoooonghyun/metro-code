#!/usr/bin/env python3
"""Offline test suite for the seekerizer plugin (stdlib unittest only).

Network access (Yahoo Finance) is mocked, so these run deterministically with
no internet and no live market data. Run from anywhere:

    python3 plugins/seekerizer/tests/test_seekerizer.py
    # or
    python3 -m unittest discover -s plugins/seekerizer/tests
"""
import io
import os
import sys
import tempfile
import contextlib
import unittest

SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
sys.path.insert(0, SCRIPTS)

import common  # noqa: E402
import manage  # noqa: E402
import targets  # noqa: E402
import statusline  # noqa: E402
import monitor  # noqa: E402
import setup as setup_mod  # noqa: E402

# Canned quotes: symbol -> (price, prev_close, name) or None for "not found".
FAKE = {
    "AAPL": (294.30, 297.0, "Apple Inc."),
    "005930.KS": (338500.0, 310000.0, "Samsung Electronics Co., Ltd."),
    "NVDA": (200.04, 208.0, "NVIDIA Corporation"),
}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["SEEKERIZER_DATA_DIR"] = os.path.join(self.tmp, "data")
        # Mock the single network entry point; everything routes through it.
        self.calls = {}

        def fake_fetch(sym):
            self.calls[sym] = self.calls.get(sym, 0) + 1
            return FAKE.get(sym)

        self._orig_fetch = common.fetch_quote
        common.fetch_quote = fake_fetch

        # manage.validate has its own request; mock it too.
        self._orig_validate = manage.validate

        def fake_validate(sym):
            q = FAKE.get(sym)
            return (q is not None, q[2] if q else None)

        manage.validate = fake_validate

    def tearDown(self):
        common.fetch_quote = self._orig_fetch
        manage.validate = self._orig_validate
        os.environ.pop("SEEKERIZER_DATA_DIR", None)

    @staticmethod
    def run_capture(fn, *a, **k):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rv = fn(*a, **k)
        return rv, buf.getvalue()


class TestHelpers(Base):
    def test_clean_name(self):
        self.assertEqual(common.clean_name("Samsung Electronics Co., Ltd."), "Samsung Electronics")
        self.assertEqual(common.clean_name("NVIDIA Corporation"), "NVIDIA")
        self.assertEqual(common.clean_name("Apple Inc."), "Apple")
        self.assertEqual(common.clean_name("Bitcoin USD"), "Bitcoin USD")

    def test_currency(self):
        self.assertEqual(common.currency_for("005930.KS"), "₩")
        self.assertEqual(common.currency_for("7203.T"), "¥")
        self.assertEqual(common.currency_for("AAPL"), "$")

    def test_format_price(self):
        self.assertEqual(common.format_price("005930.KS", 338500.0), "₩338,500")
        self.assertEqual(common.format_price("AAPL", 294.3), "$294.30")

    def test_display_name_priority(self):
        q = {"name": "Apple Inc."}
        self.assertEqual(common.display_name("AAPL", q, "내사과"), "내사과")   # alias wins
        self.assertEqual(common.display_name("AAPL", q), "Apple")             # then company
        self.assertEqual(common.display_name("AAPL", {}), "AAPL")            # then symbol

    def test_is_touched(self):
        self.assertTrue(common.is_touched({"price": 100, "direction": "above"}, 120))
        self.assertFalse(common.is_touched({"price": 100, "direction": "above"}, 90))
        self.assertTrue(common.is_touched({"price": 100, "direction": "below"}, 90))
        self.assertFalse(common.is_touched({"price": 100, "direction": "below"}, 120))


class TestQuotesCache(Base):
    def test_cache_reuse_no_refetch(self):
        common.get_quotes(["AAPL", "NVDA"])
        common.get_quotes(["AAPL", "NVDA"])      # within TTL -> served from cache
        self.assertEqual(self.calls, {"AAPL": 1, "NVDA": 1})

    def test_expired_refetches(self):
        common.get_quotes(["AAPL"])
        common.get_quotes(["AAPL"], ttl=0)       # force-stale -> refetch
        self.assertEqual(self.calls["AAPL"], 2)

    def test_keep_last_on_failure(self):
        common.get_quotes(["AAPL"])              # cached
        common.fetch_quote = lambda s: None      # now fail
        q = common.get_quotes(["AAPL"], ttl=0)
        self.assertEqual(q["AAPL"]["price"], 294.30)   # last known kept

    def test_name_cached_with_quote(self):
        q = common.get_quotes(["005930.KS"])
        self.assertEqual(q["005930.KS"]["name"], "Samsung Electronics Co., Ltd.")


class TestManage(Base):
    def test_add_and_list(self):
        self.run_capture(manage.cmd_add, ["AAPL", "BADSYM", "005930.KS"])
        self.assertEqual(common.load_tickers(), ["AAPL", "005930.KS"])  # BADSYM rejected

    def test_alias_unalias(self):
        self.run_capture(manage.cmd_alias, ["005930.KS", "삼성전자"])
        self.assertEqual(common.load_aliases()["005930.KS"], "삼성전자")
        self.run_capture(manage.cmd_unalias, ["005930.KS"])
        self.assertNotIn("005930.KS", common.load_aliases())

    def test_remove_cascades_alias_and_warns_target(self):
        common.save_tickers(["005930.KS"])
        common.save_aliases({"005930.KS": "삼성전자"})
        common.save_targets({"005930.KS": {"price": 1, "direction": "above", "fired": False}})
        _, out = self.run_capture(manage.cmd_remove, ["005930.KS"])
        self.assertEqual(common.load_tickers(), [])
        self.assertNotIn("005930.KS", common.load_aliases())     # alias cascaded
        self.assertIn("still has a price target", out)           # target warning


class TestTargets(Base):
    def test_set_autodetect_direction(self):
        self.run_capture(targets.cmd_set, ["AAPL", "100"])       # 100 < 294 -> below
        self.assertEqual(common.load_targets()["AAPL"]["direction"], "below")
        self.run_capture(targets.cmd_set, ["AAPL", "999"])       # 999 > 294 -> above
        self.assertEqual(common.load_targets()["AAPL"]["direction"], "above")

    def test_set_rejects_bad_symbol_and_price(self):
        rv, _ = self.run_capture(targets.cmd_set, ["BADSYM", "100"])
        self.assertEqual(rv, 1)
        rv, _ = self.run_capture(targets.cmd_set, ["AAPL", "notnum"])
        self.assertEqual(rv, 1)

    def test_remove_clear(self):
        self.run_capture(targets.cmd_set, ["AAPL", "100"])
        self.run_capture(targets.cmd_remove, ["AAPL"])
        self.assertEqual(common.load_targets(), {})


class TestStatusline(Base):
    def test_empty(self):
        out = statusline.render([], {}, {})
        self.assertIn("📈", out)

    def test_render_name_color_bell(self):
        common.save_tickers(["005930.KS", "AAPL"])
        quotes = common.get_quotes(["005930.KS", "AAPL"])
        targets_d = {"005930.KS": {"price": 1, "direction": "above", "fired": False}}
        out = statusline.render(["005930.KS", "AAPL"], quotes, targets_d, {"AAPL": "애플"})
        self.assertIn("Samsung Electronics", out)   # company name (numeric ticker)
        self.assertIn("애플", out)                   # alias
        self.assertIn("🔔", out)                     # touched target marker
        self.assertIn(statusline.RED, out)          # 005930.KS up -> red
        self.assertIn(statusline.BLUE, out)         # AAPL down -> blue


class TestMonitor(Base):
    def test_fires_once(self):
        common.save_tickers(["AAPL"])
        common.save_targets({"AAPL": {"price": 100, "direction": "above", "fired": False}})
        _, out1 = self.run_capture(monitor.check_once)
        self.assertIn("touched target", out1)
        self.assertTrue(common.load_targets()["AAPL"]["fired"])
        _, out2 = self.run_capture(monitor.check_once)
        self.assertEqual(out2.strip(), "")          # silent after firing

    def test_shared_cache_dedup(self):
        common.save_tickers(["AAPL", "NVDA"])
        common.save_targets({"NVDA": {"price": 9e9, "direction": "above", "fired": False}})
        self.run_capture(monitor.check_once)        # monitor warms cache
        statusline.render(["AAPL", "NVDA"], common.get_quotes(["AAPL", "NVDA"]), {}, {})
        self.run_capture(monitor.check_once)
        self.assertEqual(self.calls, {"AAPL": 1, "NVDA": 1})  # one fetch each, ever


class TestSetup(Base):
    def setUp(self):
        super().setUp()
        self.home = tempfile.mkdtemp()
        os.environ["HOME"] = self.home
        self.settings = os.path.join(self.home, ".claude", "settings.json")

    def test_install_status_remove(self):
        rv, _ = self.run_capture(setup_mod.main, ["--global"])
        self.assertEqual(rv, 0)
        s = setup_mod.load_settings(self.settings)
        self.assertIn("statusline.py", s["statusLine"]["command"])
        _, out = self.run_capture(setup_mod.main, ["--status-only"])
        self.assertIn("installed", out)
        self.run_capture(setup_mod.main, ["--remove"])
        self.assertNotIn("statusLine", setup_mod.load_settings(self.settings))

    def test_refuses_foreign_statusline(self):
        setup_mod.save_settings(self.settings, {"statusLine": {"type": "command", "command": "other"}})
        rv, out = self.run_capture(setup_mod.main, ["--global"])
        self.assertEqual(rv, 1)
        self.assertIn("different statusLine", out)

    def test_update_refreshes_path(self):
        setup_mod.save_settings(self.settings, {
            "theme": "dark",
            "statusLine": {"type": "command",
                           "command": 'python3 "/old/cache/v1/scripts/statusline.py"'},
        })
        rv, out = self.run_capture(setup_mod.main, ["--update"])
        self.assertEqual(rv, 0)
        self.assertIn("Updated", out)
        s = setup_mod.load_settings(self.settings)
        self.assertEqual(s["statusLine"]["command"], setup_mod.desired_command())
        self.assertEqual(s["theme"], "dark")        # other settings preserved


if __name__ == "__main__":
    unittest.main(verbosity=2)
