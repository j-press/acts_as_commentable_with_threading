"""Minimal HTTP dashboard for exposing agent status."""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable


class DashboardServer:
    """Expose a read-only HTTP endpoint for agent status."""

    def __init__(self, host: str, port: int, status_provider: Callable[[], str]):
        self.host = host
        self.port = port
        self.status_provider = status_provider
        self._thread: threading.Thread | None = None
        self._server: ThreadingHTTPServer | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        status_provider = self.status_provider

        class Handler(BaseHTTPRequestHandler):  # pragma: no cover - exercised in integration tests
            def do_GET(self):
                if self.path not in {"/", "/status"}:
                    self.send_error(404)
                    return
                payload = status_provider()
                data = payload.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, format, *args):  # pragma: no cover - suppress noise in tests
                return

        self._server = ThreadingHTTPServer((self.host, self.port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server.server_close()
        if self._thread:
            self._thread.join(timeout=2)

    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())


__all__ = ["DashboardServer"]
