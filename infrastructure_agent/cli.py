"""Command-line interface for running the automation agent."""

from __future__ import annotations

import argparse
import json
import signal
import sys
from typing import Optional

from .agent import AutomationAgent
from .config import ConfigError, load_config
from .dashboard import DashboardServer


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Infrastructure automation agent (Python prototype)")
    parser.add_argument("--config", required=True, help="Path to the YAML configuration file")
    parser.add_argument("--dashboard", action="store_true", help="Expose an HTTP dashboard with task status")
    parser.add_argument("--dump-status", action="store_true", help="Print the status snapshot when exiting")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    agent = AutomationAgent(config)

    dashboard: DashboardServer | None = None
    if args.dashboard:
        dash_cfg = config.get("runtime", {}).get("dashboard", {})
        host = dash_cfg.get("host", "0.0.0.0")
        port = int(dash_cfg.get("port", 8020))
        dashboard = DashboardServer(host, port, status_provider=agent.status.to_json)
        dashboard.start()
        agent.logger.info("Dashboard listening on %s:%s", host, port)

    def _handle_signal(signum, frame):  # pragma: no cover - interactive behaviour
        agent.logger.warning("Received signal %s, shutting down", signum)
        raise SystemExit(130)

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    summary = agent.run()

    if args.dump_status:
        print(agent.status.to_json())

    if dashboard:
        dashboard.stop()

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
