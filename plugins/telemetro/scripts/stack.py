#!/usr/bin/env python3
"""Manage the local Grafana monitoring stack for Claude Code telemetry.

Runs grafana/otel-lgtm — an all-in-one container bundling an OTLP collector,
Prometheus, Loki, Tempo and Grafana — so Claude Code's OTel export has somewhere
to land. `up` is idempotent and respects an existing setup: if something is
already listening on the OTLP ports (any collector — theirs or ours), no new
container is started.

Usage:
    stack.py up        # start the stack unless an OTLP listener already exists
    stack.py down      # stop (and remove) the telemetro container
    stack.py status    # report listener/container state

Requires Docker (or Podman). Grafana UI: http://localhost:3000 (anonymous
admin login enabled by the image).
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (  # noqa: E402
    STACK_IMAGE, CONTAINER_NAME, GRAFANA_PORT, OTLP_GRPC_PORT, OTLP_HTTP_PORT,
    port_in_use,
)

INSTALL_HINT = (
    "No container runtime found. Install Docker Desktop (macOS) or docker/podman\n"
    "(Linux), start it, then re-run /telemetro:init."
)


def runtime():
    """Return the container CLI to use ('docker' or 'podman'), or None."""
    for cli in ("docker", "podman"):
        try:
            r = subprocess.run([cli, "info"], stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=10)
            if r.returncode == 0:
                return cli
        except (OSError, subprocess.TimeoutExpired):
            continue
    return None


def _run(cli, *args, capture=True):
    return subprocess.run([cli, *args], text=True,
                          stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.STDOUT if capture else None)


def container_state(cli):
    """'running' | 'stopped' | 'absent' for our container."""
    r = _run(cli, "inspect", "-f", "{{.State.Running}}", CONTAINER_NAME)
    if r.returncode != 0:
        return "absent"
    return "running" if (r.stdout or "").strip() == "true" else "stopped"


def otlp_listener():
    """Port an OTLP listener is on, or None."""
    for port in (OTLP_GRPC_PORT, OTLP_HTTP_PORT):
        if port_in_use(port):
            return port
    return None


def cmd_up(argv):
    listener = otlp_listener()
    if listener:
        print(f"An OTLP listener is already running on port {listener} — "
              "using the existing monitoring setup, no container started.")
        print("Telemetry will flow there once installed (otel.py install).")
        return 0

    cli = runtime()
    if not cli:
        print(INSTALL_HINT)
        return 1

    state = container_state(cli)
    if state == "running":
        print(f"Stack already running ({CONTAINER_NAME}).")
    elif state == "stopped":
        r = _run(cli, "start", CONTAINER_NAME)
        if r.returncode != 0:
            print(f"Failed to start {CONTAINER_NAME}:\n{(r.stdout or '').strip()}")
            return 1
        print(f"Restarted existing stack ({CONTAINER_NAME}).")
    else:
        print(f"Starting {STACK_IMAGE} (first run pulls the image, ~a few min)…")
        r = _run(cli, "run", "-d", "--name", CONTAINER_NAME,
                 "-p", f"{GRAFANA_PORT}:3000",
                 "-p", f"{OTLP_GRPC_PORT}:4317",
                 "-p", f"{OTLP_HTTP_PORT}:4318",
                 STACK_IMAGE)
        if r.returncode != 0:
            print(f"Failed to start the stack:\n{(r.stdout or '').strip()}")
            return 1
        print(f"Started {CONTAINER_NAME}.")
    print(f"Grafana:  http://localhost:{GRAFANA_PORT}")
    print(f"OTLP in:  grpc://localhost:{OTLP_GRPC_PORT}  ·  http://localhost:{OTLP_HTTP_PORT}")
    return 0


def cmd_down(argv):
    cli = runtime()
    if not cli:
        print(INSTALL_HINT)
        return 1
    if container_state(cli) == "absent":
        print(f"No {CONTAINER_NAME} container exists. Nothing to stop.")
        return 0
    _run(cli, "stop", CONTAINER_NAME)
    if "--rm" in argv:
        _run(cli, "rm", CONTAINER_NAME)
        print(f"Stopped and removed {CONTAINER_NAME}.")
    else:
        print(f"Stopped {CONTAINER_NAME} (kept; `stack.py up` restarts it, --rm deletes).")
    return 0


def cmd_status(argv):
    listener = otlp_listener()
    print(f"OTLP listener: {'port ' + str(listener) if listener else 'none'}")
    cli = runtime()
    if not cli:
        print("Container runtime: none (docker/podman not available)")
        return 0
    print(f"Container runtime: {cli}")
    print(f"{CONTAINER_NAME}: {container_state(cli)}")
    if listener:
        print(f"Grafana (if ours): http://localhost:{GRAFANA_PORT}")
    return 0


COMMANDS = {"up": cmd_up, "down": cmd_down, "status": cmd_status}


def main(argv):
    if not argv or argv[0] not in COMMANDS:
        print(__doc__)
        return 2
    return COMMANDS[argv[0]](argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
