#!/usr/bin/env python3
"""Offline test suite for the telemetro plugin (stdlib unittest only).

Docker/podman and network sockets are mocked, so these run with no container
runtime and no listeners. Run from anywhere:

    python3 plugins/telemetro/tests/test_telemetro.py
"""
import io
import json
import os
import sys
import tempfile
import contextlib
import unittest

SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
sys.path.insert(0, SCRIPTS)

import common     # noqa: E402
import otel       # noqa: E402
import stack      # noqa: E402
import query      # noqa: E402
import inventory  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        os.environ["HOME"] = self.home
        os.environ["TELEMETRO_DATA_DIR"] = tempfile.mkdtemp()
        self.settings = os.path.join(self.home, ".claude", "settings.json")

    def tearDown(self):
        os.environ.pop("TELEMETRO_DATA_DIR", None)

    @staticmethod
    def run_capture(fn, *a, **k):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rv = fn(*a, **k)
        return rv, buf.getvalue()

    def read_settings(self):
        return common.load_json(self.settings, {})


class TestOtel(Base):
    def test_install_writes_env(self):
        rv, out = self.run_capture(otel.main, ["install"])
        self.assertEqual(rv, 0)
        env = self.read_settings()["env"]
        self.assertEqual(env["CLAUDE_CODE_ENABLE_TELEMETRY"], "1")
        self.assertEqual(env["OTEL_METRICS_EXPORTER"], "otlp")
        self.assertEqual(env["OTEL_EXPORTER_OTLP_ENDPOINT"], "http://localhost:4317")
        self.assertIn("Start a new Claude Code session", out)

    def test_install_custom_endpoint(self):
        self.run_capture(otel.main, ["install", "--endpoint", "http://otel.corp:4317"])
        env = self.read_settings()["env"]
        self.assertEqual(env["OTEL_EXPORTER_OTLP_ENDPOINT"], "http://otel.corp:4317")

    def test_install_preserves_other_settings(self):
        common.save_json(self.settings, {"theme": "dark", "env": {"FOO": "bar"}})
        self.run_capture(otel.main, ["install"])
        s = self.read_settings()
        self.assertEqual(s["theme"], "dark")
        self.assertEqual(s["env"]["FOO"], "bar")
        self.assertEqual(s["env"]["OTEL_METRICS_EXPORTER"], "otlp")

    def test_install_refuses_conflicts_without_force(self):
        common.save_json(self.settings, {"env": {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://other:4317"}})
        rv, out = self.run_capture(otel.main, ["install"])
        self.assertEqual(rv, 1)
        self.assertIn("different values", out)
        # unchanged
        self.assertEqual(self.read_settings()["env"]["OTEL_EXPORTER_OTLP_ENDPOINT"],
                         "http://other:4317")
        rv, _ = self.run_capture(otel.main, ["install", "--force"])
        self.assertEqual(rv, 0)
        self.assertEqual(self.read_settings()["env"]["OTEL_EXPORTER_OTLP_ENDPOINT"],
                         "http://localhost:4317")

    def test_remove_only_our_keys(self):
        common.save_json(self.settings, {"env": {"FOO": "bar"}})
        self.run_capture(otel.main, ["install"])
        rv, _ = self.run_capture(otel.main, ["remove"])
        self.assertEqual(rv, 0)
        env = self.read_settings()["env"]
        self.assertEqual(env, {"FOO": "bar"})     # ours gone, theirs kept

    def test_remove_drops_empty_env(self):
        self.run_capture(otel.main, ["install"])
        self.run_capture(otel.main, ["remove"])
        self.assertNotIn("env", self.read_settings())

    def test_status_states(self):
        _, out = self.run_capture(otel.main, ["status"])
        self.assertIn("not configured", out)
        self.run_capture(otel.main, ["install"])
        _, out = self.run_capture(otel.main, ["status"])
        self.assertIn("ENABLED", out)
        # partial: drop one key
        s = self.read_settings()
        del s["env"]["OTEL_LOGS_EXPORTER"]
        common.save_json(self.settings, s)
        _, out = self.run_capture(otel.main, ["status"])
        self.assertIn("PARTIAL", out)


class FakeRun:
    """Programmable subprocess.run replacement for the container CLI."""

    def __init__(self, responses):
        self.responses = responses      # list of (predicate, returncode, stdout)
        self.calls = []

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        for pred, rc, out in self.responses:
            if pred(cmd):
                return type("R", (), {"returncode": rc, "stdout": out})()
        return type("R", (), {"returncode": 0, "stdout": ""})()


class TestStack(Base):
    def setUp(self):
        super().setUp()
        self._run = stack.subprocess.run
        self._port = stack.port_in_use
        stack.port_in_use = lambda *a, **k: False

    def tearDown(self):
        stack.subprocess.run = self._run
        stack.port_in_use = self._port
        super().tearDown()

    def test_up_skips_when_listener_exists(self):
        stack.port_in_use = lambda port, **k: port == 4317
        fake = FakeRun([])
        stack.subprocess.run = fake
        rv, out = self.run_capture(stack.main, ["up"])
        self.assertEqual(rv, 0)
        self.assertIn("already running on port 4317", out)
        self.assertEqual(fake.calls, [])          # no docker calls at all

    def test_up_starts_container_when_absent(self):
        fake = FakeRun([
            (lambda c: c[1] == "info", 0, ""),
            (lambda c: c[1] == "inspect", 1, "no such container"),
            (lambda c: c[1] == "run", 0, "abc123"),
        ])
        stack.subprocess.run = fake
        rv, out = self.run_capture(stack.main, ["up"])
        self.assertEqual(rv, 0)
        run_cmd = next(c for c in fake.calls if c[1] == "run")
        self.assertIn(common.STACK_IMAGE, run_cmd)
        self.assertIn("4317:4317", " ".join(run_cmd))
        self.assertIn("Grafana:  http://localhost:3000", out)

    def test_up_restarts_stopped_container(self):
        fake = FakeRun([
            (lambda c: c[1] == "info", 0, ""),
            (lambda c: c[1] == "inspect", 0, "false\n"),
            (lambda c: c[1] == "start", 0, ""),
        ])
        stack.subprocess.run = fake
        rv, out = self.run_capture(stack.main, ["up"])
        self.assertEqual(rv, 0)
        self.assertIn("Restarted existing stack", out)
        self.assertFalse(any(c[1] == "run" for c in fake.calls))

    def test_up_no_runtime(self):
        fake = FakeRun([(lambda c: c[1] == "info", 1, "")])
        stack.subprocess.run = fake
        rv, out = self.run_capture(stack.main, ["up"])
        self.assertEqual(rv, 1)
        self.assertIn("No container runtime", out)

    def test_down_stop_and_rm(self):
        fake = FakeRun([
            (lambda c: c[1] == "info", 0, ""),
            (lambda c: c[1] == "inspect", 0, "true\n"),
        ])
        stack.subprocess.run = fake
        rv, out = self.run_capture(stack.main, ["down", "--rm"])
        self.assertEqual(rv, 0)
        ops = [c[1] for c in fake.calls]
        self.assertIn("stop", ops)
        self.assertIn("rm", ops)

    def test_status_reports(self):
        stack.port_in_use = lambda port, **k: port == 4318
        fake = FakeRun([
            (lambda c: c[1] == "info", 0, ""),
            (lambda c: c[1] == "inspect", 0, "true\n"),
        ])
        stack.subprocess.run = fake
        _, out = self.run_capture(stack.main, ["status"])
        self.assertIn("port 4318", out)
        self.assertIn("running", out)


class TestQuery(Base):
    def setUp(self):
        super().setUp()
        self._get = query._get

    def tearDown(self):
        query._get = self._get
        super().tearDown()

    def test_summary_digest_from_mocked_backends(self):
        def fake_get(url, timeout=15):
            if "label/__name__/values" in url:
                return {"status": "success",
                        "data": ["claude_code_token_usage_tokens_total", "up"]}
            if "/api/v1/query?" in url:
                return {"status": "success", "data": {"result": [
                    {"metric": {"type": "input", "model": "opus"},
                     "value": [0, "1200"]},
                    {"metric": {"type": "output", "model": "opus"},
                     "value": [0, "300"]},
                ]}}
            if "loki/api/v1/query_range" in url:
                line = lambda d: json.dumps(d)  # noqa: E731
                return {"data": {"result": [{
                    "stream": {"service_name": "claude-code"},
                    "values": [
                        ["1", line({"event.name": "claude_code.tool_decision",
                                    "decision": "reject", "source": "hook",
                                    "tool_name": "Bash"})],
                        ["2", line({"event.name": "claude_code.tool_decision",
                                    "decision": "accept", "source": "user_temporary",
                                    "tool_name": "WebFetch"})],
                        ["3", line({"event.name": "claude_code.tool_result",
                                    "tool_name": "Skill"})],
                        ["4", line({"event.name": "claude_code.api_error",
                                    "error": "overloaded"})],
                    ]}]}}
            raise AssertionError("unexpected url " + url)

        query._get = fake_get
        rv, out = self.run_capture(query.main, ["summary", "--hours", "24"])
        self.assertEqual(rv, 0)
        self.assertIn("claude_code_token_usage_tokens_total", out)
        self.assertIn("type=input", out)               # token breakdown
        self.assertNotIn("- up:", out)                 # non-claude metric skipped
        self.assertIn("reject (hook): 1", out)         # guardrail fired
        self.assertIn("accept (user_temporary): 1", out)  # allowlist candidate
        self.assertIn("used:Skill", out)
        self.assertIn("overloaded", out)

    def test_summary_unreachable_stack(self):
        def fail(url, timeout=15):
            raise OSError("connection refused")
        query._get = fail
        rv, out = self.run_capture(query.main, ["summary"])
        self.assertEqual(rv, 1)
        self.assertIn("Cannot reach the monitoring stack", out)
        self.assertIn("/telemetro:init", out)

    def test_summary_empty_data(self):
        def empty(url, timeout=15):
            if "label/__name__/values" in url:
                return {"status": "success", "data": []}
            return {"data": {"result": []}}
        query._get = empty
        rv, out = self.run_capture(query.main, ["summary"])
        self.assertEqual(rv, 0)
        self.assertIn("no claude_code metrics", out)
        self.assertIn("no claude_code log events", out)


class TestEventClassification(Base):
    def _digest(self, events):
        return "\n".join(query.events_digest(events))

    def test_skill_agent_mcp_attribution(self):
        events = [
            {"event.name": "claude_code.tool_result", "tool_name": "Skill",
             "tool_parameters": json.dumps({"skill_name": "echogram:start"})},
            {"event.name": "claude_code.tool_result", "tool_name": "Task",
             "tool_parameters": json.dumps({"subagent_type": "code-reviewer"})},
            {"event.name": "claude_code.tool_result",
             "tool_name": "mcp__memory__create_entities"},
            {"event.name": "claude_code.tool_result",
             "tool_name": "mcp__memory__search_nodes"},
        ]
        out = self._digest(events)
        self.assertIn("skills invoked", out)
        self.assertIn("echogram:start: 1", out)
        self.assertIn("subagents spawned", out)
        self.assertIn("code-reviewer: 1", out)
        self.assertIn("MCP servers used", out)
        self.assertIn("memory: 2", out)

    def test_tool_failures_counted(self):
        events = [
            {"event.name": "claude_code.tool_result", "tool_name": "Bash",
             "success": "false"},
            {"event.name": "claude_code.tool_result", "tool_name": "Bash",
             "success": "true"},
        ]
        out = self._digest(events)
        self.assertIn("tool failures", out)
        self.assertIn("Bash: 1", out)

    def test_params_as_dict_and_garbage(self):
        events = [
            {"event.name": "claude_code.tool_result", "tool_name": "Skill",
             "tool_parameters": {"skill": "review"}},
            {"event.name": "claude_code.tool_result", "tool_name": "Skill",
             "tool_parameters": "not-json"},
        ]
        out = self._digest(events)          # must not raise
        self.assertIn("review: 1", out)
        self.assertIn("(unnamed): 1", out)


class TestInventory(Base):
    def _mk(self, *parts, content=""):
        path = os.path.join(*parts)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_full_inventory(self):
        proj = tempfile.mkdtemp()
        self._mk(proj, ".claude", "skills", "deploy", "SKILL.md",
                 content="---\nname: deploy\n---\n")
        self._mk(self.home, ".claude", "skills", "notes", "SKILL.md",
                 content="---\nname: notes\n---\n")
        self._mk(proj, ".claude", "agents", "reviewer.md", content="# r")
        self._mk(proj, ".mcp.json",
                 content=json.dumps({"mcpServers": {
                     "memory-graph": {"command": "npx"},
                     "github": {"url": "https://x"}}}))
        self._mk(proj, "CLAUDE.md", content="# rules")

        rv, out = self.run_capture(inventory.main, ["--project", proj])
        self.assertEqual(rv, 0)
        self.assertIn("deploy  [project]", out)
        self.assertIn("notes  [user]", out)
        self.assertIn("reviewer  [project]", out)
        self.assertIn("memory-graph (stdio)  ← memory-type", out)
        self.assertIn("github (remote)", out)
        self.assertIn("[project] " + os.path.join(proj, "CLAUDE.md"), out)

    def test_empty_project(self):
        proj = tempfile.mkdtemp()
        rv, out = self.run_capture(inventory.main, ["--project", proj])
        self.assertEqual(rv, 0)
        self.assertIn("(none found)", out)
        self.assertIn("(no CLAUDE.md at any tier)", out)


class TestCommon(Base):
    def test_managed_keys_match_env(self):
        self.assertEqual(set(common.MANAGED_KEYS), set(common.otel_env().keys()))

    def test_port_in_use_real_socket(self):
        import socket
        srv = socket.socket()
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        port = srv.getsockname()[1]
        try:
            self.assertTrue(common.port_in_use(port))
        finally:
            srv.close()
        self.assertFalse(common.port_in_use(port))


if __name__ == "__main__":
    unittest.main(verbosity=2)
